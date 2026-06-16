import anthropic
import json
import os
import time
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
PHENOPACKETS_DIR  = Path("phenopackets")
EXOMISER_DIR      = Path("exomiser_results")
RESULTS_DIR = Path("llm_results_exomiser_assisted_sonnet_10genes")
MODEL = "claude-sonnet-4-6"

TOP_N_EXOMISER    = 10  # number of Exomiser genes to feed into prompt
# ──────────────────────────────────────────────────────────────────────────────

RESULTS_DIR.mkdir(exist_ok=True)
client = anthropic.Anthropic()


def extract_phenotypes(phenopacket: dict) -> list[str]:
    features = phenopacket.get("phenotypicFeatures", [])
    return [f["type"]["label"] for f in features if "type" in f]


def extract_exomiser_genes(patient_id: str) -> list[dict]:
    """Read Exomiser parquet and return top N genes by phenotype score."""
    import polars as pl
    parquet_file = EXOMISER_DIR / f"{patient_id}.parquet"
    if not parquet_file.exists():
        return []
    df = pl.read_parquet(parquet_file)
    top = (df.sort("genePhenotypeScore", descending=True)
             .unique(subset=["geneSymbol"], keep="first")
             .head(TOP_N_EXOMISER)
             .select(["geneSymbol", "genePhenotypeScore"]))
    return [
        {"gene": row["geneSymbol"], "phenotype_score": round(row["genePhenotypeScore"], 4)}
        for row in top.to_dicts()
    ]


def build_prompt(patient_id: str, phenotypes: list[str], exomiser_genes: list[dict]) -> str:
    phenotype_list = "\n".join(f"- {p}" for p in phenotypes)
    gene_list = "\n".join(
        f"{i+1}. {g['gene']} (phenotype score: {g['phenotype_score']})"
        for i, g in enumerate(exomiser_genes)
    )
    return f"""You are an expert clinical geneticist specialising in rare genetic diseases.

A patient presents with the following clinical features:
{phenotype_list}

Exomiser has prioritised the following candidate genes based on phenotype similarity:
{gene_list}

Using both the patient's phenotypes and the Exomiser candidate genes, provide your diagnostic interpretation.

You MUST respond with ONLY a valid JSON object in exactly this format, no other text:
{{
  "patient_id": "{patient_id}",
  "top_genes": [
    {{"rank": 1, "gene_symbol": "GENE1", "score": 0.95}},
    {{"rank": 2, "gene_symbol": "GENE2", "score": 0.85}},
    {{"rank": 3, "gene_symbol": "GENE3", "score": 0.75}},
    {{"rank": 4, "gene_symbol": "GENE4", "score": 0.65}},
    {{"rank": 5, "gene_symbol": "GENE5", "score": 0.55}},
    {{"rank": 6, "gene_symbol": "GENE6", "score": 0.45}},
    {{"rank": 7, "gene_symbol": "GENE7", "score": 0.40}},
    {{"rank": 8, "gene_symbol": "GENE8", "score": 0.35}},
    {{"rank": 9, "gene_symbol": "GENE9", "score": 0.30}},
    {{"rank": 10, "gene_symbol": "GENE10", "score": 0.25}}
  ],
  "likely_diagnosis": "Disease name here",
  "confidence": "high/medium/low",
  "reasoning": "Brief explanation considering both phenotypes and Exomiser candidates"
}}

Return exactly 10 candidate genes ranked by likelihood. Prioritise genes from the Exomiser list where they fit the phenotype, but you may include genes not in the Exomiser list if strongly indicated. Use real HGNC gene symbols only."""


def run_patient(patient_id: str, phenotypes: list[str], exomiser_genes: list[dict]) -> dict | None:
    prompt = build_prompt(patient_id, phenotypes, exomiser_genes)
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error for {patient_id}: {e}")
        return {"patient_id": patient_id, "error": "json_parse_error", "raw": raw}
    except Exception as e:
        print(f"  ⚠ API error for {patient_id}: {e}")
        return {"patient_id": patient_id, "error": str(e)}


def already_processed(patient_id: str) -> bool:
    return (RESULTS_DIR / f"{patient_id}.json").exists()


def main():
    phenopacket_files = sorted(PHENOPACKETS_DIR.glob("patient_*.json"))
    total = len(phenopacket_files)
    print(f"Found {total} phenopackets\n")

    success = 0
    skipped = 0
    failed  = 0
    no_exomiser = 0

    for i, filepath in enumerate(phenopacket_files, 1):
        patient_id = filepath.stem

        if already_processed(patient_id):
            print(f"[{i}/{total}] Skipping {patient_id} (already done)")
            skipped += 1
            continue

        print(f"[{i}/{total}] Processing {patient_id}...", end=" ")

        with open(filepath) as f:
            phenopacket = json.load(f)

        phenotypes = extract_phenotypes(phenopacket)
        if not phenotypes:
            print("⚠ No phenotypes, skipping")
            failed += 1
            continue

        exomiser_genes = extract_exomiser_genes(patient_id)
        if not exomiser_genes:
            print("⚠ No Exomiser results, skipping")
            no_exomiser += 1
            failed += 1
            continue

        result = run_patient(patient_id, phenotypes, exomiser_genes)

        if result:
            out_path = RESULTS_DIR / f"{patient_id}.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)

            if "error" in result:
                print(f"✗ Error saved")
                failed += 1
            else:
                print(f"✓ Done ({len(result.get('top_genes', []))} genes, {len(exomiser_genes)} Exomiser candidates)")
                success += 1
        else:
            failed += 1

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Complete: {success} success, {skipped} skipped, {failed} failed ({no_exomiser} missing Exomiser)")
    print(f"Results saved to: {RESULTS_DIR}/")


if __name__ == "__main__":
    main()