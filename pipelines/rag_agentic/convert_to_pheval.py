"""
convert_to_pheval.py
====================
Convert RAG + Monarch agentic results to PhEval gene result parquet files.

Run on Apocrita after SCP-ing results:
    python3 convert_to_pheval.py

Then benchmark:
    pheval-utils benchmark --run-yaml benchmark_config_rag_agentic.yaml
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
    print("ERROR: pheval not installed — run on Apocrita")

# ── Paths ──────────────────────────────────────────────────────────────────
LLM_RESULTS_DIR = Path("llm_results_rag_agentic")
OUTPUT_DIR      = Path("pheval_gene_results_rag_agentic")
PHENOPACKET_DIR = Path("synthetic_patients_with_genes")
LOOKUP_CSV      = Path("synthetic_patients_lookup.csv")


def build_lookup() -> dict[str, str]:
    lookup = {}
    if not LOOKUP_CSV.exists():
        print(f"WARNING: {LOOKUP_CSV} not found")
        return lookup
    with open(LOOKUP_CSV) as f:
        for row in csv.DictReader(f):
            new_stem  = Path(row["new_file"]).stem
            orig_stem = Path(row["original_file"]).stem
            lookup[new_stem] = orig_stem
    return lookup


def main():
    if not HAS_PHEVAL:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pheval_gene_results").mkdir(parents=True, exist_ok=True)

    lookup     = build_lookup()
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
        if "error" in data or not data.get("top_genes"):
            print(f"  skip  {patient_id} — error or no genes")
            skipped += 1
            continue

        records = [
            {
                "gene_symbol":     g["gene_symbol"].strip(),
                "gene_identifier": g["gene_symbol"].strip(),
                "score":           float(g.get("score", 0.0)),
            }
            for g in data["top_genes"]
            if g.get("gene_symbol")
        ]

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
            top1    = records[0]["gene_symbol"]
            print(f"  ok  {patient_id} → {orig_stem}  top: {top1}  tools: {n_tools}")
            success += 1

        except Exception as e:
            print(f"  error  {patient_id} — {e}")
            failed += 1

    print(f"\nDone.  ok {success}  skip {skipped}  failed {failed}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"""
Next — benchmark:
  cat > benchmark_config_rag_agentic.yaml << 'EOF'
benchmark_name: llm_rag_agentic
runs:
  - run_identifier: claude_rag_agentic
    results_dir: /data/home/bt251044/p2p-work/{OUTPUT_DIR}
    phenopacket_dir: /data/home/bt251044/p2p-work/{PHENOPACKET_DIR}
    gene_analysis: true
    variant_analysis: false
    disease_analysis: false
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
  pheval-utils benchmark --run-yaml benchmark_config_rag_agentic.yaml
""")


if __name__ == "__main__":
    main()
