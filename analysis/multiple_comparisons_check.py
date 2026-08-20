
import csv
from pathlib import Path

files = [
    "mcnemar_final_with_phenotype.csv",  # 28 gene-level comparisons
    "mcnemar_disease_level.csv",          # 3 disease-level comparisons
]

all_rows = []
for fname in files:
    p = Path(fname)
    if not p.exists():
        print(f"WARNING: {fname} not found, skipping")
        continue
    with open(p) as f:
        for row in csv.DictReader(f):
            row["source_file"] = fname
            all_rows.append(row)

n_tests = len(all_rows)
alpha = 0.05
bonferroni_threshold = alpha / n_tests

print(f"Total pairwise tests across all comparisons: {n_tests}")
print(f"Uncorrected alpha: {alpha}")
print(f"Bonferroni-corrected threshold: {bonferroni_threshold:.6f}\n")

survives = []
fails_after_correction = []
already_ns = []

for row in all_rows:
    p_val = float(row["p_value"])
    label = f"{row['approach_A']} vs {row['approach_B']} ({row['source_file']})"
    if p_val >= alpha:
        already_ns.append((label, p_val))
    elif p_val < bonferroni_threshold:
        survives.append((label, p_val))
    else:
        fails_after_correction.append((label, p_val))

print(f"Significant at uncorrected alpha=0.05: {len(survives) + len(fails_after_correction)}")
print(f"  Still significant after Bonferroni correction: {len(survives)}")
print(f"  No longer significant after Bonferroni correction: {len(fails_after_correction)}")
print(f"Already non-significant at uncorrected alpha: {len(already_ns)}\n")

if fails_after_correction:
    print("Comparisons that were significant uncorrected but NOT after Bonferroni correction:")
    for label, p in sorted(fails_after_correction, key=lambda x: x[1]):
        print(f"  {label}: p={p}")
else:
    print("No comparisons changed significance status after Bonferroni correction.")

# Holm-Bonferroni as a slightly less conservative alternative, worth reporting too
print("\n--- Holm-Bonferroni (step-down, less conservative) ---")
sorted_rows = sorted(all_rows, key=lambda r: float(r["p_value"]))
holm_fails = []
for i, row in enumerate(sorted_rows):
    p_val = float(row["p_value"])
    threshold = alpha / (n_tests - i)
    label = f"{row['approach_A']} vs {row['approach_B']} ({row['source_file']})"
    if p_val >= alpha:
        break  # already non-significant, no need to check further
    if p_val >= threshold:
        holm_fails.append((label, p_val, threshold))

if holm_fails:
    print("Comparisons that fail under Holm-Bonferroni (less conservative than plain Bonferroni):")
    for label, p, t in holm_fails:
        print(f"  {label}: p={p} (threshold at this rank: {t:.6f})")
else:
    print("All uncorrected-significant results survive Holm-Bonferroni correction too.")
