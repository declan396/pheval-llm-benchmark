"""
exomiser_loader.py
==================
Load Exomiser gene ranking results from PhEval parquet files.

Usage (standalone test):
    python exomiser_loader.py exomiser_results/OMIM_613286_patient_1-gene_result.parquet
"""

import sys
import csv
from pathlib import Path
from dataclasses import dataclass

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class ExomiserCandidate:
    rank:        int
    gene_symbol: str
    score:       float


def load_candidates(
    parquet_path: Path,
    top_n: int = 10,
) -> list[ExomiserCandidate]:
    """
    Load top-N candidate genes from an Exomiser PhEval parquet file.

    Args:
        parquet_path: path to *-gene_result.parquet file
        top_n:        number of top candidates to return

    Returns:
        list of ExomiserCandidate sorted by score descending
    """
    if not HAS_PANDAS:
        raise ImportError("pandas required: pip install pandas pyarrow")

    if not parquet_path.exists():
        return []

    df = pd.read_parquet(parquet_path)

    # PhEval parquet schema: gene_symbol, gene_identifier, score, rank
    score_col = "score" if "score" in df.columns else df.columns[-1]
    df = df.sort_values(score_col, ascending=False).head(top_n).reset_index(drop=True)

    candidates = []
    for i, row in df.iterrows():
        candidates.append(ExomiserCandidate(
            rank        = i + 1,
            gene_symbol = str(row.get("gene_symbol", "")),
            score       = round(float(row.get(score_col, 0.0)), 4),
        ))

    return candidates


def load_candidates_for_patient(
    patient_id:      str,
    exomiser_dir:    Path,
    lookup_csv:      Path | None = None,
    top_n:           int = 10,
) -> list[ExomiserCandidate]:
    """
    Load Exomiser candidates for a patient, handling stem mapping if needed.

    Args:
        patient_id:   e.g. "patient_001" or "OMIM_613286_patient_1"
        exomiser_dir: directory containing *-gene_result.parquet files
        lookup_csv:   optional CSV mapping patient_001 -> OMIM stem
        top_n:        number of candidates to return
    """
    # Try direct match first
    direct = exomiser_dir / f"{patient_id}-gene_result.parquet"
    if direct.exists():
        return load_candidates(direct, top_n)

    # Try lookup CSV mapping
    if lookup_csv and lookup_csv.exists():
        with open(lookup_csv) as f:
            for row in csv.DictReader(f):
                new_stem  = Path(row["new_file"]).stem
                orig_stem = Path(row["original_file"]).stem
                if new_stem == patient_id:
                    mapped = exomiser_dir / f"{orig_stem}-gene_result.parquet"
                    if mapped.exists():
                        return load_candidates(mapped, top_n)

    return []


def format_for_prompt(candidates: list[ExomiserCandidate]) -> str:
    """Format Exomiser candidates for inclusion in LLM prompt."""
    if not candidates:
        return "  (no Exomiser results available)"
    lines = []
    for c in candidates:
        lines.append(f"  {c.rank}. {c.gene_symbol} (score: {c.score})")
    return "\n".join(lines)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if path:
        candidates = load_candidates(path)
        for c in candidates:
            print(f"  {c.rank}. {c.gene_symbol} — score: {c.score}")
    else:
        print("Usage: python exomiser_loader.py path/to/file-gene_result.parquet")
