"""
convert_disease_to_pheval.py
============================
Convert disease-level LLM results to PhEval disease result parquet files.

Uses generate_disease_result with synthetic_patients/ as phenopacket_dir.
Disease-level benchmarking only needs the diseases field (OMIM ID) in the
phenopacket — NOT gene interpretations — so we use the original
synthetic_patients/ directory, not synthetic_patients_with_genes/.

Run on Apocrita:
    python3 convert_disease_to_pheval.py
"""

import csv
import json
from pathlib import Path

try:
    import polars as pl
    from pheval.post_processing.post_processing import generate_disease_result, SortOrder
    HAS_PHEVAL = True
except ImportError:
    HAS_PHEVAL = False
    print("ERROR: pheval not installed")

# ── Paths ──────────────────────────────────────────────────────────────────
LLM_RESULTS_DIR  = Path("llm_results_disease_level")
OUTPUT_DIR       = Path("pheval_disease_results_correct")
PHENOPACKET_DIR  = Path("synthetic_patients")   # original — has diseases field
LOOKUP_CSV       = Path("synthetic_patients_lookup.csv")


def build_lookup() -> dict:
    lookup = {}
    if LOOKUP_CSV.exists():
        with open(LOOKUP_CSV) as f:
            for row in csv.DictReader(f):
                lookup[Path(row["new_file"]).stem] = Path(row["original_file"]).stem
    return lookup


def main():
    if not HAS_PHEVAL:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pheval_disease_results").mkdir(parents=True, exist_ok=True)

    lookup = build_lookup()
    json_files = sorted(LLM_RESULTS_DIR.glob("patient_*.json"))
    print(f"Found {len(json_files)} result files\n")

    success = skipped = failed = 0

    for filepath in json_files:
        patient_id = filepath.stem
        orig_stem  = lookup.get(patient_id)

        if not orig_stem:
            print(f"  skip  {patient_id} — no lookup entry")
            skipped += 1
            continue

        phenopacket_path = PHENOPACKET_DIR / f"{orig_stem}.json"
        if not phenopacket_path.exists():
            print(f"  skip  {patient_id} — no phenopacket")
            skipped += 1
            continue

        data = json.loads(filepath.read_text())
        if "error" in data or not data.get("top_diseases"):
            print(f"  skip  {patient_id} — error or no diseases")
            skipped += 1
            continue

        records = []
        for d in data["top_diseases"]:
            disease_id   = d.get("disease_id", "").strip()
            disease_name = d.get("disease_name", "").strip()
            score        = float(d.get("score", 0.0))
            if disease_id:
                records.append({
                    "disease_name":       disease_name or disease_id,
                    "disease_identifier": disease_id,
                    "score":              score,
                })

        if not records:
            print(f"  skip  {patient_id} — no valid disease records")
            skipped += 1
            continue

        df = pl.DataFrame(records)

        try:
            generate_disease_result(
                results         = df,
                sort_order      = SortOrder.DESCENDING,
                output_dir      = OUTPUT_DIR,
                result_path     = phenopacket_path,
                phenopacket_dir = PHENOPACKET_DIR,
            )
            top1 = records[0]["disease_identifier"]
            print(f"  ok  {patient_id} -> {orig_stem}  top: {top1}")
            success += 1

        except Exception as e:
            print(f"  error  {patient_id} — {e}")
            failed += 1

    print(f"\nDone.  ok {success}  skipped {skipped}  failed {failed}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"""
Next — benchmark:
  cat > benchmark_config_disease.yaml << 'EOF'
benchmark_name: llm_disease_correct
runs:
  - run_identifier: claude_disease_level
    results_dir: /data/home/bt251044/p2p-work/{OUTPUT_DIR}
    phenopacket_dir: /data/home/bt251044/p2p-work/{PHENOPACKET_DIR}
    gene_analysis: false
    variant_analysis: false
    disease_analysis: true
    threshold:
    score_order: descending
plot_customisation:
  gene_plots:
    plot_type: bar_cumulative
    rank_plot_title:
    roc_curve_title:
    precision_recall_title:
  disease_plots:
    plot_type: bar_cumulative
    rank_plot_title:
    roc_curve_title:
    precision_recall_title:
  variant_plots:
    plot_type: bar_cumulative
    rank_plot_title:
    roc_curve_title:
    precision_recall_title:
EOF
  pheval-utils benchmark --run-yaml benchmark_config_disease.yaml
""")


if __name__ == "__main__":
    main()
