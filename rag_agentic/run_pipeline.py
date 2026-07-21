"""
run_pipeline.py
===============
Main entry point for the RAG + Monarch agentic pipeline.

Processes all patients in the phenopackets directory and saves
results to llm_results_rag_agentic/ for PhEval benchmarking.

Usage:
    python run_pipeline.py                        # all patients
    python run_pipeline.py --patient patient_001  # single patient
    python run_pipeline.py --limit 10             # first 10 only
    python run_pipeline.py --verbose              # show tool calls

Environment:
    ANTHROPIC_API_KEY  (required)
"""

import os
import json
import time
import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer

from rag_retriever import (
    HPOA_PATH, CHROMA_DIR, EMBEDDING_MODEL,
    parse_hpo_labels, build_gene_lookup,
    build_or_load_index, retrieve,
)
from agent import run_agent

# ── Paths — resolve relative to project root ───────────────────────────────
_HERE           = Path(__file__).parent
BASE_DIR        = _HERE.parent
PHENOPACKET_DIR = BASE_DIR / "phenopackets"
OUTPUT_DIR      = BASE_DIR / "llm_results_rag_agentic"
TOP_N_RETRIEVE  = 10
SLEEP_BETWEEN   = 1.5

OUTPUT_DIR.mkdir(exist_ok=True)


def load_patient(path: Path, id_to_label: dict) -> tuple[list[str], list[str]]:
    """Load HPO IDs and labels from a phenopacket."""
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


def already_done(patient_id: str) -> bool:
    f = OUTPUT_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.loads(f.read_text())
    return "error" not in data and bool(data.get("top_genes"))


def main():
    parser = argparse.ArgumentParser(description="RAG + Monarch agentic pipeline")
    parser.add_argument("--patient", help="Run single patient e.g. patient_001")
    parser.add_argument("--limit",   type=int, help="Process only first N patients")
    parser.add_argument("--verbose", action="store_true", help="Show tool call details")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        return

    # Load resources
    print("Loading resources...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL)
    id_to_label = parse_hpo_labels(PHENOPACKET_DIR)
    gene_lookup = build_gene_lookup()
    collection  = build_or_load_index(HPOA_PATH, CHROMA_DIR, id_to_label)

    # Collect phenopackets
    if args.patient:
        phenopackets = [PHENOPACKET_DIR / f"{args.patient}.json"]
        if not phenopackets[0].exists():
            print(f"ERROR: {phenopackets[0]} not found")
            return
    else:
        phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
        if args.limit:
            phenopackets = phenopackets[:args.limit]

    total = len(phenopackets)
    print(f"\nRAG + Monarch Agentic — {total} patient(s)")
    print(f"Retrieve: top-{TOP_N_RETRIEVE} diseases from HPOA")
    print(f"Tools: monarch_gene_lookup · monarch_disease_lookup · monarch_phenotype_search\n")

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

            retrieved = retrieve(hpo_labels, collection, embed_model, gene_lookup, TOP_N_RETRIEVE)

            result = run_agent(
                patient_id  = patient_id,
                hpo_ids     = hpo_ids,
                hpo_labels  = hpo_labels,
                retrieved   = retrieved,
                verbose     = args.verbose,
            )

            result["patient_id"]         = patient_id
            result["hpo_ids"]            = hpo_ids
            result["hpo_labels"]         = hpo_labels
            result["retrieved_diseases"] = [
                {"rank": r.rank, "disease_id": r.disease_id,
                 "disease_name": r.disease_name, "similarity": r.similarity,
                 "genes": r.genes}
                for r in retrieved
            ]

            (OUTPUT_DIR / f"{patient_id}.json").write_text(json.dumps(result, indent=2))

            n_genes  = len(result.get("top_genes", []))
            n_tools  = len(result.get("tool_calls", []))
            n_rounds = result.get("rounds", 0)
            top1     = result["top_genes"][0]["gene_symbol"] if result.get("top_genes") else "none"
            print(f"ok  top: {top1}  tools: {n_tools}  rounds: {n_rounds}  genes: {n_genes}")
            success += 1

        except Exception as e:
            err = str(e)
            print(f"error  {err[:70]}")
            (OUTPUT_DIR / f"{patient_id}.json").write_text(
                json.dumps({"error": err, "patient_id": patient_id})
            )
            if "rate_limit" in err.lower():
                print("    Rate limited — waiting 60s")
                time.sleep(60)
            failed += 1

        if i < total:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n{'─' * 50}")
    print(f"Done.  ok {success}  skip {skipped}  failed {failed}")
    print(f"Results: {OUTPUT_DIR}/")
    print(f"\nNext: python convert_to_pheval.py")


if __name__ == "__main__":
    main()
