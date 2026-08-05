import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

fig, axes = plt.subplots(1, 2, figsize=(16, 10))

# ── Figure A: Study pipeline ───────────────────────────────────────────────
ax = axes[0]
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis('off')
ax.set_title('Figure A — Overall study pipeline', fontsize=11, pad=10)

def box(ax, x, y, w, h, text, subtext=None, color='#E1F5EE', tcolor='#085041'):
    rect = mpatches.FancyBboxPatch((x, y), w, h,
        boxstyle="round,pad=0.1", facecolor=color, edgecolor=tcolor, linewidth=0.8)
    ax.add_patch(rect)
    if subtext:
        ax.text(x+w/2, y+h*0.65, text, ha='center', va='center',
                fontsize=8, fontweight='bold', color=tcolor)
        ax.text(x+w/2, y+h*0.28, subtext, ha='center', va='center',
                fontsize=6.5, color=tcolor)
    else:
        ax.text(x+w/2, y+h/2, text, ha='center', va='center',
                fontsize=8, fontweight='bold', color=tcolor)

def arrow(ax, x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle='->', color='#444', lw=1.0))

# Labels
for label, y in [('DATA PREPARATION', 13.5), ('APPROACHES', 9.5), ('EVALUATION', 5.5)]:
    ax.text(0.2, y, label, fontsize=7, color='#888', fontweight='bold')
    ax.axhline(y-0.2, color='#ddd', lw=0.5, xmin=0.02, xmax=0.98)

box(ax, 2.5, 11.8, 5, 1.2, 'HPOA v2026-02-16', '12,996 disease–phenotype associations', '#E1F5EE', '#085041')
arrow(ax, 5, 11.8, 5, 11.2)
box(ax, 2.5, 10.0, 5, 1.1, 'phenotype2phenopacket', '200 synthetic phenopackets · 200 diseases', '#E1F5EE', '#085041')

# Branch
ax.annotate('', xy=(2.5, 9.2), xytext=(4, 10.0),
    arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
ax.annotate('', xy=(7.5, 9.2), xytext=(6, 10.0),
    arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))

box(ax, 0.3, 8.0, 3.8, 1.1, 'Gene annotation', 'p2p add-genes → 158/200', '#E1F5EE', '#085041')
box(ax, 5.9, 8.0, 3.8, 1.1, 'Redaction', 'Strip disease, gene, variants', '#E1F5EE', '#085041')

arrow(ax, 2.2, 8.0, 2.2, 7.2)
arrow(ax, 7.8, 8.0, 7.8, 7.2)

box(ax, 0.3, 5.9, 3.8, 1.2, 'Exomiser v15 (baseline)', 'Phenotype-only · Apocrita HPC · n=149', '#FAEEDA', '#633806')
box(ax, 5.0, 5.5, 4.8, 2.0, 'LLM approaches (×10)\nPhenotype-only · Exomiser-assisted\nCoT · Disease-level · RAG v1/v2\nRAG+Agentic · RAG+Exomiser', None, '#E6F1FB', '#0C447C')
ax.text(5.0+4.8/2, 5.5+2.0/2, 'LLM approaches (×10)\nPhenotype-only · Exomiser-assisted\nCoT · Disease-level · RAG v1/v2\nRAG+Agentic · RAG+Exomiser',
        ha='center', va='center', fontsize=7, color='#0C447C')

arrow(ax, 2.2, 5.9, 2.2, 5.1)
arrow(ax, 7.4, 5.5, 5.5, 5.1)

box(ax, 1.5, 3.8, 7, 1.2, 'PhEval v0.7.13', 'generate_gene_result / generate_disease_result · Top-1, Top-3, Top-5, MRR', '#EEEDFE', '#26215C')
arrow(ax, 5, 3.8, 5, 3.0)
box(ax, 1.5, 1.8, 7, 1.1, 'Statistical analysis', "McNemar's tests · Wilson 95% CIs", '#F1EFE8', '#2C2C2A')

# ── Figure B: RAG + Agentic architecture ──────────────────────────────────
ax2 = axes[1]
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 14)
ax2.axis('off')
ax2.set_title('Figure B — RAG + Agentic architecture', fontsize=11, pad=10)

for label, y in [('INDEX CONSTRUCTION (once)', 13.5), ('RUNTIME — per patient', 10.5), ('AGENTIC LOOP (max 3 rounds)', 7.2), ('OUTPUT', 3.2)]:
    ax2.text(0.2, y, label, fontsize=7, color='#888', fontweight='bold')
    ax2.axhline(y-0.2, color='#ddd', lw=0.5, xmin=0.02, xmax=0.98)

