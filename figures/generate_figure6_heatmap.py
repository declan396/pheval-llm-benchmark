import matplotlib.pyplot as plt
import numpy as np
import csv

# Map your script's approach names to display names
name_map = {
    "rag_exomiser": "RAG+Exomiser",
    "exomiser_anchored_5g": "Exomiser 5g",
    "exomiser_anchored_10g": "Exomiser 10g",
    "exomiser_no_anchor": "Exomiser no-anchor",
    "rag_v2": "RAG v2",
    "rag_agentic": "RAG+Agentic",
    "phenotype_only": "Phenotype-only",
    "cot": "CoT",
}
approaches = ["RAG+Exomiser", "Exomiser 5g", "Exomiser 10g", "Exomiser no-anchor",
              "RAG v2", "RAG+Agentic", "Phenotype-only", "CoT"]

# Read p-values directly from the CSV, no hand-typed dictionary
p_matrix = {}
with open("mcnemar_final_with_phenotype.csv") as f:
    for row in csv.DictReader(f):
        a = name_map[row["approach_A"]]
        b = name_map[row["approach_B"]]
        p_matrix[(a, b)] = float(row["p_value"])

n = len(approaches)
matrix = np.full((n, n), np.nan)
missing = []
for i, a in enumerate(approaches):
    for j, b in enumerate(approaches):
        if i < j:
            p = p_matrix.get((a, b)) or p_matrix.get((b, a))
            if p is None:
                missing.append((a, b))
            matrix[j, i] = p

if missing:
    print(f"WARNING: {len(missing)} pairs missing from CSV: {missing}")
else:
    print("All 28 pairs found, no gaps.")

fig, ax = plt.subplots(figsize=(10, 9))
log_matrix = -np.log10(np.clip(matrix, 1e-10, 1))
im = ax.imshow(log_matrix, cmap="Blues", vmin=0, vmax=6)

for i in range(n):
    for j in range(n):
        if not np.isnan(matrix[i, j]):
            p = matrix[i, j]
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            label = f"{sig}\n{p:.3f}" if p >= 0.001 else f"{sig}\n<0.001"
            color = "white" if log_matrix[i, j] > 3 else "black"
            ax.text(j, i, label, ha="center", va="center", fontsize=7.5, color=color)

ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels(approaches, rotation=45, ha="right")
ax.set_yticklabels(approaches)
ax.set_title("Pairwise McNemar's test p-values\n(gene-level top-1 accuracy, n=139-158)", fontsize=12)
plt.colorbar(im, label="-log10(p-value)")
plt.tight_layout()
plt.savefig("figure6_mcnemar_heatmap_8approaches_v2.png", dpi=300)
print("Saved figure6_mcnemar_heatmap_8approaches_v2.png")