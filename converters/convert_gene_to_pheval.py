"""
Correct converter using PhEval's generate_gene_result helper.

Uses synthetic_patients_lookup.csv to map patient_001 → OMIM_100700_patient_1
so that result file stems match the phenopacket stems in synthetic_patients_with_genes/.

PhEval handles true positive identification internally using the interpretations
field in the original phenopackets with gene annotations.

Usage:
    python convert_llm_to_pheval_correct.py

Paths assume you are running from your PyCharm project directory.
Copy results to Apocrita after running locally, or run directly on Apocrita.
"""

import csv
import json
from pathlib import Path
import polars as pl

from pheval.post_processing.post_processing import generate_gene_result, SortOrder

# ── Configuration ─────────────────────────────────────────────────────────────
# Raw LLM results (patient_001.json etc)
LLM_RESULTS_DIR = Path("llm_results_exomiser_assisted_sonnet")

# Output directory for PhEval standardised gene results
OUTPUT_DIR = Path("pheval_gene_results_correct")

# Phenopackets WITH gene interpretations (OMIM-named)
# PhEval uses these to determine true positives internally
PHENOPACKET_DIR = Path("synthetic_patients_with_genes")

# Lookup CSV mapping patient_001 → OMIM_100700_patient_1
LOOKUP_CSV = Path("synthetic_patients_lookup.csv")
# ──────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Build lookup: patient_001 → OMIM_100700_patient_1 (stem only)
lookup = {}
with open(LOOKUP_CSV) as f:
    for row in csv.DictReader(f):
        new_stem = Path(row["new_file"]).stem          # patient_001
        orig_stem = Path(row["original_file"]).stem    # OMIM_100700_patient_1
        lookup[new_stem] = orig_stem

json_files = sorted(LLM_RESULTS_DIR.glob("patient_*.json"))
print(f"Found {len(json_files)} result files")
print(f"Lookup entries: {len(lookup)}\n")

success = 0
skipped = 0
no_match = 0

for filepath in json_files:
    patient_id = filepath.stem  # patient_001

    # Look up the original OMIM-named stem
    orig_stem = lookup.get(patient_id)
    if not orig_stem:
        print(f"⚠ No lookup entry for {patient_id}")
        no_match += 1
        continue

    # Check the corresponding phenopacket with genes exists
    phenopacket_path = PHENOPACKET_DIR / f"{orig_stem}.json"
    if not phenopacket_path.exists():
        print(f"⚠ No phenopacket with genes for {orig_stem} (disease has no known gene)")
        skipped += 1
        continue

    with open(filepath) as f:
        data = json.load(f)

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

    # result_path stem must match the phenopacket stem exactly
    # We pass phenopacket_path as result_path so the stem matches
    generate_gene_result(
        results=df,
        sort_order=SortOrder.DESCENDING,
        output_dir=OUTPUT_DIR,
        result_path=phenopacket_path,      # stem = OMIM_100700_patient_1
        phenopacket_dir=PHENOPACKET_DIR,   # contains OMIM_100700_patient_1.json
    )

    print(f"✓ {patient_id} → {orig_stem} ({len(records)} genes)")
    success += 1

print(f"\nDone.")
print(f"  Converted:     {success}")
print(f"  Skipped:       {skipped} (errors, no genes, or no phenopacket with genes)")
print(f"  No lookup:     {no_match}")
print(f"  Output:        {OUTPUT_DIR}/")