# Phase 1
box(ax2, 0.2, 11.8, 2.2, 1.0, 'HPOA', '12,996 diseases', '#E1F5EE', '#085041')
ax2.annotate('', xy=(2.8, 12.3), xytext=(2.4, 12.3), arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
box(ax2, 2.8, 11.8, 2.8, 1.0, 'HPO label extraction', '"Intellectual disability"', '#E1F5EE', '#085041')
ax2.annotate('', xy=(6.2, 12.3), xytext=(5.6, 12.3), arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
box(ax2, 6.2, 11.8, 2.5, 1.0, 'Sentence embedding', 'all-MiniLM-L6-v2', '#E1F5EE', '#085041')
ax2.annotate('', xy=(9.2, 12.3), xytext=(8.7, 12.3), arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
box(ax2, 9.2, 11.8, 0.7, 1.0, 'Chroma\nDB', None, '#EEEDFE', '#26215C')

# Phase 2
box(ax2, 0.2, 9.2, 3.2, 1.0, 'Redacted phenopacket', 'HPO labels only', '#F1EFE8', '#2C2C2A')
ax2.annotate('', xy=(3.8, 9.7), xytext=(3.4, 9.7), arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
box(ax2, 3.8, 9.2, 2.8, 1.0, 'Query embedding', 'cosine similarity', '#E1F5EE', '#085041')
ax2.annotate('', xy=(7.0, 9.7), xytext=(6.6, 9.7), arrowprops=dict(arrowstyle='->', color='#444', lw=0.8))
box(ax2, 7.0, 9.2, 2.9, 1.0, 'Top-10 diseases', 'name · similarity · genes', '#E1F5EE', '#085041')
# ChromaDB feeds retrieval
ax2.annotate('', xy=(9.55, 11.8), xytext=(9.55, 10.2),
    arrowprops=dict(arrowstyle='->', color='#888', lw=0.7, linestyle='dashed'))

# Claude
arrow(ax2, 1.8, 9.2, 3.5, 8.3)
arrow(ax2, 8.5, 9.2, 6.5, 8.3)
box(ax2, 1.5, 7.3, 7, 0.9, 'Claude Sonnet 4.6', 'Reasons over retrieved diseases + HPO terms · decides to call tool or return JSON', '#E6F1FB', '#0C447C')

# Tools
arrow(ax2, 2.5, 7.3, 1.5, 6.2)
arrow(ax2, 5.0, 7.3, 5.0, 6.2)
arrow(ax2, 7.5, 7.3, 8.5, 6.2)

box(ax2, 0.2, 4.8, 2.8, 1.3, 'Monarch Initiative', 'Gene→disease lookup', '#FAECE7', '#4A1B0C')
box(ax2, 3.6, 4.8, 2.8, 1.3, 'PubMed', 'Literature search\nNCBI eUtils', '#FAECE7', '#4A1B0C')
box(ax2, 7.0, 4.8, 2.8, 1.3, 'ClinVar', 'Pathogenic variants\nNCBI eUtils', '#FAECE7', '#4A1B0C')

# Return arrows dashed
for x in [1.6, 5.0, 8.4]:
    ax2.annotate('', xy=(5.0, 7.3), xytext=(x, 6.1),
        arrowprops=dict(arrowstyle='->', color='#888', lw=0.7,
                       connectionstyle='arc3,rad=0.1', linestyle='dashed'))

# Output
arrow(ax2, 5.0, 7.3, 5.0, 3.5)
box(ax2, 2.0, 2.4, 6, 1.0, 'Ranked gene list (JSON)', 'Top-10 genes · score · reasoning', '#F1EFE8', '#2C2C2A')
arrow(ax2, 5.0, 2.4, 5.0, 1.6)
box(ax2, 2.0, 0.6, 6, 1.0, 'PhEval benchmarking', 'Top-1 / Top-3 / Top-5 / MRR', '#EEEDFE', '#26215C')

plt.tight_layout(pad=2)
plt.savefig('figures/pipeline_diagrams.png', dpi=150, bbox_inches='tight')
plt.savefig('figures/pipeline_diagrams.svg', bbox_inches='tight')
print("Saved figures/pipeline_diagrams.png and figures/pipeline_diagrams.svg")
plt.show()