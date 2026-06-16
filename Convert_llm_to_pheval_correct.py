"""
Correct converter using PhEval's generate_gene_result helper.

This replaces the manual parquet creation and true_positive flagging approach.
PhEval handles true positive identification internally using the original
(unredacted) phenopackets.

Usage:
    python convert_llm_to_pheval_correct.py
"""

import json
from pathlib import Path
import polars as pl

from pheval.post_processing.post_processing import generate_gene_result, SortOrder

# ── Configuration ─────────────────────────────────────────────────────────────
# Raw LLM results directory (JSON files from run_llm_batch.py)
LLM_RESULTS_DIR = Path("llm_results_phenotype_only_10genes")

# Output directory for PhEval standardised gene results
OUTPUT_DIR = Path("pheval_gene_results_correct")

# IMPORTANT: use the ORIGINAL unredacted phenopackets, not the redacted ones
# PhEval uses these to determine true positives internally
PHENOPACKET_DIR = Path("synthetic_patients_original")
# ──────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

json_files = sorted(LLM_RESULTS_DIR.glob("patient_*.json"))
print(f"Found {len(json_files)} result files\n")

success = 0
skipped = 0

for filepath in json_files:
    patient_id = filepath.stem

    with open(filepath) as f:
        data = json.load(f)

    # Skip error files — PhEval will treat missing files as no result
    if "error" in data:
        print(f"⚠ Skipping {patient_id} (error file)")
        skipped += 1
        continue

    top_genes = data.get("top_genes", [])

    if not top_genes:
        print(f"⚠ Skipping {patient_id} (no top_genes)")
        skipped += 1
        continue

    # Build Polars DataFrame with required schema
    # gene_symbol, gene_identifier, score — no true_positive, PhEval handles that
    records = []
    for g in top_genes:
        gene_symbol = g.get("gene_symbol", "").strip()
        if not gene_symbol:
            continue
        records.append({
            "gene_symbol":     gene_symbol,
            "gene_identifier": gene_symbol,
            "score":           float(g.get("score", 0.0)),
        })

    if not records:
        print(f"⚠ Skipping {patient_id} (no valid genes)")
        skipped += 1
        continue

    df = pl.DataFrame(records)

    # generate_gene_result writes the standardised parquet file
    # and uses PHENOPACKET_DIR to determine true positives internally
    generate_gene_result(
        results=df,
        sort_order=SortOrder.DESCENDING,
        output_dir=OUTPUT_DIR,
        result_path=filepath,          # stem must match phenopacket stem
        phenopacket_dir=PHENOPACKET_DIR,
    )

    print(f"✓ {patient_id} ({len(records)} genes)")
    success += 1

print(f"\nDone. Converted: {success}, Skipped: {skipped}")
print(f"Output: {OUTPUT_DIR}/")