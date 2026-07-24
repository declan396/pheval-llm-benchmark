import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Figure 4 — RAG v1 vs v2
labels4 = ['RAG v1\n(HPO IDs)', 'RAG v2\n(HPO labels)']
values4 = [1.2, 35.8]
colors4 = ['#888780', '#2a78d6']
bars = ax1.bar(labels4, values4, color=colors4, width=0.4, edgecolor='white')
ax1.set_ylim(0, 45)
ax1.set_ylabel('Top-1 accuracy (%)')
ax1.set_title('Figure 4 — HPO IDs vs labels (gene-level top-1)')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
for bar, val in zip(bars, values4):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{val}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

# Figure 5 — Disease-level vs MALCO
labels5 = ['MALCO Exomiser', 'Claude RAG\n(this work)', 'MALCO best LLM\n(o1-preview)',
           'Claude disease\n(Sonnet)', 'Claude disease\n(Haiku)']
values5 = [35.5, 32.5, 23.6, 9.0, 2.5]
colors5 = ['#88878099', '#2a78d6', '#88878099', '#2a78d680', '#2a78d680']
bars2 = ax2.barh(labels5, values5, color=colors5, edgecolor='white')
ax2.set_xlim(0, 42)
ax2.set_xlabel('Top-1 accuracy (%)')
ax2.set_title('Figure 5 — Disease-level top-1 vs MALCO')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
for bar, val in zip(bars2, values5):
    ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val}%', ha='left', va='center', fontsize=10)

plt.tight_layout(pad=2)
plt.savefig('figures_4_and_5.png', dpi=150, bbox_inches='tight')
plt.savefig('figures_4_and_5.svg', bbox_inches='tight')
print("Saved figures_4_and_5.png and figures_4_and_5.svg")
plt.show()