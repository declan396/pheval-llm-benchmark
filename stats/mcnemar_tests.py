"""
mcnemar_tests.py
================
McNemar's test for pairwise comparison of gene prioritisation approaches.

Reads LLM JSON results and gene-annotated phenopackets to determine
per-patient top-1 correctness for each approach, then runs McNemar's test.

Usage:
    python stats/mcnemar_tests.py

Requires:
    - llm_results_*/ directories with patient JSON files
    - synthetic_patients_with_genes/ directory with gene-annotated phenopackets
    - synthetic_patients_lookup.csv for stem mapping
"""

import csv
import json
from pathlib import Path
from scipy.stats import chi2 as chi2_dist


# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path("C:/Users/decla/PycharmProjects/Phenopackets_AI")
PHENOPACKET_DIR = BASE / "synthetic_patients_with_genes"
LOOKUP_CSV      = BASE / "synthetic_patients_lookup.csv"

# Map approach name -> LLM results directory
APPROACHES = {
    "RAG v2 (labels)":         BASE / "llm_results_rag_v2",
    "RAG + Agentic":           BASE / "llm_results_rag_agentic",
    "RAG + Exomiser scores":   BASE / "llm_results_rag_exomiser",
    "Phenotype-only (Sonnet)": BASE / "llm_results",
    "Exomiser-assisted 5g":    BASE / "llm_results_exomiser_assisted_sonnet",
    "Exomiser no-anchor":      BASE / "llm_results_exomiser_no_anchor",
    "CoT (Haiku)":             BASE / "llm_results_cot",
}

COMPARISONS = [
    ("RAG v2 (labels)",         "Phenotype-only (Sonnet)",  "RAG v2 vs phenotype-only"),
    ("RAG v2 (labels)",         "RAG + Agentic",            "RAG v2 vs RAG + Agentic"),
    ("RAG v2 (labels)",         "RAG + Exomiser scores",    "RAG v2 vs RAG + Exomiser"),
    ("RAG v2 (labels)",         "Exomiser-assisted 5g",     "RAG v2 vs Exomiser-assisted"),
    ("RAG v2 (labels)",         "CoT (Haiku)",              "RAG v2 vs CoT"),
    ("Phenotype-only (Sonnet)", "Exomiser-assisted 5g",     "Phenotype-only vs Exomiser-assisted"),
    ("Phenotype-only (Sonnet)", "CoT (Haiku)",              "Phenotype-only vs CoT"),
    ("Phenotype-only (Sonnet)", "Exomiser no-anchor",       "Phenotype-only vs no-anchor"),
]


def build_lookup() -> dict[str, str]:
    """patient_001 -> OMIM_100700_patient_1"""
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


def get_true_gene(phenopacket_path: Path) -> str | None:
    """Extract causal gene symbol from gene-annotated phenopacket."""
    try:
        data = json.loads(phenopacket_path.read_text())
        for interp in data.get("interpretations", []):
            for genomic_interp in interp.get("diagnosis", {}).get("genomicInterpretations", []):
                gene = genomic_interp.get("gene", {}).get("symbol", "")
                if gene:
                    return gene.upper()
    except Exception:
        pass
    return None


def get_top1_gene(result_path: Path) -> str | None:
    """Get the top-ranked gene symbol from an LLM result JSON."""
    try:
        data = json.loads(result_path.read_text())
        if "error" in data:
            return None
        genes = data.get("top_genes", [])
        if not genes:
            return None
        # Sort by rank or score to get top-1
        genes_sorted = sorted(genes, key=lambda g: g.get("rank", 999))
        return genes_sorted[0].get("gene_symbol", "").upper() if genes_sorted else None
    except Exception:
        return None


