"""
run_llm_rag_v2_exomiser.py
=======================
RAG + Exomiser variant evidence pipeline.

Combines:
1. RAG: retrieve top-N similar diseases from HPOA vector store
2. Exomiser: top-10 genes ranked by phenotype score from parquet files

Claude receives both sources and re-ranks using combined evidence.

Usage:
    python run_llm_rag_exomiser.py

Environment:
    ANTHROPIC_API_KEY
"""

import os
import json
import time
import re
from pathlib import Path
import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False
    print("Warning: polars not installed — Exomiser parquet loading disabled")

# ── Configuration ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 1000
RESULTS_DIR       = Path("llm_results_rag_exomiser_no_padding")
PHENOPACKET_DIR   = Path("phenopackets")
EXOMISER_DIR      = Path("exomiser_results")
HPOA_PATH         = Path("hpo_resources/phenotype.hpoa")
CHROMA_DIR        = Path("chroma_db_v2")
TOP_N_RETRIEVE    = 10
TOP_N_EXOMISER    = 10
NUM_GENES         = 10
SLEEP_BETWEEN     = 1.0
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
COLLECTION_NAME   = "hpoa_diseases_v2"

RESULTS_DIR.mkdir(exist_ok=True)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert clinical geneticist specialising in rare Mendelian disease diagnosis.

You will be given:
1. A patient's HPO phenotype terms
2. Phenotypically similar diseases retrieved from the HPOA database (with associated genes)
3. Exomiser's top candidate genes ranked by phenotype-similarity score

Use ALL three sources of evidence together. The retrieved diseases tell you what conditions match the phenotype. The Exomiser scores give you a systematic phenotype-similarity ranking. Use your clinical reasoning to integrate both.

You MUST respond with ONLY valid JSON — no prose, no markdown:
{"top_genes": [{"rank": 1, "gene_symbol": "GENE1", "score": 0.95, "reasoning": "brief"}, {"rank": 2, "gene_symbol": "GENE2", "score": 0.85, "reasoning": "brief"}], "likely_diagnosis": "Disease name", "confidence": "high/medium/low"}

