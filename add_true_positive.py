"""
Add true_positive column to pheval_gene_results/*.parquet
using ground_truth_genes_all.csv

true_positive = True if gene_symbol matches the ground truth gene for that patient
"""

import csv
from pathlib import Path
import polars as pl

GROUND_TRUTH_FILE = Path("ground_truth_genes_all.csv")
RESULTS_DIR       = Path("pheval_gene_results")

# ── Load ground truth ──────────────────────────────────────────────────────────
truth = {}
with open(GROUND_TRUTH_FILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        gene = row["ground_truth_gene"].strip()
        if gene != "?":
            truth[row["patient_id"].strip()] = gene

print(f"Loaded ground truth for {len(truth)} patients\n")

# ── Add true_positive column to each parquet file ─────────────────────────────
updated  = 0
skipped  = 0

for patient_id, true_gene in truth.items():
    parquet_file = RESULTS_DIR / f"{patient_id}-gene_result.parquet"

    if not parquet_file.exists():
        print(f"  ⚠ Missing parquet for {patient_id}")
        skipped += 1
        continue

    df = pl.read_parquet(parquet_file)

    df = df.with_columns(
        (pl.col("gene_symbol") == true_gene).alias("true_positive")
    )

    df.write_parquet(parquet_file)
    updated += 1

print(f"Done.")
print(f"  ✓ Updated : {updated}")
print(f"  ⚠ Skipped : {skipped}")