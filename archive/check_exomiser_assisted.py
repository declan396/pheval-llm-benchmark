import polars as pl
df = pl.read_parquet("exomiser_results/patient_037.parquet")
print(df.columns)
print(df.sort("genePhenotypeScore", descending=True).head(20).select(["geneSymbol", "genePhenotypeScore"]))
print("\nScore distribution:")
print(df["genePhenotypeScore"].describe())
print("\nHow many genes share the max score?")
max_score = df["genePhenotypeScore"].max()
print(f"Max score: {max_score}, count of genes at max: {(df['genePhenotypeScore'] == max_score).sum()}")