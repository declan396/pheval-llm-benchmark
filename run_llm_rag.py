"""
run_llm_rag.py
==============
RAG-based gene prioritisation pipeline.

FIXED: Uses HPO term labels (not IDs) for embedding — semantically meaningful.

For each patient:
1. Embed patient HPO labels using sentence-transformers
2. Retrieve top-N most similar diseases from ChromaDB (built from HPOA labels)
3. Inject retrieved disease-gene associations into Claude prompt
4. Claude returns ranked gene list

First run builds the ChromaDB index from HPOA — takes ~5 minutes.
DELETE chroma_db/ folder if rebuilding after a fix.

Usage:
    python run_llm_rag.py

Environment:
    ANTHROPIC_API_KEY
"""

import os
import json
import time
from pathlib import Path
import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

# ── Configuration ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 1000
RESULTS_DIR       = Path("llm_results_rag_v2")
PHENOPACKET_DIR   = Path("phenopackets")
HPOA_PATH         = Path("hpo_resources/phenotype.hpoa")
CHROMA_DIR        = Path("chroma_db_v2")       # new dir — forces rebuild with labels
TOP_N_RETRIEVE    = 10
NUM_GENES         = 10
SLEEP_BETWEEN     = 1.0
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"

RESULTS_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert clinical geneticist. Respond with ONLY a JSON object. No prose, no explanation, no markdown. Your entire response must be valid JSON starting with { and ending with }.

Format:
{"top_genes": [{"rank": 1, "gene_symbol": "GENE1", "score": 0.95}, {"rank": 2, "gene_symbol": "GENE2", "score": 0.85}], "likely_diagnosis": "Disease name", "confidence": "high"}

