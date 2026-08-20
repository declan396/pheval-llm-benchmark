import json
import csv
from pathlib import Path
import polars as pl

# ── Configuration ─────────────────────────────────────────────────────────────
PHENOPACKETS_DIR      = Path("phenopackets")
EXOMISER_DIR           = Path("exomiser_results")
PHENO_WITH_GENES_DIR   = Path("synthetic_patients_with_genes")
LOOKUP_CSV             = Path("synthetic_patients_lookup.csv")
TOP_N_EXOMISER          = 10

# ↓↓↓ CHANGE THIS LINE FOR EACH OF THE THREE RUNS ↓↓↓
CLAUDE_RESULTS_DIR = Path("llm_results_exomiser_no_anchor")
# Run 1: llm_results_exomiser_no_anchor
# Run 2: llm_results_exomiser_assisted_sonnet
# Run 3: llm_results_exomiser_assisted_sonnet_10genes
# ──────────────────────────────────────────────────────────────────────────────


def load_lookup() -> dict:
    lookup = {}
    with open(LOOKUP_CSV) as f:
        for row in csv.DictReader(f):
            lookup[Path(row["new_file"]).stem] = Path(row["original_file"]).stem
    return lookup


def get_true_gene(patient_id: str, lookup: dict) -> str | None:
    orig = lookup.get(patient_id)
    if not orig:
        return None
    p = PHENO_WITH_GENES_DIR / f"{orig}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    for interp in data.get("interpretations", []):
        for gi in interp.get("diagnosis", {}).get("genomicInterpretations", []):
            g = gi.get("gene", {}).get("symbol", "")
            if g:
                return g.upper()
    return None


def get_exomiser_top10(patient_id: str) -> list[str]:
    parquet_file = EXOMISER_DIR / f"{patient_id}.parquet"
    if not parquet_file.exists():
        return []
    df = pl.read_parquet(parquet_file)
    top = (df.unique(subset=["geneSymbol"], keep="first")
             .sort("genePhenotypeScore", descending=True)
             .head(TOP_N_EXOMISER))
    return [g.upper() for g in top["geneSymbol"].to_list()]


def get_claude_genes(patient_id: str) -> list[str]:
    f = CLAUDE_RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return []
    data = json.loads(f.read_text())
    if "error" in data:
        return []
    return [g.get("gene_symbol", "").upper() for g in data.get("top_genes", [])]


def main():
    lookup = load_lookup()

    exo_yes_claude_yes = 0
    exo_yes_claude_no  = 0
    exo_no_claude_yes  = 0
    exo_no_claude_no   = 0
    skipped = 0

    detail_rows = []
    debug_count = 0  # TEMPORARY DEBUG

    for patient_id in lookup:
        true_gene = get_true_gene(patient_id, lookup)
        if not true_gene:
            continue

        exo_top10 = get_exomiser_top10(patient_id)
        claude_genes = get_claude_genes(patient_id)

        # TEMPORARY DEBUG — print raw values for the first 5 patients that have data
        if debug_count < 5 and exo_top10 and claude_genes:
            print(f"\n--- DEBUG {patient_id} ---")
            print(f"true_gene:    {repr(true_gene)}")
            print(f"exo_top10:    {exo_top10}")
            print(f"claude_genes: {claude_genes}")
            debug_count += 1

        if not exo_top10 or not claude_genes:
            skipped += 1
            continue

        gene_in_exo = true_gene in exo_top10
        gene_in_claude = true_gene in claude_genes

        if gene_in_exo and gene_in_claude:
            exo_yes_claude_yes += 1
        elif gene_in_exo and not gene_in_claude:
            exo_yes_claude_no += 1
        elif not gene_in_exo and gene_in_claude:
            exo_no_claude_yes += 1
        else:
            exo_no_claude_no += 1

        detail_rows.append({
            "patient_id": patient_id,
            "true_gene": true_gene,
            "in_exomiser_top10": gene_in_exo,
            "in_claude_output": gene_in_claude,
            "exomiser_rank": exo_top10.index(true_gene) + 1 if gene_in_exo else None,
            "claude_rank": claude_genes.index(true_gene) + 1 if gene_in_claude else None,
        })

    total = exo_yes_claude_yes + exo_yes_claude_no + exo_no_claude_yes + exo_no_claude_no
    print(f"\n=== Variant: {CLAUDE_RESULTS_DIR.name} ===")
    print(f"Analysed {total} patients ({skipped} skipped, missing Exomiser or Claude output)\n")

    print("                          Claude HAS gene   Claude MISSING gene")
    print(f"Exomiser top-10 HAS gene       {exo_yes_claude_yes:4d}                {exo_yes_claude_no:4d}")
    print(f"Exomiser top-10 MISSING gene   {exo_no_claude_yes:4d}                {exo_no_claude_no:4d}")

    print("\n--- Interpretation ---")
    if (exo_yes_claude_yes + exo_yes_claude_no) > 0:
        pct = 100 * exo_yes_claude_no / (exo_yes_claude_yes + exo_yes_claude_no)
        print(f"When Exomiser HAD the correct gene, Claude still dropped it in "
              f"{exo_yes_claude_no}/{exo_yes_claude_yes + exo_yes_claude_no} cases ({pct:.1f}%).")
    if (exo_no_claude_yes + exo_no_claude_no) > 0:
        pct = 100 * exo_no_claude_yes / (exo_no_claude_yes + exo_no_claude_no)
        print(f"When Exomiser did NOT have the correct gene, Claude recovered it in "
              f"{exo_no_claude_yes}/{exo_no_claude_yes + exo_no_claude_no} cases ({pct:.1f}%).")
    if exo_no_claude_yes == 0:
        print("\nClaude NEVER recovered a gene absent from Exomiser's top-10.")
        print("This supports the 're-order rather than augment' hypothesis.")
    else:
        print(f"\nClaude recovered {exo_no_claude_yes} genes NOT in Exomiser's top-10.")
        print("This is evidence AGAINST a pure 're-order only' hypothesis, Claude can add genes.")

    out_path = Path(f"anchoring_mechanism_analysis_{CLAUDE_RESULTS_DIR.name}.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_rows[0].keys())
        writer.writeheader()
        writer.writerows(detail_rows)
    print(f"Per-patient detail saved to {out_path}")


if __name__ == "__main__":
    main()