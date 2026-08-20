import duckdb
from pathlib import Path

# Map each approach to its duckdb file and summary table name

approaches = {
    "Exomiser": ("exomiser_gene_results_correct.duckdb", "exomiser_gene_results_correct_gene_summary"),
    "RAG + Exomiser (fixed)": ("llm_rag_exomiser_fixed.duckdb", "llm_rag_exomiser_fixed_gene_summary"),
    "Exomiser-assisted 5g (fixed)": ("llm_exomiser_assisted_fixed.duckdb", "llm_exomiser_assisted_fixed_gene_summary"),
    "Exomiser-assisted 10g (fixed)": ("phenotype_only_5genes_sonnet.duckdb", "REPLACE"),  # adjust
    "Exomiser no-anchor (fixed)": ("llm_exomiser_no_anchor_fixed.duckdb", "llm_exomiser_no_anchor_fixed_gene_summary"),
    "RAG v2": ("llm_rag_v2.duckdb", "llm_rag_v2_gene_summary"),
    "RAG + Agentic": ("llm_rag_agentic.duckdb", "llm_rag_agentic_gene_summary"),
    "CoT": ("llm_cot_correct.duckdb", "llm_cot_correct_gene_summary"),
    "RAG v1": ("llm_rag.duckdb", "llm_rag_gene_summary"),
    "Phenotype-only (5g Sonnet)": ("llm_phenotype_only_correct.duckdb", "llm_phenotype_only_correct_gene_summary"),
    "Phenotype-only (10g Haiku)": ("llm_10genes_correct.duckdb", "llm_10genes_correct_gene_summary"),
}

print(f"{'Approach':35s} {'top1':>6} {'n':>5} {'reported %':>11} {'computed %':>11} {'raw top1/n %':>13} {'match?'}")
print("-" * 100)

for name, (dbfile, table) in approaches.items():
    if not Path(dbfile).exists():
        print(f"{name:35s} FILE NOT FOUND: {dbfile}")
        continue
    try:
        con = duckdb.connect(dbfile)
        row = con.execute(f'SELECT top1, number_of_samples, "percentage@1" FROM {table}').df().iloc[0]
        top1 = int(row["top1"])
        n = int(row["number_of_samples"])
        reported_pct = float(row["percentage@1"])
        computed_pct = 100 * top1 / n
        match = "OK" if abs(reported_pct - computed_pct) < 0.05 else "MISMATCH"
        print(f"{name:35s} {top1:6d} {n:5d} {reported_pct:10.2f}% {computed_pct:10.2f}% {'':13} {match}")
    except Exception as e:
        print(f"{name:35s} ERROR: {e}")