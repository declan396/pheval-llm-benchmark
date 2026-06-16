"""
Convert llm_results/*.json → pheval_gene_results/*.parquet

Compatible with the JSON format produced by run_llm_batch.py:
{
  "patient_id": "patient_001",
  "top_genes": [
    {"rank": 1, "gene_symbol": "RYR2", "score": 0.95},
    ...
  ],
  ...
}
"""

import json
from pathlib import Path
import polars as pl

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_DIR  = Path("llm_results")           # folder of per-patient JSON files
OUTPUT_DIR = Path("pheval_gene_results")   # PhEval expects this structure
# ──────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

json_files = sorted(INPUT_DIR.glob("patient_*.json"))
print(f"Found {len(json_files)} result files in {INPUT_DIR}/\n")

success = 0
skipped = 0
errors  = 0

for filepath in json_files:
    patient_id = filepath.stem

    with open(filepath) as f:
        data = json.load(f)

    # Skip error files
    if "error" in data:
        print(f"⚠ Skipping {patient_id} (error file)")
        skipped += 1
        continue

    top_genes = data.get("top_genes", [])

    if not top_genes:
        print(f"⚠ Skipping {patient_id} (no top_genes)")
        skipped += 1
        continue

    records = []
    for gene_entry in top_genes:
        gene_symbol = gene_entry.get("gene_symbol", "UNKNOWN").strip()
        score       = float(gene_entry.get("score", 0.0))
        rank        = int(gene_entry.get("rank", 0))

        if not gene_symbol or gene_symbol == "UNKNOWN":
            continue

        records.append({
            "gene_symbol":     gene_symbol,
            "gene_identifier": gene_symbol,
            "score":           score,
            "rank":            rank,
            "grouping_id":     gene_symbol,
        })

    if not records:
        records.append({
            "gene_symbol":    "UNKNOWN",
            "gene_identifier": "UNKNOWN",
            "score":           0.0,
            "grouping_id":     "UNKNOWN",
        })

    df = pl.DataFrame(records)
    out_file = OUTPUT_DIR / f"{patient_id}-gene_result.parquet"
    df.write_parquet(out_file)
    success += 1

print(f"\nDone.")
print(f"  ✓ Converted : {success}")
print(f"  ⚠ Skipped   : {skipped}")
print(f"  ✗ Errors    : {errors}")
print(f"\nOutput written to: {OUTPUT_DIR}/")