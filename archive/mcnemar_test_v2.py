import pickle
from itertools import combinations
from statsmodels.stats.contingency_tables import mcnemar
import csv

with open("verified_correctness.pkl", "rb") as f:
    all_correctness = pickle.load(f)

approach_names = list(all_correctness.keys())
print(f"Approaches available: {approach_names}\n")

results = []
for a, b in combinations(approach_names, 2):
    shared_patients = set(all_correctness[a].keys()) & set(all_correctness[b].keys())
    if not shared_patients:
        print(f"WARNING: no shared patients between {a} and {b}, skipping")
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
        "approach_A": a, "approach_B": b,
        "chi2": round(result.statistic, 4),
        "p_value": round(result.pvalue, 6),
        "significance": "***" if result.pvalue < 0.001 else "**" if result.pvalue < 0.01 else "*" if result.pvalue < 0.05 else "ns",
        "A_only_correct": a_only, "B_only_correct": b_only,
        "both_correct": both, "neither_correct": neither,
        "n_shared": len(shared_patients),
    })

with open("mcnemar_verified.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\nSaved {len(results)} comparisons to mcnemar_verified.csv\n")
print("--- Summary (sorted by p-value) ---")
for r in sorted(results, key=lambda x: x["p_value"]):
    print(f"{r['approach_A']} vs {r['approach_B']}: chi2={r['chi2']}, p={r['p_value']} {r['significance']} "
          f"(both={r['both_correct']}, A_only={r['A_only_correct']}, B_only={r['B_only_correct']}, "
          f"neither={r['neither_correct']}, n={r['n_shared']})")