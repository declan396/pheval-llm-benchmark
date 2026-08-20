import polars as pl
from pathlib import Path
from itertools import combinations
from statsmodels.stats.contingency_tables import mcnemar
import csv

# ── Configuration ─────────────────────────────────────────────────────────────
APPROACH_DIRS = {
    "phenotype_only":        Path("pheval_gene_results_phenotype_only_correct/pheval_gene_results"),
    "cot":                   Path("pheval_gene_results_cot/pheval_gene_results"),
    "rag_v2":                Path("pheval_gene_results_rag_v2/pheval_gene_results"),
    "rag_agentic":           Path("pheval_gene_results_rag_agentic/pheval_gene_results"),
    "exomiser_no_anchor":    Path("pheval_gene_results_exomiser_no_anchor_fixed/pheval_gene_results"),
    "exomiser_anchored_5g":  Path("pheval_gene_results_correct/pheval_gene_results"),
    "exomiser_anchored_10g": Path("pheval_gene_results_exomiser_assisted_10genes/pheval_gene_results"),
    "rag_exomiser":          Path("pheval_gene_results_rag_exomiser/pheval_gene_results"),
}
# ──────────────────────────────────────────────────────────────────────────────


def get_top1_correctness(results_dir: Path) -> dict:
    """For each patient, return True if the top-ranked (rank=1) gene was a true positive."""
    correctness = {}
    for f in sorted(results_dir.glob("*-gene_result.parquet")):
        patient_id = f.stem.replace("-gene_result", "")
        df = pl.read_parquet(f)
        top1 = df.sort("rank").head(1)
        if len(top1) == 0:
            continue
        correctness[patient_id] = bool(top1["true_positive"][0])
    return correctness


def main():
    all_correctness = {}
    for name, path in APPROACH_DIRS.items():
        if not path.exists():
            print(f"WARNING: {path} does not exist, skipping {name}")
            continue
        all_correctness[name] = get_top1_correctness(path)
        print(f"{name}: loaded {len(all_correctness[name])} patients")

    approach_names = list(all_correctness.keys())

    results = []
    for a, b in combinations(approach_names, 2):
        shared_patients = set(all_correctness[a].keys()) & set(all_correctness[b].keys())
        if not shared_patients:
            continue

        a_only = b_only = both = neither = 0
        for pid in shared_patients:
            a_correct = all_correctness[a][pid]
            b_correct = all_correctness[b][pid]
            if a_correct and b_correct:
                both += 1
            elif a_correct and not b_correct:
                a_only += 1
            elif not a_correct and b_correct:
                b_only += 1
            else:
                neither += 1

        table = [[both, a_only], [b_only, neither]]
        result = mcnemar(table, exact=False, correction=True)

        results.append({
            "approach_A": a,
            "approach_B": b,
            "chi2": round(result.statistic, 4),
            "p_value": round(result.pvalue, 6),
            "significance": "***" if result.pvalue < 0.001 else "**" if result.pvalue < 0.01 else "*" if result.pvalue < 0.05 else "ns",
            "A_only_correct": a_only,
            "B_only_correct": b_only,
            "n_shared": len(shared_patients),
        })

    out_path = Path("mcnemar_full_comparison_matrix.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved {len(results)} pairwise comparisons to {out_path}")
    print("\n--- Summary (sorted by p-value) ---")
    for r in sorted(results, key=lambda x: x["p_value"]):
        print(f"{r['approach_A']} vs {r['approach_B']}: chi2={r['chi2']}, p={r['p_value']} {r['significance']}")


if __name__ == "__main__":
    main()