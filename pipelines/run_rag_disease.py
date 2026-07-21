"""
run_llm_rag_disease.py
======================
Disease-level RAG pipeline.

Same retrieval approach as run_llm_rag.py but asks Claude to return
OMIM disease IDs instead of gene symbols.

Retrieves top-10 similar diseases from HPOA vector store, injects
into prompt, Claude returns ranked disease list.

Usage:
    python run_llm_rag_disease.py

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

# ── Configuration ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 1000
RESULTS_DIR       = Path("llm_results_rag_disease")
PHENOPACKET_DIR   = Path("phenopackets")
HPOA_PATH         = Path("hpo_resources/phenotype.hpoa")
CHROMA_DIR        = Path("chroma_db_v2")       # reuse existing index
TOP_N_RETRIEVE    = 10
NUM_DISEASES      = 10
SLEEP_BETWEEN     = 1.0
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
COLLECTION_NAME   = "hpoa_diseases_v2"

RESULTS_DIR.mkdir(exist_ok=True)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert clinical geneticist specialising in rare disease diagnosis.

You will be given a patient's HPO phenotype terms and a list of phenotypically similar diseases retrieved from the HPO Annotation database.

Use the retrieved disease information to identify the most likely diagnosis. Consider which diseases best match the patient's specific combination of phenotypes.

You MUST respond with ONLY valid JSON — no prose, no markdown:
{"top_diseases": [{"rank": 1, "disease_id": "OMIM:123456", "disease_name": "Disease Name", "score": 0.95, "reasoning": "brief"}, {"rank": 2, "disease_id": "OMIM:234567", "disease_name": "Disease Name", "score": 0.85, "reasoning": "brief"}]}

Return exactly 10 diseases using real OMIM IDs. Never return empty top_diseases."""


def load_index():
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = chroma_client.get_collection(COLLECTION_NAME)
        print(f"Loaded ChromaDB index ({collection.count()} diseases)")
        return collection
    except Exception:
        print("ERROR: ChromaDB index not found — run run_llm_rag.py first")
        return None


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


def retrieve_diseases(hpo_labels, collection, embed_model, top_n=TOP_N_RETRIEVE):
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
        retrieved.append({
            "rank":         i + 1,
            "disease_id":   meta["disease_id"],
            "disease_name": meta["disease_name"],
            "similarity":   round(1 - dist, 3),
        })
    return retrieved


def build_prompt(hpo_labels: list, retrieved: list) -> str:
    hpo_str = "\n".join(f"- {l}" for l in hpo_labels)
    disease_str = "\n".join(
        f"{d['rank']}. {d['disease_name']} ({d['disease_id']}) [similarity: {d['similarity']}]"
        for d in retrieved
    )
    return f"""A patient presents with the following HPO phenotype terms:
{hpo_str}

The following diseases were retrieved from the HPO Annotation database as phenotypically similar:
{disease_str}

Based on the patient's phenotypes and these retrieved diseases, return your top {NUM_DISEASES} most likely diagnoses as OMIM IDs."""


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    try:
        r = json.loads(text)
        if "top_diseases" in r:
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
                if "top_diseases" in r:
                    return r
            except json.JSONDecodeError:
                continue
    match = re.search(r'\{.*?"top_diseases".*?\}', text, re.DOTALL)
    if match:
        try:
            r = json.loads(match.group())
            if "top_diseases" in r:
                return r
        except json.JSONDecodeError:
            pass
    return None


def _pad_diseases(top_diseases: list, retrieved: list, target: int = 10) -> list:
    """Pad disease list to target using retrieved diseases."""
    seen = {d.get("disease_id", "") for d in top_diseases}
    for d in retrieved:
        if d["disease_id"] not in seen and len(top_diseases) < target:
            top_diseases.append({
                "rank":         len(top_diseases) + 1,
                "disease_id":   d["disease_id"],
                "disease_name": d["disease_name"],
                "score":        round(d["similarity"] * 0.4, 3),
                "reasoning":    "RAG retrieval fallback",
            })
            seen.add(d["disease_id"])
    return top_diseases


def already_done(patient_id: str) -> bool:
    f = RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.loads(f.read_text())
    return "error" not in data and bool(data.get("top_diseases"))


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY")
        return

    print("Loading resources...")
    embed_model  = SentenceTransformer(EMBEDDING_MODEL)
    collection   = load_index()
    if not collection:
        return
    id_to_label  = parse_hpo_labels()

    phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
    total = len(phenopackets)
    print(f"\nDisease-level RAG — {total} patients")
    print(f"Retrieve: top-{TOP_N_RETRIEVE} diseases from HPOA")
    print(f"Output: {RESULTS_DIR}/\n")

    success = skipped = failed = 0

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

            retrieved = retrieve_diseases(hpo_labels, collection, embed_model)
            prompt    = build_prompt(hpo_labels, retrieved)

            response = client.messages.create(
                model      = MODEL,
                max_tokens = MAX_TOKENS,
                system     = SYSTEM_PROMPT,
                messages   = [{"role": "user", "content": prompt}],
            )

            text   = response.content[0].text.strip()
            result = _parse_json(text)

            if not result:
                # Force JSON formatter
                force = client.messages.create(
                    model      = MODEL,
                    max_tokens = 600,
                    system     = "Return ONLY valid JSON. No prose.",
                    messages   = [{"role": "user", "content": f"Format as JSON with top_diseases array:\n{text[:500]}\n\nUse format: {{\"top_diseases\": [{{\"rank\": 1, \"disease_id\": \"OMIM:123456\", \"disease_name\": \"Name\", \"score\": 0.9, \"reasoning\": \"brief\"}}]}}"}],
                )
                result = _parse_json(force.content[0].text)

            if not result:
                result = {"top_diseases": []}

            # Pad to 10 from retrieved
            result["top_diseases"] = _pad_diseases(
                result.get("top_diseases", []), retrieved
            )

            result["patient_id"]         = patient_id
            result["hpo_labels"]         = hpo_labels
            result["retrieved_diseases"] = retrieved

            (RESULTS_DIR / f"{patient_id}.json").write_text(json.dumps(result, indent=2))

            n = len(result.get("top_diseases", []))
            top1 = result["top_diseases"][0]["disease_id"] if result.get("top_diseases") else "none"
            print(f"ok  top: {top1}  diseases: {n}")
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
    print(f"\nNext: scp to Apocrita → convert_disease_to_pheval.py → benchmark")


if __name__ == "__main__":
    main()
