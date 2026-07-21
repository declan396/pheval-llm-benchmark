"""
run_llm_disease_level.py
========================
Disease-level LLM benchmarking using Claude Haiku.

Asks Claude to return OMIM disease IDs from patient HPO terms.
Results benchmarked with PhEval generate_disease_result.

Output: llm_results_disease_level/patient_001.json etc.

Usage:
    python run_llm_disease_level.py

Environment:
    ANTHROPIC_API_KEY
"""

import os
import json
import time
from pathlib import Path
import anthropic

# ── Configuration ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 800
RESULTS_DIR       = Path("llm_results_disease_level_sonnet")
PHENOPACKET_DIR   = Path("phenopackets")
NUM_DISEASES      = 5
SLEEP_BETWEEN     = 1.0

RESULTS_DIR.mkdir(exist_ok=True)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a clinical genetics expert specialising in rare disease diagnosis.

Given a patient's HPO phenotype terms, return the most likely rare disease diagnoses as OMIM IDs.

You MUST respond with valid JSON only — no explanation, no markdown, no other text:
{
  "top_diseases": [
    {"rank": 1, "disease_id": "OMIM:123456", "disease_name": "Disease Name", "score": 0.95},
    {"rank": 2, "disease_id": "OMIM:234567", "disease_name": "Disease Name", "score": 0.80}
  ]
}"""


def already_done(patient_id: str) -> bool:
    f = RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.loads(f.read_text())
    return "error" not in data and bool(data.get("top_diseases"))


def load_hpo_terms(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    terms = []
    for feat in data.get("phenotypicFeatures", []):
        t = feat.get("type", {})
        hpo_id = t.get("id", "")
        label  = t.get("label", "")
        if hpo_id and not feat.get("excluded", False):
            terms.append(f"{hpo_id} ({label})" if label else hpo_id)
    return terms


def query_llm(hpo_terms: list[str]) -> dict:
    hpo_str = "\n".join(f"- {t}" for t in hpo_terms)
    user_msg = f"""A patient presents with the following HPO phenotype terms:

{hpo_str}

Return the top {NUM_DISEASES} most likely OMIM disease diagnoses as JSON."""

    response = client.messages.create(
        model      = MODEL,
        max_tokens = MAX_TOKENS,
        system     = SYSTEM_PROMPT,
        messages   = [{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue
    return json.loads(text)


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        return

    phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
    total = len(phenopackets)
    print(f"Disease-level benchmarking — {total} patients")
    print(f"Model: {MODEL}  |  Top-{NUM_DISEASES} diseases per patient")
    print(f"Output: {RESULTS_DIR}/\n")

    success = skipped = failed = 0

    for i, ppath in enumerate(phenopackets, 1):
        patient_id = ppath.stem

        if already_done(patient_id):
            print(f"[{i:03d}/{total}] skip  {patient_id}")
            skipped += 1
            continue

        print(f"[{i:03d}/{total}] run   {patient_id}...", end=" ", flush=True)

        try:
            hpo_terms = load_hpo_terms(ppath)
            if not hpo_terms:
                print("warning no HPO terms")
                skipped += 1
                continue

            result = query_llm(hpo_terms)
            result["patient_id"] = patient_id
            result["hpo_terms"]  = hpo_terms

            (RESULTS_DIR / f"{patient_id}.json").write_text(json.dumps(result, indent=2))

            top1 = result["top_diseases"][0]["disease_id"] if result.get("top_diseases") else "none"
            print(f"ok  top: {top1}")
            success += 1

        except anthropic.RateLimitError:
            print("rate limited waiting 60s")
            time.sleep(60)
            failed += 1

        except Exception as e:
            err = str(e)[:80]
            print(f"error  {err}")
            (RESULTS_DIR / f"{patient_id}.json").write_text(
                json.dumps({"error": err, "patient_id": patient_id})
            )
            failed += 1

        if i < total:
            time.sleep(SLEEP_BETWEEN)

    print(f"\nDone.  success {success}  skipped {skipped}  failed {failed}")
    print(f"Results: {RESULTS_DIR}/")
    print(f"\nNext: scp results to Apocrita then run convert_disease_to_pheval.py")


if __name__ == "__main__":
    main()
