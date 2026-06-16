"""
Convert LLM disease-level JSON results to PhEval standardised disease parquet files.

Uses generate_disease_result which handles true positive identification internally
using the diseases field (OMIM ID) in the original phenopackets.

Usage:
    python convert_llm_disease_to_pheval.py
"""

import json
from pathlib import Path
import polars as pl

from pheval.post_processing.post_processing import generate_disease_result, SortOrder

# ── Configuration ─────────────────────────────────────────────────────────────
# Raw LLM disease results (from run_llm_disease_level.py)
LLM_RESULTS_DIR = Path("llm_results_disease_level")

# Output directory for PhEval standardised disease results
OUTPUT_DIR = Path("pheval_disease_results_llm")

# Original phenopackets with OMIM disease IDs
# PhEval uses these to determine true positives internally
PHENOPACKET_DIR = Path("synthetic_corpus_prepared/phenopackets")
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

    if "error" in data:
        print(f"⚠ Skipping {patient_id} (error file)")
        skipped += 1
        continue

    top_diseases = data.get("top_diseases", [])

    if not top_diseases:
        print(f"⚠ Skipping {patient_id} (no top_diseases)")
        skipped += 1
        continue

    # Build Polars DataFrame with required disease schema:
    # disease_identifier, score
    records = []
    for d in top_diseases:
        disease_id = d.get("disease_id", "").strip()
        if not disease_id:
            continue
        records.append({
            "disease_identifier": disease_id,
            "score":              float(d.get("score", 0.0)),
        })

    if not records:
        print(f"⚠ Skipping {patient_id} (no valid disease IDs)")
        skipped += 1
        continue

    df = pl.DataFrame(records)

    # generate_disease_result handles true positive identification
    # using OMIM disease IDs from the phenopacket's diseases field
    generate_disease_result(
        results=df,
        sort_order=SortOrder.DESCENDING,
        output_dir=OUTPUT_DIR,
        result_path=filepath,
        phenopacket_dir=PHENOPACKET_DIR,
    )

    print(f"✓ {patient_id} ({len(records)} diseases)")
    success += 1

print(f"\nDone. Converted: {success}, Skipped: {skipped}")
print(f"Output: {OUTPUT_DIR}/")