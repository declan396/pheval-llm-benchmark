from google import genai
import json
import os
import time
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
PHENOPACKETS_DIR = Path(r"C:\Users\decla\PycharmProjects\Phenopackets_AI\phenopackets")  # ← check this matches your actual folder
RESULTS_DIR       = Path("llm_results_phenotype_only_gemini")
MODEL              = "gemini-2.0-flash"  # confirm current on ai.google.dev/gemini-api/docs/models
# ──────────────────────────────────────────────────────────────────────────────

RESULTS_DIR.mkdir(exist_ok=True)
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def extract_phenotypes(phenopacket: dict) -> list[str]:
    features = phenopacket.get("phenotypicFeatures", [])
    return [f["type"]["label"] for f in features if "type" in f]


def build_prompt(patient_id: str, phenotypes: list[str]) -> str:
    phenotype_list = "\n".join(f"- {p}" for p in phenotypes)
    return f"""You are an expert clinical geneticist specialising in rare genetic diseases.

A patient presents with the following clinical features:
{phenotype_list}

Based on these phenotypes, provide your differential diagnosis.

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
  "reasoning": "Brief explanation of your reasoning"
}}

Return exactly 10 candidate genes ranked by likelihood. Use real HGNC gene symbols only."""


def run_patient(patient_id: str, phenotypes: list[str]) -> dict | None:
    prompt = build_prompt(patient_id, phenotypes)
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        raw = response.text.strip()

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
    f = RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.load(open(f))
    return "error" not in data


def main():
    phenopacket_files = sorted(PHENOPACKETS_DIR.glob("patient_*.json"))
    total = len(phenopacket_files)
    print(f"Found {total} phenopackets\n")

    success = 0
    skipped = 0
    failed  = 0

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

        result = run_patient(patient_id, phenotypes)

        if result:
            out_path = RESULTS_DIR / f"{patient_id}.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)

            if "error" in result:
                print(f"✗ Error saved")
                failed += 1
            else:
                print(f"✓ Done ({len(result.get('top_genes', []))} genes)")
                success += 1
        else:
            failed += 1

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Complete: {success} success, {skipped} skipped, {failed} failed")
    print(f"Results saved to: {RESULTS_DIR}/")


if __name__ == "__main__":
    main()