"""
convert_to_pheval.py
====================
Convert agentic pipeline results to PhEval gene result parquet files.

Uses generate_gene_result with synthetic_patients_with_genes/ as
phenopacket_dir — PhEval determines true positives from the
interpretations field automatically.

Usage:
    python convert_to_pheval.py

Expects:
    llm_results_agentic/     — JSON results from run_pipeline.py
    synthetic_patients_with_genes/  — gene-annotated phenopackets
    synthetic_patients_lookup.csv   — patient_001 → OMIM stem mapping
"""

import csv
import json
from pathlib import Path

try:
    import polars as pl
    from pheval.post_processing.post_processing import generate_gene_result, SortOrder
    HAS_PHEVAL = True
except ImportError:
    HAS_PHEVAL = False
    print("WARNING: pheval not installed. Run: pip install pheval")

# ── Paths ──────────────────────────────────────────────────────────────────
LLM_RESULTS_DIR  = Path("llm_results_agentic")
OUTPUT_DIR       = Path("pheval_gene_results_agentic")
PHENOPACKET_DIR  = Path("synthetic_patients_with_genes")
LOOKUP_CSV       = Path("synthetic_patients_lookup.csv")


def build_lookup() -> dict[str, str]:
    """Build patient_001 → OMIM_100700_patient_1 mapping."""
    lookup = {}
    if LOOKUP_CSV.exists():
        with open(LOOKUP_CSV) as f:
            for row in csv.DictReader(f):
                new_stem  = Path(row["new_file"]).stem
                orig_stem = Path(row["original_file"]).stem
                lookup[new_stem] = orig_stem
    return lookup


def convert_results():
    if not HAS_PHEVAL:
        print("pheval not available — install it first")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pheval_gene_results").mkdir(parents=True, exist_ok=True)

    lookup = build_lookup()
    json_files = sorted(LLM_RESULTS_DIR.glob("patient_*.json"))
    print(f"Found {len(json_files)} result files to convert\n")

    success = skipped = failed = 0

    for filepath in json_files:
        patient_id = filepath.stem

        # Map to OMIM stem
        orig_stem = lookup.get(patient_id)
        if not orig_stem:
            print(f"  skip  {patient_id} — no lookup entry")
            skipped += 1
            continue

        # Check gene-annotated phenopacket exists
        phenopacket_path = PHENOPACKET_DIR / f"{orig_stem}.json"
        if not phenopacket_path.exists():
            print(f"  skip  {patient_id} — no gene-annotated phenopacket (42 expected)")
            skipped += 1
            continue

        # Load result
        data = json.loads(filepath.read_text())
        if "error" in data or not data.get("top_genes"):
            print(f"  skip  {patient_id} — error or no genes in result")
            skipped += 1
            continue

        # Build Polars DataFrame
        records = []
        for g in data["top_genes"]:
            symbol = g.get("gene_symbol", "").strip()
            if symbol:
                records.append({
                    "gene_symbol":     symbol,
                    "gene_identifier": symbol,
                    "score":           float(g.get("score", 0.0)),
                })

        if not records:
            print(f"  skip  {patient_id} — no valid gene records")
            skipped += 1
            continue

        df = pl.DataFrame(records)

        try:
            generate_gene_result(
                results         = df,
                sort_order      = SortOrder.DESCENDING,
                output_dir      = OUTPUT_DIR,
                result_path     = phenopacket_path,
                phenopacket_dir = PHENOPACKET_DIR,
            )
            n_tools = len(data.get("tool_calls", []))
            print(f"  ✓  {patient_id} → {orig_stem}  ({len(records)} genes, {n_tools} OMIM calls)")
            success += 1

        except Exception as e:
            print(f"  ✗  {patient_id} — {e}")
            failed += 1

    print(f"\nDone.  ✓ {success}  skip {skipped}  ✗ {failed}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"\nNext — benchmark with PhEval:")
    print(f"""
  pheval-utils benchmark --run-yaml benchmark_config_agentic.yaml

  # benchmark_config_agentic.yaml:
  benchmark_name: agentic_pipeline
  runs:
    - run_identifier: claude_agent_omim
      results_dir: {OUTPUT_DIR.resolve()}
      phenopacket_dir: {PHENOPACKET_DIR.resolve()}
      gene_analysis: true
      variant_analysis: false
      disease_analysis: false
      threshold:
      score_order: descending
""")


if __name__ == "__main__":
    convert_results()
