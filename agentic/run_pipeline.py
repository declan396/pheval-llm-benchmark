"""
run_pipeline.py
===============
Main entry point for the agentic gene prioritisation pipeline.

Processes all patients in the phenopackets directory and saves
results to llm_results_agentic/ for PhEval benchmarking.

Usage:
    python run_pipeline.py                   # run all patients
    python run_pipeline.py --patient patient_001  # single patient
    python run_pipeline.py --limit 10        # first 10 patients only
    python run_pipeline.py --verbose         # show tool call details

Environment variables:
    ANTHROPIC_API_KEY   (required)
    OMIM_API_KEY        (optional but recommended)
"""

import os
import json
import time
import argparse
from pathlib import Path

from agentic.phenopacket_loader import load_phenopacket
from agentic.exomiser_loader import load_candidates_for_patient
from agentic.agent import run_agent

# ── Paths ──────────────────────────────────────────────────────────────────
PHENOPACKET_DIR  = Path("../phenopackets")
EXOMISER_DIR     = Path("../exomiser_results")
OUTPUT_DIR       = Path("llm_results_agentic")
LOOKUP_CSV       = Path("synthetic_patients_lookup.csv")

# ── Settings ───────────────────────────────────────────────────────────────
TOP_N_EXOMISER   = 10   # Exomiser candidates to pass to Claude
SLEEP_BETWEEN    = 2.0  # seconds between patients (rate limiting)


def process_patient(
    phenopacket_path: Path,
    verbose: bool = False,
) -> dict:
    """Load, run agent, return result dict."""
    patient    = load_phenopacket(phenopacket_path)
    candidates = load_candidates_for_patient(
        patient_id   = patient.patient_id,
        exomiser_dir = EXOMISER_DIR,
        lookup_csv   = LOOKUP_CSV,
        top_n        = TOP_N_EXOMISER,
    )
    result = run_agent(patient, candidates, verbose=verbose)
    result["patient_id"]          = patient.patient_id
    result["hpo_terms"]           = patient.hpo_terms
    result["exomiser_candidates"] = [
        {"rank": c.rank, "gene_symbol": c.gene_symbol, "score": c.score}
        for c in candidates
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description="Agentic gene prioritisation pipeline")
    parser.add_argument("--patient", help="Run single patient by ID e.g. patient_001")
    parser.add_argument("--limit",   type=int, help="Process only first N patients")
    parser.add_argument("--verbose", action="store_true", help="Print tool call details")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        return

    if not os.environ.get("OMIM_API_KEY"):
        print("WARNING: OMIM_API_KEY not set — Claude will reason without OMIM lookups")
        print("         Get a free key at https://omim.org/api\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Collect phenopackets to process
    if args.patient:
        phenopackets = [PHENOPACKET_DIR / f"{args.patient}.json"]
        if not phenopackets[0].exists():
            print(f"ERROR: {phenopackets[0]} not found")
            return
    else:
        phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
        if args.limit:
            phenopackets = phenopackets[:args.limit]

    print(f"Agentic pipeline — {len(phenopackets)} patient(s)")
    print(f"Output: {OUTPUT_DIR}/\n")

    success = skipped = failed = 0

    for i, ppath in enumerate(phenopackets, 1):
        patient_id  = ppath.stem
        output_file = OUTPUT_DIR / f"{patient_id}.json"

        # Skip completed patients
        if output_file.exists():
            existing = json.loads(output_file.read_text())
            if "error" not in existing and existing.get("top_genes"):
                print(f"[{i:03d}/{len(phenopackets):03d}] skip  {patient_id}")
                skipped += 1
                continue

        print(f"[{i:03d}/{len(phenopackets):03d}] run   {patient_id}...", end=" ", flush=True)

        try:
            result = process_patient(ppath, verbose=args.verbose)
            output_file.write_text(json.dumps(result, indent=2))

            n_genes  = len(result.get("top_genes", []))
            n_tools  = len(result.get("tool_calls", []))
            n_rounds = result.get("rounds", 0)
            top1     = result["top_genes"][0]["gene_symbol"] if result.get("top_genes") else "—"

            print(f"✓  {n_genes} genes  {n_tools} OMIM calls  {n_rounds} rounds  top: {top1}")
            success += 1

        except Exception as e:
            err_msg = str(e)
            print(f"✗  {err_msg[:80]}")
            output_file.write_text(json.dumps({"error": err_msg, "patient_id": patient_id}))

            if "rate_limit" in err_msg.lower() or "529" in err_msg:
                print("    Rate limited — waiting 60s")
                time.sleep(60)
            failed += 1

        if i < len(phenopackets):
            time.sleep(SLEEP_BETWEEN)

    print(f"\n{'─' * 50}")
    print(f"Done.  ✓ {success}  skip {skipped}  ✗ {failed}")
    print(f"Results saved to: {OUTPUT_DIR}/")
    print(f"\nNext step — benchmark with PhEval:")
    print(f"  python convert_to_pheval.py")


if __name__ == "__main__":
    main()