Return exactly 10 genes using real HGNC gene symbols. Never return empty top_genes."""


# ── Load resources ─────────────────────────────────────────────────────────
def load_index():
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = chroma_client.get_collection(COLLECTION_NAME)
        print(f"Loaded ChromaDB index ({collection.count()} diseases)")
        return collection
    except Exception:
        print("ERROR: ChromaDB index not found — run run_llm_rag.py first")
        return None


def build_gene_lookup() -> dict:
    lookup = {}
    genes_file = Path("hpo_resources/genes_to_disease.txt")
    if not genes_file.exists():
        return lookup
    with open(genes_file) as f:
        for line in f:
            if line.startswith("#") or line.startswith("ncbi_gene_id"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            gene_symbol = parts[1].strip()
            disease_id  = parts[3].strip()
            if disease_id not in lookup:
                lookup[disease_id] = []
            if gene_symbol not in lookup[disease_id]:
                lookup[disease_id].append(gene_symbol)
    print(f"Gene lookup: {len(lookup)} disease-gene associations")
    return lookup


def parse_hpo_labels() -> dict:
    id_to_label = {}
    for ppath in sorted(PHENOPACKET_DIR.glob("patient_*.json")):
        data = json.loads(ppath.read_text())
        for feat in data.get("phenotypicFeatures", []):
            t = feat.get("type", {})
            hid   = t.get("id", "")
            label = t.get("label", "")
            if hid and label:
                id_to_label[hid] = label
    return id_to_label


# ── Patient data loading ───────────────────────────────────────────────────
def load_patient(path: Path, id_to_label: dict) -> tuple[list, list]:
    data = json.loads(path.read_text())
    ids, labels = [], []
    for feat in data.get("phenotypicFeatures", []):
        t = feat.get("type", {})
        hid   = t.get("id", "")
        label = t.get("label", "") or id_to_label.get(hid, hid)
        if hid and not feat.get("excluded", False):
            ids.append(hid)
            labels.append(label)
    return ids, labels


def load_exomiser_genes(patient_id: str) -> list[dict]:
    """Load top Exomiser genes from parquet file."""
    if not HAS_POLARS:
        return []
    parquet_file = EXOMISER_DIR / f"{patient_id}.parquet"
    if not parquet_file.exists():
        return []
    try:
        df = pl.read_parquet(parquet_file)
        top = (
            df.unique(subset=["geneSymbol"], keep="first")
            .sort("genePhenotypeScore", descending=True)
            .head(TOP_N_EXOMISER)
            .select(["geneSymbol", "genePhenotypeScore"])
        )
        return [
            {"gene": row["geneSymbol"], "phenotype_score": round(row["genePhenotypeScore"], 4)}
            for row in top.to_dicts()
        ]
    except Exception:
        return []


# ── RAG retrieval ──────────────────────────────────────────────────────────
def retrieve_diseases(hpo_labels, collection, embed_model, gene_lookup, top_n=TOP_N_RETRIEVE):
    query     = ", ".join(hpo_labels)
    embedding = embed_model.encode([query]).tolist()
    results   = collection.query(
        query_embeddings=embedding,
        n_results=top_n,
        include=["metadatas", "distances"],
    )
    retrieved = []
    for i, (meta, dist) in enumerate(zip(
        results["metadatas"][0], results["distances"][0]
    )):
        disease_id = meta["disease_id"]
        genes      = gene_lookup.get(disease_id, [])
        retrieved.append({
            "rank":         i + 1,
            "disease_id":   disease_id,
            "disease_name": meta["disease_name"],
            "similarity":   round(1 - dist, 3),
            "genes":        genes[:5],
        })
    return retrieved


# ── Prompt builder ─────────────────────────────────────────────────────────
def build_prompt(hpo_labels: list, retrieved: list, exomiser_genes: list) -> str:
    hpo_str = "\n".join(f"- {l}" for l in hpo_labels)

    disease_str = "\n".join(
        f"{d['rank']}. {d['disease_name']} ({d['disease_id']}) "
        f"[sim: {d['similarity']}] genes: {', '.join(d['genes']) or 'unknown'}"
        for d in retrieved
    )

    if exomiser_genes:
        exo_str = "\n".join(
            f"{i+1}. {g['gene']} (phenotype score: {g['phenotype_score']})"
            for i, g in enumerate(exomiser_genes)
        )
        exo_section = f"""
Exomiser phenotype-similarity scores (systematic HPO matching):
{exo_str}"""
    else:
        exo_section = "\nExomiser scores: not available for this patient."

    return f"""A patient presents with the following HPO phenotype terms:
{hpo_str}

Phenotypically similar diseases retrieved from HPOA:
{disease_str}
{exo_section}

Using all three sources of evidence — HPO phenotypes, retrieved diseases, and Exomiser scores — return your top {NUM_GENES} most likely causative genes."""


# ── JSON parsing and padding ───────────────────────────────────────────────
def _parse_json(text: str) -> dict | None:
    text = text.strip()
    try:
        r = json.loads(text)
        if "top_genes" in r:
            return r
    except json.JSONDecodeError:
        pass
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                r = json.loads(part)
                if "top_genes" in r:
                    return r
            except json.JSONDecodeError:
                continue
    match = re.search(r'\{.*?"top_genes".*?\}', text, re.DOTALL)
    if match:
        try:
            r = json.loads(match.group())
            if "top_genes" in r:
                return r
        except json.JSONDecodeError:
            pass
    return None


def _pad_genes(top_genes: list, retrieved: list, exomiser_genes: list, target: int = 10) -> list:
    """Padding disabled for this ablation run — Claude's raw output is returned as-is."""
    return top_genes