def get_correctness(results_dir: Path, lookup: dict, phenopacket_dir: Path) -> dict[str, int]:
    """
    For each patient in results_dir, check if top-1 predicted gene matches true gene.
    Returns dict: patient_id -> 1 (correct) or 0 (incorrect)
    """
    correct = {}
    if not results_dir.exists():
        return correct

    for result_file in sorted(results_dir.glob("patient_*.json")):
        patient_id = result_file.stem
        orig_stem  = lookup.get(patient_id)
        if not orig_stem:
            continue

        phenopacket_path = Path(
            "C:/Users/decla/PycharmProjects/Phenopackets_AI/synthetic_patients_with_genes") / f"{orig_stem}.json"
        if not phenopacket_path.exists():
            continue  # patient has no known gene — skip

        true_gene = get_true_gene(phenopacket_path)
        if not true_gene:
            continue

        pred_gene = get_top1_gene(result_file)
        correct[patient_id] = 1 if (pred_gene and pred_gene == true_gene) else 0

    return correct


def mcnemar_test(correct_a, correct_b):
    patients = sorted(set(correct_a.keys()) & set(correct_b.keys()))
    n = len(patients)
    if n == 0:
        return None, 1.0, 0, 0, 0

    b = sum(correct_a[p] == 1 and correct_b[p] == 0 for p in patients)
    c = sum(correct_a[p] == 0 and correct_b[p] == 1 for p in patients)

    if b + c == 0:
        return 0.0, 1.0, b, c, n

    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p    = 1 - chi2_dist.cdf(stat, df=1)
    return stat, p, b, c, n


def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


def main():
    lookup = build_lookup()
    print(f"Lookup: {len(lookup)} patients\n")

    # Find phenopacket directory
    pheno_dir = PHENOPACKET_DIR
    if not pheno_dir.exists():
        pheno_dir = Path("synthetic_patients_with_genes")
    if not pheno_dir.exists():
        print("ERROR: synthetic_patients_with_genes/ not found")
        print("SCP from Apocrita:")
        print("  scp -r bt251044@login.hpc.qmul.ac.uk:/data/home/bt251044/p2p-work/synthetic_patients_with_genes .")
        return

    print("Loading per-patient top-1 correctness...\n")
    results = {}
    for name, path in APPROACHES.items():
        correct  = get_correctness(path, lookup, pheno_dir)
        n_correct = sum(correct.values())
        n_total   = len(correct)
        pct = 100 * n_correct / n_total if n_total > 0 else 0
        status = f"{n_correct}/{n_total} correct ({pct:.1f}%)"
        if not correct:
            status = "NOT FOUND"
        print(f"  {name:<30} {status}")
        results[name] = correct

    print("\n" + "─" * 85)
    print("McNemar's tests (Yates continuity correction, df=1)")
    print("─" * 85)
    print(f"{'Comparison':<45} {'χ²':>8} {'p':>9} {'sig':>4} {'A✓B✗':>6} {'A✗B✓':>6} {'n':>5}")
    print("─" * 85)

    rows = []
    for name_a, name_b, label in COMPARISONS:
        if name_a not in results or name_b not in results:
            print(f"  SKIP {label}")
            continue
        if not results[name_a] or not results[name_b]:
            print(f"  SKIP {label} — missing data")
            continue

        stat, p, b, c, n = mcnemar_test(results[name_a], results[name_b])
        if stat is None:
            continue

        p_str = "< 0.001" if p < 0.001 else f"{p:.3f}"
        print(f"{label:<45} {stat:>8.3f} {p_str:>9} {sig_stars(p):>4} {b:>6} {c:>6} {n:>5}")
        rows.append({
            "comparison": label, "approach_A": name_a, "approach_B": name_b,
            "chi2": round(stat, 4), "p_value": round(p, 6),
            "significance": sig_stars(p), "A_correct_B_wrong": b,
            "B_correct_A_wrong": c, "n_shared": n,
        })

    print("─" * 85)
    print("sig: *** p<0.001  ** p<0.01  * p<0.05  ns not significant")
    print("A✓B✗ = A correct, B wrong  |  A✗B✓ = A wrong, B correct")

    if rows:
        out = Path("stats/mcnemar_results.csv")
        out.parent.mkdir(exist_ok=True)
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()