Return exactly 10 genes. Use real HGNC gene symbols only."""


# ── HPOA Parser ────────────────────────────────────────────────────────────
def parse_hpoa(hpoa_path: Path) -> dict:
    """
    Parse HPOA into disease → {name, hpo_labels} mapping.
    Uses HPO term labels from the disease name field and builds
    a text description for embedding.

    HPOA columns: database_id, disease_name, qualifier, hpo_id, reference,
                  evidence, onset, frequency, sex, modifier, aspect, biocuration
    """
    diseases = {}

    with open(hpoa_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("database_id"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue

            disease_id   = parts[0].strip()
            disease_name = parts[1].strip()
            qualifier    = parts[2].strip()
            hpo_id       = parts[3].strip()

            if qualifier == "NOT":
                continue
            if not hpo_id.startswith("HP:"):
                continue

            if disease_id not in diseases:
                diseases[disease_id] = {
                    "name":       disease_name,
                    "hpo_ids":    [],
                    "hpo_labels": [],
                }

            diseases[disease_id]["hpo_ids"].append(hpo_id)
            # We'll add labels from HPO obo if available,
            # for now use the disease name as context
            diseases[disease_id]["hpo_labels"].append(hpo_id)

    print(f"Parsed {len(diseases)} diseases from HPOA")
    return diseases


def parse_hpo_labels(hpoa_path: Path) -> dict:
    """
    Build HPO ID → label mapping by reading an hp.obo file if present,
    otherwise fall back to extracting labels from phenopackets.
    """
    # Try to find hp.obo in hpo_resources
    obo_path = hpoa_path.parent / "hp.obo"
    id_to_label = {}

    if obo_path.exists():
        print("Loading HPO labels from hp.obo...")
        current_id = None
        with open(obo_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("id: HP:"):
                    current_id = line.replace("id: ", "").strip()
                elif line.startswith("name: ") and current_id:
                    label = line.replace("name: ", "").strip()
                    id_to_label[current_id] = label
                    current_id = None
        print(f"Loaded {len(id_to_label)} HPO labels from hp.obo")
    else:
        print("hp.obo not found — extracting labels from phenopackets...")
        for ppath in sorted(Path("phenopackets").glob("patient_*.json")):
            data = json.loads(ppath.read_text())
            for feat in data.get("phenotypicFeatures", []):
                t = feat.get("type", {})
                hid = t.get("id", "")
                label = t.get("label", "")
                if hid and label:
                    id_to_label[hid] = label
        print(f"Extracted {len(id_to_label)} HPO labels from phenopackets")

    return id_to_label


# ── ChromaDB Index ─────────────────────────────────────────────────────────
def build_or_load_index(hpoa_path: Path, chroma_dir: Path, id_to_label: dict):
    """
    Build ChromaDB index using HPO term LABELS for embedding.
    Each disease embedded as: "disease_name: label1, label2, label3..."
    """
    chroma_client = chromadb.PersistentClient(path=str(chroma_dir))

    try:
        collection = chroma_client.get_collection("hpoa_diseases_v2")
        count = collection.count()
        if count > 0:
            print(f"Loaded existing ChromaDB index ({count} diseases)")
            return collection
    except Exception:
        pass

    print("Building ChromaDB index with HPO labels — ~5 minutes...")
    diseases = parse_hpoa(hpoa_path)
    model = SentenceTransformer(EMBEDDING_MODEL)

    collection = chroma_client.get_or_create_collection(
        name="hpoa_diseases_v2",
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 500
    ids, documents, metadatas = [], [], []

    for disease_id, data in diseases.items():
        # Convert HPO IDs to labels for semantic embedding
        labels = []
        for hpo_id in data["hpo_ids"]:
            label = id_to_label.get(hpo_id, hpo_id)  # fall back to ID if no label
            labels.append(label)

        # Rich text representation for embedding
        doc = f"{data['name']}: {', '.join(labels)}"

        ids.append(disease_id)
        documents.append(doc)
        metadatas.append({
            "disease_id":   disease_id,
            "disease_name": data["name"],
            "hpo_ids":      ",".join(data["hpo_ids"][:20]),  # store first 20
        })

        if len(ids) >= batch_size:
            embeddings = model.encode(documents, show_progress_bar=False).tolist()
            collection.add(ids=ids, documents=documents,
                           metadatas=metadatas, embeddings=embeddings)
            print(f"  Indexed {collection.count()} diseases...")
            ids, documents, metadatas = [], [], []

    if ids:
        embeddings = model.encode(documents, show_progress_bar=False).tolist()
        collection.add(ids=ids, documents=documents,
                       metadatas=metadatas, embeddings=embeddings)

    print(f"Index complete: {collection.count()} diseases")
    return collection


# ── Gene-Disease Lookup ────────────────────────────────────────────────────
def build_gene_lookup() -> dict:
    """
    Parse genes_to_disease.txt format:
    ncbi_gene_id  gene_symbol  association_type  disease_id  source
    col 0         col 1        col 2             col 3       col 4
    """
    lookup = {}
    genes_file = Path("hpo_resources/genes_to_disease.txt")
    if not genes_file.exists():
        print("Warning: genes_to_disease.txt not found — no gene associations")
        return lookup

    with open(genes_file) as f:
        for line in f:
            # Skip header and comments
            if line.startswith("#") or line.startswith("ncbi_gene_id"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            gene_symbol = parts[1].strip()   # col 1
            disease_id  = parts[3].strip()   # col 3 e.g. OMIM:212050
            if not gene_symbol or not disease_id:
                continue
            if disease_id not in lookup:
                lookup[disease_id] = []
            if gene_symbol not in lookup[disease_id]:
                lookup[disease_id].append(gene_symbol)

    print(f"Gene lookup: {len(lookup)} disease-gene associations")
    return lookup


# ── RAG Retrieval ──────────────────────────────────────────────────────────
def retrieve_similar_diseases(
    hpo_labels: list[str],
    collection,
    model: SentenceTransformer,
    gene_lookup: dict,
    top_n: int = TOP_N_RETRIEVE,
) -> list[dict]:
    # Query using labels as natural language
    query = ", ".join(hpo_labels)
    embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=top_n,
        include=["metadatas", "distances"],
    )

    retrieved = []
    for i, (meta, dist) in enumerate(zip(
        results["metadatas"][0],
        results["distances"][0],
    )):
        disease_id = meta["disease_id"]
        genes = gene_lookup.get(disease_id, [])
        retrieved.append({
            "rank":         i + 1,
            "disease_id":   disease_id,
            "disease_name": meta["disease_name"],
            "similarity":   round(1 - dist, 3),
            "genes":        genes[:5],
        })

    return retrieved


# ── Load patient HPO terms ─────────────────────────────────────────────────
def load_hpo_terms(path: Path, id_to_label: dict) -> tuple[list[str], list[str]]:
    """Returns (hpo_ids, hpo_labels) — use labels for embedding, IDs for logging."""
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


# ── Prompt Builder ─────────────────────────────────────────────────────────
def build_prompt(hpo_labels: list[str], retrieved: list[dict]) -> str:
    hpo_str = "\n".join(f"- {l}" for l in hpo_labels)

    disease_str = ""
    for d in retrieved:
        genes = ", ".join(d["genes"]) if d["genes"] else "no gene data"
        disease_str += (
            f"{d['rank']}. {d['disease_name']} ({d['disease_id']}) "
            f"[similarity: {d['similarity']}]\n"
            f"   Associated genes: {genes}\n"
        )

    return f"""A patient presents with the following clinical phenotype features:
{hpo_str}

