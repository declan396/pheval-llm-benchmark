"""
stats_analysis.py
=================
Statistical analysis for PhEval LLM benchmark dissertation.

1. Wilson 95% confidence intervals for top-1 accuracy (all approaches)
2. McNemar's pairwise significance tests (all pairs)
3. Heatmap of p-values saved as figures/pvalue_heatmap.png

Usage:
    python stats/stats_analysis.py

Requires: scipy, statsmodels, matplotlib, seaborn, numpy
    pip install statsmodels seaborn
"""

import csv
import json
from pathlib import Path
from scipy.stats import chi2 as chi2_dist
from statsmodels.stats.proportion import proportion_confint
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

BASE          = Path("C:/Users/decla/PycharmProjects/Phenopackets_AI")
PHENO_DIR     = BASE / "synthetic_patients_with_genes"
LOOKUP_CSV    = BASE / "synthetic_patients_lookup.csv"
FIGURES_DIR   = BASE / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# ── Approach definitions ───────────────────────────────────────────────────
APPROACHES = {
    "RAG v2":               BASE / "llm_results_rag_v2",
    "RAG + Agentic":        BASE / "llm_results_rag_agentic",
    "RAG + Exomiser":       BASE / "llm_results_rag_exomiser",
    "Phenotype-only":       BASE / "llm_results",
    "Exomiser-assisted":    BASE / "llm_results_exomiser_assisted_sonnet",
    "Exomiser no-anchor":   BASE / "llm_results_exomiser_no_anchor",
    "CoT (Haiku)":          BASE / "llm_results_cot",
}

# PhEval top-1 percentages (from benchmark) and n for CI calculation
PHEVAL_RESULTS = {
    "RAG v2":             (35.8, 158),
    "RAG + Agentic":      (35.2, 158),
    "RAG + Exomiser":     (31.5, 158),
    "Phenotype-only":     (12.7, 158),
    "Exomiser-assisted":  (9.7,  158),
    "Exomiser no-anchor": (9.1,  158),
    "CoT (Haiku)":        (7.3,  158),
    "Exomiser":           (58.4, 149),
}


# ── Data loading ───────────────────────────────────────────────────────────
def build_lookup() -> dict:
    lookup = {}
    with open(LOOKUP_CSV) as f:
        for row in csv.DictReader(f):
            lookup[Path(row["new_file"]).stem] = Path(row["original_file"]).stem
    return lookup


def get_true_gene(pheno_path: Path) -> str | None:
    try:
        data = json.loads(pheno_path.read_text())
        for interp in data.get("interpretations", []):
            for gi in interp.get("diagnosis", {}).get("genomicInterpretations", []):
                gene = gi.get("gene", {}).get("symbol", "")
                if gene:
                    return gene.upper()
    except Exception:
        pass
    return None


def get_top1_gene(result_path: Path) -> str | None:
    try:
        data = json.loads(result_path.read_text())
        if "error" in data:
            return None
        genes = sorted(data.get("top_genes", []), key=lambda g: g.get("rank", 999))
        return genes[0].get("gene_symbol", "").upper() if genes else None
    except Exception:
        return None


def get_correctness(results_dir: Path, lookup: dict) -> dict:
    correct = {}
    if not results_dir.exists():
        return correct
    for f in sorted(results_dir.glob("patient_*.json")):
        pid      = f.stem
        orig     = lookup.get(pid)
        if not orig:
            continue
        pheno    = PHENO_DIR / f"{orig}.json"
        if not pheno.exists():
            continue
        true_g   = get_true_gene(pheno)
        if not true_g:
            continue
        pred_g   = get_top1_gene(f)
        correct[pid] = 1 if (pred_g and pred_g == true_g) else 0
    return correct


# ── Statistical functions ──────────────────────────────────────────────────
def wilson_ci(n_correct: int, n_total: int, alpha: float = 0.05):
    lo, hi = proportion_confint(n_correct, n_total, alpha=alpha, method="wilson")
    return lo * 100, hi * 100