# ── Main ───────────────────────────────────────────────────────────────────
def already_done(patient_id: str) -> bool:
    f = RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.loads(f.read_text())
    return "error" not in data and bool(data.get("top_genes"))


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY")
        return

    print("Loading resources...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL)
    collection  = load_index()
    if not collection:
        return
    gene_lookup  = build_gene_lookup()
    id_to_label  = parse_hpo_labels()

    phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
    total = len(phenopackets)

    # Count how many have Exomiser results
    n_exomiser = sum(1 for p in phenopackets if (EXOMISER_DIR / f"{p.stem}.parquet").exists())
    print(f"\nRAG + Exomiser — {total} patients ({n_exomiser} with Exomiser scores)")
    print(f"Retrieve: top-{TOP_N_RETRIEVE} diseases from HPOA + top-{TOP_N_EXOMISER} Exomiser genes")
    print(f"Output: {RESULTS_DIR}/\n")

    success = skipped = failed = no_exo = 0

    for i, ppath in enumerate(phenopackets, 1):
        patient_id = ppath.stem

        if already_done(patient_id):
            print(f"[{i:03d}/{total}] skip  {patient_id}")
            skipped += 1
            continue

        print(f"[{i:03d}/{total}] run   {patient_id}...", end=" ", flush=True)

        try:
            hpo_ids, hpo_labels = load_patient(ppath, id_to_label)
            if not hpo_labels:
                print("no HPO terms")
                skipped += 1
                continue

            retrieved      = retrieve_diseases(hpo_labels, collection, embed_model, gene_lookup)
            exomiser_genes = load_exomiser_genes(patient_id)
            if not exomiser_genes:
                no_exo += 1

            prompt   = build_prompt(hpo_labels, retrieved, exomiser_genes)
            response = client.messages.create(
                model      = MODEL,
                max_tokens = MAX_TOKENS,
                system     = SYSTEM_PROMPT,
                messages   = [{"role": "user", "content": prompt}],
            )

            text   = response.content[0].text.strip()
            result = _parse_json(text)

            if not result:
                # Force JSON
                force = client.messages.create(
                    model      = MODEL,
                    max_tokens = 600,
                    system     = "Return ONLY valid JSON. No prose.",
                    messages   = [{"role": "user", "content": f"Format as JSON with top_genes array:\n{text[:500]}\n\nFormat: {{\"top_genes\": [{{\"rank\": 1, \"gene_symbol\": \"GENE1\", \"score\": 0.9, \"reasoning\": \"brief\"}}], \"likely_diagnosis\": \"Disease\", \"confidence\": \"medium\"}}"}],
                )
                result = _parse_json(force.content[0].text)

            if not result:
                result = {"top_genes": []}

            result["top_genes"] = _pad_genes(
                result.get("top_genes", []), retrieved, exomiser_genes
            )

            result["patient_id"]         = patient_id
            result["hpo_labels"]         = hpo_labels
            result["retrieved_diseases"] = retrieved
            result["exomiser_genes"]     = exomiser_genes

            (RESULTS_DIR / f"{patient_id}.json").write_text(json.dumps(result, indent=2))

            n_genes = len(result.get("top_genes", []))
            top1    = result["top_genes"][0]["gene_symbol"] if result.get("top_genes") else "none"
            exo_tag = f"exo:{len(exomiser_genes)}" if exomiser_genes else "no-exo"
            print(f"ok  top: {top1}  genes: {n_genes}  {exo_tag}")
            success += 1

        except anthropic.RateLimitError:
            print("rate limited — waiting 60s")
            time.sleep(60)
            failed += 1

        except Exception as e:
            print(f"error  {str(e)[:60]}")
            (RESULTS_DIR / f"{patient_id}.json").write_text(
                json.dumps({"error": str(e), "patient_id": patient_id})
            )
            failed += 1

        time.sleep(SLEEP_BETWEEN)

    print(f"\nDone.  ok {success}  skip {skipped}  failed {failed}  no-exomiser {no_exo}")
    print(f"Results: {RESULTS_DIR}/")
    print(f"\nNext: scp to Apocrita → convert_llm_to_pheval.py → benchmark")


if __name__ == "__main__":
    main()