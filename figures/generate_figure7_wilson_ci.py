import matplotlib.pyplot as plt
import numpy as np
from statsmodels.stats.proportion import proportion_confint

data = [
    ("Exomiser", 58.4, 149, "green"),
    ("RAG+Exomiser\n(fixed)", 55.2, 158, "steelblue"),
    ("Exomiser 5g\n(fixed)", 43.6, 158, "steelblue"),
    ("Exomiser 10g\n(fixed)", 41.8, 158, "steelblue"),
    ("Exomiser\nno-anchor (fixed)", 38.8, 158, "steelblue"),
    ("RAG v2", 35.8, 158, "steelblue"),
    ("RAG+Agentic", 35.2, 158, "steelblue"),
    ("Phenotype-only", 12.7, 158, "gray"),
    ("CoT", 7.3, 158, "gray"),
]

names = [d[0] for d in data]
pct = [d[1] for d in data]
n = [d[2] for d in data]
colors = [d[3] for d in data]

ci_low, ci_high = [], []
for p, ni in zip(pct, n):
    k = round(p / 100 * ni)
    lo, hi = proportion_confint(k, ni, method="wilson")
    ci_low.append(p - lo * 100)
    ci_high.append(hi * 100 - p)

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(names))
ax.bar(x, pct, yerr=[ci_low, ci_high], capsize=5, color=colors)
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=45, ha="right")
ax.set_ylabel("Top-1 accuracy (%)")
ax.set_title("Gene-level top-1 accuracy with 95% Wilson confidence intervals\n(post-correction)")
plt.tight_layout()
plt.savefig("figure7_wilson_ci_updated.png", dpi=300)
print("Saved figure7_wilson_ci_updated.png")