def mcnemar(correct_a: dict, correct_b: dict):
    patients = sorted(set(correct_a) & set(correct_b))
    n = len(patients)
    if n == 0:
        return None, 1.0, 0, 0
    b = sum(correct_a[p] == 1 and correct_b[p] == 0 for p in patients)
    c = sum(correct_a[p] == 0 and correct_b[p] == 1 for p in patients)
    if b + c == 0:
        return 0.0, 1.0, b, c
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p    = 1 - chi2_dist.cdf(stat, df=1)
    return stat, p, b, c


def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    lookup = build_lookup()

    # Load correctness for each approach
    print("Loading per-patient correctness...\n")
    results = {}
    for name, path in APPROACHES.items():
        correct = get_correctness(path, lookup)
        results[name] = correct
        n_c = sum(correct.values())
        n   = len(correct)
        print(f"  {name:<25} {n_c}/{n} ({100*n_c/n:.1f}%)" if n > 0 else f"  {name:<25} NOT FOUND")

    # ── 1. Confidence Intervals ────────────────────────────────────────────
    print("\n" + "─" * 75)
    print("Wilson 95% Confidence Intervals (from PhEval benchmarked top-1 %)")
    print("─" * 75)
    print(f"{'Approach':<25} {'Top-1':>7} {'95% CI Lower':>14} {'95% CI Upper':>14}  {'n':>5}")
    print("─" * 75)

    ci_rows = []
    for name, (pct, n) in sorted(PHEVAL_RESULTS.items(), key=lambda x: -x[1][0]):
        n_correct = round(pct / 100 * n)
        lo, hi    = wilson_ci(n_correct, n)
        print(f"{name:<25} {pct:>6.1f}%  {lo:>12.1f}%  {hi:>12.1f}%  {n:>5}")
        ci_rows.append({"approach": name, "top1_pct": pct, "ci_lower": round(lo, 1),
                        "ci_upper": round(hi, 1), "n": n})

    # Save CI table
    with open(BASE / "stats" / "confidence_intervals.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ci_rows[0].keys())
        w.writeheader()
        w.writerows(ci_rows)
    print(f"\nSaved to stats/confidence_intervals.csv")

    # ── 2. All pairwise McNemar's ──────────────────────────────────────────
    names    = list(results.keys())
    n_appr   = len(names)
    p_matrix = np.ones((n_appr, n_appr))
    s_matrix = [["" for _ in range(n_appr)] for _ in range(n_appr)]

    print("\n" + "─" * 75)
    print("All pairwise McNemar's tests")
    print("─" * 75)

    mcnemar_rows = []
    for i, na in enumerate(names):
        for j, nb in enumerate(names):
            if i >= j:
                continue
            if not results[na] or not results[nb]:
                continue
            stat, p, b, c = mcnemar(results[na], results[nb])
            if stat is None:
                continue
            p_matrix[i][j] = p
            p_matrix[j][i] = p
            s_matrix[i][j] = sig_stars(p)
            s_matrix[j][i] = sig_stars(p)
            p_str = "< 0.001" if p < 0.001 else f"{p:.3f}"
            print(f"  {na:<25} vs {nb:<25} χ²={stat:6.2f} p={p_str:>7} {sig_stars(p)}")
            mcnemar_rows.append({
                "A": na, "B": nb,
                "chi2": round(stat, 4), "p": round(p, 6),
                "sig": sig_stars(p), "A_only": b, "B_only": c,
            })

    with open(BASE / "stats" / "mcnemar_all_pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=mcnemar_rows[0].keys())
        w.writeheader()
        w.writerows(mcnemar_rows)

    # ── 3. P-value heatmap ─────────────────────────────────────────────────
    print("\nGenerating p-value heatmap...")

    # Mask diagonal and upper triangle (show lower triangle only)
    mask = np.zeros_like(p_matrix, dtype=bool)
    for i in range(n_appr):
        for j in range(n_appr):
            if i <= j:
                mask[i][j] = True

    # Log-transform p-values for colour scale
    # p=1 (diagonal/same) -> white, p<0.001 -> dark
    log_p = -np.log10(np.clip(p_matrix, 1e-10, 1.0))
    log_p_masked = np.where(mask, np.nan, log_p)

    short_names = [n.replace(" (Haiku)", "\n(Haiku)").replace("+ ", "+\n")
                   for n in names]

    fig, ax = plt.subplots(figsize=(9, 7))

    cmap = sns.color_palette("Blues", as_cmap=True)
    im   = ax.imshow(log_p_masked, cmap=cmap, vmin=0, vmax=4, aspect="auto")

    # Annotate cells with significance stars
    for i in range(n_appr):
        for j in range(n_appr):
            if mask[i][j]:
                continue
            stars = s_matrix[i][j]
            p_val = p_matrix[i][j]
            color = "white" if log_p[i][j] > 2 else "black"
            p_str = "< 0.001" if p_val < 0.001 else f"{p_val:.3f}"
            ax.text(j, i, f"{stars}\n{p_str}", ha="center", va="center",
                    fontsize=8, color=color, fontweight="bold" if stars != "ns" else "normal")

    ax.set_xticks(range(n_appr))
    ax.set_yticks(range(n_appr))
    ax.set_xticklabels(short_names, rotation=35, ha="right", fontsize=9)
    ax.set_yticklabels(short_names, fontsize=9)

    cbar = plt.colorbar(im, ax=ax, shrink=0.7)
    cbar.set_label("-log₁₀(p-value)", fontsize=10)
    cbar.set_ticks([0, 1, 2, 3, 4])
    cbar.set_ticklabels(["1.0", "0.1", "0.01", "0.001", "< 0.001"])

    ax.set_title("Pairwise McNemar's test p-values\n(gene-level top-1 accuracy, n=158)",
                 fontsize=12, pad=15)

    # Add legend for significance
    from matplotlib.patches import Patch
    legend = [
        Patch(facecolor="#08306b", label="*** p < 0.001"),
        Patch(facecolor="#2171b5", label="** p < 0.01"),
        Patch(facecolor="#6baed6", label="* p < 0.05"),
        Patch(facecolor="#deebf7", label="ns p ≥ 0.05"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=8,
              bbox_to_anchor=(1.0, 1.0), framealpha=0.9)

    plt.tight_layout()
    out_png = FIGURES_DIR / "pvalue_heatmap.png"
    out_svg = FIGURES_DIR / "pvalue_heatmap.svg"
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    print(f"Saved: {out_png}")
    print(f"Saved: {out_svg}")
    plt.show()

    # ── 4. CI bar chart ────────────────────────────────────────────────────
    print("Generating confidence interval bar chart...")

    ci_data = sorted(ci_rows, key=lambda x: -x["top1_pct"])
    names_ci  = [r["approach"] for r in ci_data]
    tops      = [r["top1_pct"] for r in ci_data]
    lowers    = [r["top1_pct"] - r["ci_lower"] for r in ci_data]
    uppers    = [r["ci_upper"] - r["top1_pct"] for r in ci_data]
    colors_ci = ["#1D9E75" if n == "Exomiser" else
                 "#2a78d6" if "RAG" in n else
                 "#888780" for n in names_ci]

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    bars = ax2.bar(names_ci, tops, color=colors_ci,
                   yerr=[lowers, uppers], capsize=4,
                   error_kw={"elinewidth": 1.5, "ecolor": "#444"},
                   edgecolor="white", linewidth=0.5)

    ax2.set_ylabel("Top-1 accuracy (%)", fontsize=11)
    ax2.set_title("Gene-level top-1 accuracy with 95% Wilson confidence intervals\n(n=158 patients with known Mendelian gene)",
                  fontsize=11)
    ax2.set_ylim(0, 70)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    plt.xticks(rotation=30, ha="right", fontsize=9)

    for bar, val in zip(bars, tops):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out2_png = FIGURES_DIR / "top1_ci_barchart.png"
    out2_svg = FIGURES_DIR / "top1_ci_barchart.svg"
    plt.savefig(out2_png, dpi=150, bbox_inches="tight")
    plt.savefig(out2_svg, bbox_inches="tight")
    print(f"Saved: {out2_png}")
    print(f"Saved: {out2_svg}")
    plt.show()

    print("\nAll done.")


if __name__ == "__main__":
    main()