import polars as pl
df = pl.read_parquet("pheval_gene_results_phenotype_only_correct/pheval_gene_results/OMIM_112240_patient_1-gene_result.parquet")
print(df.sort("rank"))