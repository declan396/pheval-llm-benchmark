import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors

approaches = ["RAG+Exomiser", "Exomiser 5g", "Exomiser 10g", "Exomiser no-anchor", "RAG v2", "RAG+Agentic", "CoT"]

# p-values matrix (upper triangle), from mcnemar_verified.csv
p_matrix = {
    ("RAG+Exomiser", "Exomiser 5g"): 0.00033,
    ("RAG+Exomiser", "Exomiser 10g"): 0.000023,
    ("RAG+Exomiser", "Exomiser no-anchor"): 0.000001,
    ("RAG+Exomiser", "RAG v2"): 0.000012,
    ("RAG+Exomiser", "RAG+Agentic"): 0.000001,
    ("RAG+Exomiser", "CoT"): 0.0,
    ("Exomiser 5g", "Exomiser 10g"): 0.723674,
    ("Exomiser 5g", "Exomiser no-anchor"): 0.061369,
    ("Exomiser 5g", "RAG v2"): 0.104833,
    ("Exomiser 5g", "RAG+Agentic"): 0.05527,
    ("Exomiser 5g", "CoT"): 0.0,
    ("Exomiser 10g", "Exomiser no-anchor"): 0.2278,
    ("Exomiser 10g", "RAG v2"): 0.222469,
    ("Exomiser 10g", "RAG+Agentic"): 0.164915,
    ("Exomiser 10g", "CoT"): 0.0,
    ("Exomiser no-anchor", "RAG v2"): 0.635256,
    ("Exomiser no-anchor", "RAG+Agentic"): 0.521839,
    ("Exomiser no-anchor", "CoT"): 0.0,
    ("RAG v2", "RAG+Agentic"): 1.0,
    ("RAG v2", "CoT"): 0.0,
    ("RAG+Agentic", "CoT"): 0.0,
}

n = len(approaches)
matrix = np.full((n, n), np.nan)
for i, a in enumerate(approaches):
    for j, b in enumerate(approaches):
        if i < j:
            p = p_matrix.get((a, b)) or p_matrix.get((b, a))
            matrix[j, i] = p  # lower triangle

fig, ax = plt.subplots(figsize=(9, 8))
log_matrix = -np.log10(np.clip(matrix, 1e-10, 1))
im = ax.imshow(log_matrix, cmap="Blues", vmin=0, vmax=6)

for i in range(n):
    for j in range(n):
        if not np.isnan(matrix[i, j]):
            p = matrix[i, j]
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            label = f"{sig}\n{p:.3f}" if p >= 0.001 else f"{sig}\n<0.001"
            color = "white" if log_matrix[i, j] > 3 else "black"
            ax.text(j, i, label, ha="center", va="center", fontsize=8, color=color)

ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels(approaches, rotation=45, ha="right")
ax.set_yticklabels(approaches)
ax.set_title("Pairwise McNemar's test p-values\n(gene-level top-1 accuracy, n=144-158)", fontsize=12)
plt.colorbar(im, label="-log10(p-value)")
plt.tight_layout()
plt.savefig("figure6_mcnemar_heatmap_updated.png", dpi=300)
print("Saved figure6_mcnemar_heatmap_updated.png")