The following diseases were retrieved from the HPO Annotation database as phenotypically similar:

{disease_str}
Based on the patient's phenotypes and these retrieved disease-gene associations, return your top {NUM_GENES} most likely causative genes."""


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
    if not HPOA_PATH.exists():
        print(f"ERROR: HPOA not found at {HPOA_PATH}")
        return

    print("Loading embedding model...")
    embed_model  = SentenceTransformer(EMBEDDING_MODEL)
    id_to_label  = parse_hpo_labels(HPOA_PATH)
    collection   = build_or_load_index(HPOA_PATH, CHROMA_DIR, id_to_label)
    gene_lookup  = build_gene_lookup()

    phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
    total = len(phenopackets)
    print(f"\nRAG pipeline v2 — {total} patients")
    print(f"Embedding: HPO labels (not IDs) → semantic matching")
    print(f"Retrieve: top-{TOP_N_RETRIEVE} similar diseases per patient\n")

    success = skipped = failed = 0

    for i, ppath in enumerate(phenopackets, 1):
        patient_id = ppath.stem

        if already_done(patient_id):
            print(f"[{i:03d}/{total}] skip  {patient_id}")
            skipped += 1
            continue

        print(f"[{i:03d}/{total}] run   {patient_id}...", end=" ", flush=True)

        try:
            hpo_ids, hpo_labels = load_hpo_terms(ppath, id_to_label)
            if not hpo_labels:
                print("no HPO terms")
                skipped += 1
                continue

            retrieved = retrieve_similar_diseases(
                hpo_labels, collection, embed_model, gene_lookup
            )

            prompt = build_prompt(hpo_labels, retrieved)
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text.strip()
            result = None

            # Try direct parse first
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                pass

            # Try extracting from markdown code fences
            if not result and "```" in text:
                for part in text.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if not part:
                        continue
                    try:
                        parsed = json.loads(part)
                        if "top_genes" in parsed:
                            result = parsed
                            break
                    except json.JSONDecodeError:
                        continue

            # Try extracting JSON object with regex
            if not result:
                import re
                match = re.search(r'\{[^{}]*"top_genes"[^{}]*\[.*?\][^{}]*\}', text, re.DOTALL)
                if match:
                    try:
                        result = json.loads(match.group())
                    except json.JSONDecodeError:
                        pass

            # Try finding any { } block
            if not result:
                import re
                matches = re.findall(r'\{.*?\}', text, re.DOTALL)
                for m in matches:
                    try:
                        parsed = json.loads(m)
                        if "top_genes" in parsed:
                            result = parsed
                            break
                    except json.JSONDecodeError:
                        continue

            if not result:
                # Save raw for debugging
                raise ValueError(f"Could not parse JSON. Raw: {text[:200]}")

            result["patient_id"]         = patient_id
            result["hpo_ids"]            = hpo_ids
            result["hpo_labels"]         = hpo_labels
            result["retrieved_diseases"] = retrieved

            (RESULTS_DIR / f"{patient_id}.json").write_text(json.dumps(result, indent=2))

            top1 = result["top_genes"][0]["gene_symbol"] if result.get("top_genes") else "none"
            print(f"ok  top: {top1}  retrieved: {len(retrieved)}")
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

    print(f"\nDone.  ok {success}  skip {skipped}  failed {failed}")
    print(f"Results: {RESULTS_DIR}/")
    print(f"\nNext: scp to Apocrita → convert → benchmark")


if __name__ == "__main__":
    main()