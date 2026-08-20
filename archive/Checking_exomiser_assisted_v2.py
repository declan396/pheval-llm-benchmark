import polars as pl
from pathlib import Path

overlap_counts = []
for f in sorted(Path("exomiser_results").glob("patient_*.parquet"))[:30]:
    df = pl.read_parquet(f)
    buggy = (df.sort("genePhenotypeScore", descending=True)
               .unique(subset=["geneSymbol"], keep="first")
               .head(10)["geneSymbol"].to_list())
    correct = (df.unique(subset=["geneSymbol"], keep="first")
                 .sort("genePhenotypeScore", descending=True)
                 .head(10)["geneSymbol"].to_list())
    overlap = len(set(buggy) & set(correct))
    overlap_counts.append(overlap)

print(f"Average overlap between buggy and correct top-10: {sum(overlap_counts)/len(overlap_counts):.1f}/10")
print(f"Distribution: {sorted(overlap_counts)}")