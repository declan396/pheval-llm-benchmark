import matplotlib.pyplot as plt
import numpy as np
from statsmodels.stats.proportion import proportion_confint

data = [
    ("RAG disease-level", 32.5, 200),
    ("Disease-level\n(Sonnet)", 9.0, 200),
    ("Disease-level\n(Haiku)", 2.5, 200),
]

names = [d[0] for d in data]
pct = [d[1] for d in data]
n = [d[2] for d in data]

ci_low, ci_high = [], []
for p, ni in zip(pct, n):
    k = round(p / 100 * ni)
    lo, hi = proportion_confint(k, ni, method="wilson")
    ci_low.append(p - lo * 100)
    ci_high.append(hi * 100 - p)

fig, ax = plt.subplots(figsize=(8, 5.5))   # wider + a bit taller — was (6, 5)
x = np.arange(len(names))
colors = ["steelblue", "#a6a6a6", "#595959"]  # Sonnet/Haiku now distinguishable
ax.bar(x, pct, yerr=[ci_low, ci_high], capsize=5, color=colors)
ax.set_xticks(x)
ax.set_xticklabels(names)
ax.set_ylabel("Top-1 accuracy (%)")
ax.set_title("Disease-level top-1 accuracy with 95% Wilson confidence intervals",
             fontsize=13, pad=12)   # slightly smaller so it fits; was default (~larger)

def sig_bracket(x1, x2, y, h, text):
    ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=1, color="black")
    ax.text((x1+x2)/2, y+h, text, ha="center", va="bottom", fontsize=9)

sig_bracket(0, 1, 42, 2, "***")
sig_bracket(0, 2, 48, 2, "***")
sig_bracket(1, 2, 15, 2, "***")

ax.set_ylim(0, 58)   # a touch more headroom for the note below

fig.text(0.5, 0.005,
         "Error bars: 95% Wilson CIs. Significance stars: McNemar's paired test (n=200 per pair), not CI overlap.",
         ha="center", fontsize=8, style="italic")

plt.tight_layout(rect=[0, 0.03, 1, 1])   # reserve space at bottom for the note
plt.savefig("figure_disease_level_significance.png", dpi=300, bbox_inches="tight")
print("Saved")