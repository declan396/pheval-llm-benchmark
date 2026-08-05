import polars as pl
import json
from pathlib import Path

def get_top1_correct(results_dir: Path) -> dict:
    """
    Returns dict: patient_stem -> 1 (correct) or 0 (incorrect) at top-1
    """
    correct = {}
    for f in sorted(results_dir.glob("*.parquet")):
        df = pl.read_parquet(f)
        # PhEval parquet has 'rank' column — rank 1 = top-1 correct
        top1 = df.filter(pl.col("rank") == 1)
        patient_stem = f.stem.replace("-gene_result", "")
        correct[patient_stem] = 1 if len(top1) > 0 else 0
    return correct