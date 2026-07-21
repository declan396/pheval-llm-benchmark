"""
run_llm_cot.py
==============
Chain-of-thought gene prioritisation using Claude Haiku.

Same as phenotype-only but prompts Claude to reason step by step
before returning its ranked gene list. Tests whether CoT improves
gene prioritisation accuracy.

Output: llm_results_cot/patient_001.json etc.

Usage:
    python run_llm_cot.py

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
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 1200
RESULTS_DIR       = Path("llm_results_cot")
PHENOPACKET_DIR   = Path("phenopackets")
NUM_GENES         = 5
SLEEP_BETWEEN     = 1.0

RESULTS_DIR.mkdir(exist_ok=True)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Key difference: ask Claude to reason before answering
SYSTEM_PROMPT = """You are a clinical genetics expert specialising in rare Mendelian disease diagnosis.

Given a patient's HPO phenotype terms, identify the most likely causative gene.

IMPORTANT: Before giving your final answer, reason step by step:
1. Which phenotypes are most specific and diagnostically useful?
2. What disease categories do these phenotypes suggest?
3. Which genes are known to cause diseases with this phenotype combination?
4. Consider inheritance patterns and gene-disease specificity.

After reasoning, return your final answer as valid JSON only:
{
  "reasoning": "your step-by-step reasoning here",
  "top_genes": [
    {"rank": 1, "gene_symbol": "GENE1", "score": 0.95},
    {"rank": 2, "gene_symbol": "GENE2", "score": 0.80}
  ]
}"""


def already_done(patient_id: str) -> bool:
    f = RESULTS_DIR / f"{patient_id}.json"
    if not f.exists():
        return False
    data = json.loads(f.read_text())
    return "error" not in data and bool(data.get("top_genes"))


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

Please reason step by step, then return the top {NUM_GENES} most likely causative genes as JSON."""

    response = client.messages.create(
        model      = MODEL,
        max_tokens = MAX_TOKENS,
        system     = SYSTEM_PROMPT,
        messages   = [{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()

    # Try to parse JSON — may be embedded in reasoning text
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

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from within text
    import re
    match = re.search(r'\{.*"top_genes".*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"error": "Could not parse JSON", "raw": text[:500]}


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        return

    phenopackets = sorted(PHENOPACKET_DIR.glob("patient_*.json"))
    total = len(phenopackets)
    print(f"Chain-of-thought gene prioritisation — {total} patients")
    print(f"Model: {MODEL}  |  Top-{NUM_GENES} genes with reasoning")
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

            if "error" in result:
                print(f"parse error")
                failed += 1
            else:
                top1 = result["top_genes"][0]["gene_symbol"] if result.get("top_genes") else "none"
                has_reasoning = bool(result.get("reasoning"))
                print(f"ok  top: {top1}  reasoning: {'yes' if has_reasoning else 'no'}")
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
    print(f"\nNext: scp to Apocrita then run convert_llm_to_pheval.py pointing at {RESULTS_DIR}/")


if __name__ == "__main__":
    main()