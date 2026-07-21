"""
agent.py
========
Claude agentic loop for RAG + Monarch gene prioritisation.

Claude receives patient HPO terms and retrieved HPOA diseases, then
iteratively calls Monarch/PubMed/ClinVar tools before returning a
final ranked gene list.

Usage (standalone test):
    python agent.py

Environment:
    ANTHROPIC_API_KEY
"""

import os
import re
import json
import anthropic

from monarch_client import TOOL_DEFINITIONS, dispatch
from rag_retriever import RetrievedDisease, format_for_prompt

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 2000
MAX_TOOL_ROUNDS   = 3
NUM_GENES         = 10

SYSTEM_PROMPT = """You are an expert clinical geneticist specialising in rare Mendelian disease diagnosis.

You have access to Monarch Initiative, PubMed, and ClinVar tools to investigate candidate genes.

IMPORTANT: You have a maximum of 3 tool calls total. After your tools are used, immediately return JSON.

You MUST respond with ONLY this JSON format — no prose, no thinking, no explanation:
{"top_genes": [{"rank": 1, "gene_symbol": "GENE1", "score": 0.95, "reasoning": "brief"}, {"rank": 2, "gene_symbol": "GENE2", "score": 0.85, "reasoning": "brief"}, {"rank": 3, "gene_symbol": "GENE3", "score": 0.75, "reasoning": "brief"}, {"rank": 4, "gene_symbol": "GENE4", "score": 0.65, "reasoning": "brief"}, {"rank": 5, "gene_symbol": "GENE5", "score": 0.55, "reasoning": "brief"}, {"rank": 6, "gene_symbol": "GENE6", "score": 0.45, "reasoning": "brief"}, {"rank": 7, "gene_symbol": "GENE7", "score": 0.40, "reasoning": "brief"}, {"rank": 8, "gene_symbol": "GENE8", "score": 0.35, "reasoning": "brief"}, {"rank": 9, "gene_symbol": "GENE9", "score": 0.30, "reasoning": "brief"}, {"rank": 10, "gene_symbol": "GENE10", "score": 0.20, "reasoning": "brief"}], "likely_diagnosis": "Disease name", "confidence": "high/medium/low"}

Return exactly 10 real HGNC gene symbols. Never return empty top_genes. If uncertain, use genes from the retrieved diseases list."""


def _parse_json(text: str) -> dict | None:
    """Try multiple strategies to extract JSON from text."""
    text = text.strip()

    # Direct parse
    try:
        result = json.loads(text)
        if "top_genes" in result:
            return result
    except json.JSONDecodeError:
        pass

    # Markdown fences
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                result = json.loads(part)
                if "top_genes" in result:
                    return result
            except json.JSONDecodeError:
                continue

    # Regex extraction
    match = re.search(r'\{.*?"top_genes".*?\}', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "top_genes" in result:
                return result
        except json.JSONDecodeError:
            pass

    return None


def _pad_genes(top_genes: list, retrieved: list[RetrievedDisease], target: int = 10) -> list:
    """Pad gene list to target length using genes from retrieved diseases."""
    seen = {g["gene_symbol"] for g in top_genes}
    for d in retrieved:
        for g in d.genes:
            if g and g not in seen and len(top_genes) < target:
                top_genes.append({
                    "rank":        len(top_genes) + 1,
                    "gene_symbol": g,
                    "score":       round(d.similarity * 0.4, 3),
                    "reasoning":   f"RAG: {d.disease_name}",
                })
                seen.add(g)
        if len(top_genes) >= target:
            break
    return top_genes


def _fallback_genes(retrieved: list[RetrievedDisease]) -> list:
    """Build gene list entirely from RAG retrieved diseases."""
    genes = []
    seen = set()
    for d in retrieved:
        for g in d.genes:
            if g and g not in seen and len(genes) < 10:
                genes.append({
                    "rank":        len(genes) + 1,
                    "gene_symbol": g,
                    "score":       round(d.similarity * 0.5, 3),
                    "reasoning":   f"RAG: {d.disease_name}",
                })
                seen.add(g)
        if len(genes) >= 10:
            break
    return genes


def run_agent(
    patient_id:    str,
    hpo_ids:       list[str],
    hpo_labels:    list[str],
    retrieved:     list[RetrievedDisease],
    verbose:       bool = False,
) -> dict:
    """
    Run the agentic loop for a single patient.
    Always returns a result with top_genes (padded from RAG if needed).
    """
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set", "top_genes": []}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hpo_str      = "\n".join(f"- {label} ({hid})" for hid, label in zip(hpo_ids, hpo_labels))
    disease_str  = format_for_prompt(retrieved)

    user_message = f"""Patient HPO phenotypes:
{hpo_str}

Top phenotypically similar diseases retrieved from HPOA:
{disease_str}

Investigate the most promising candidates using up to 3 tool calls, then return your JSON ranking immediately."""

    messages       = [{"role": "user", "content": user_message}]
    tool_calls_log = []

    for round_num in range(MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model      = MODEL,
            max_tokens = MAX_TOKENS,
            system     = SYSTEM_PROMPT,
            tools      = TOOL_DEFINITIONS,
            messages   = messages,
        )

        if response.stop_reason == "end_turn":
            raw_text = ""
            for block in response.content:
                if block.type == "text":
                    raw_text = block.text
                    result = _parse_json(block.text)
                    if result:
                        result["top_genes"] = _pad_genes(result["top_genes"], retrieved)
                        result["tool_calls"] = tool_calls_log
                        result["rounds"]     = round_num
                        return result

            # JSON parse failed — ask Claude to reformat
            try:
                force = client.messages.create(
                    model      = MODEL,
                    max_tokens = 800,
                    system     = "You are a JSON formatter. Return ONLY valid JSON, no prose.",
                    messages   = [{"role": "user", "content": f"Extract gene symbols from this analysis and return JSON:\n\n{raw_text[:1000]}\n\nFormat: {{\"top_genes\": [{{\"rank\": 1, \"gene_symbol\": \"GENE1\", \"score\": 0.9, \"reasoning\": \"brief\"}}], \"likely_diagnosis\": \"Disease\", \"confidence\": \"medium\"}}"}],
                )
                for b in force.content:
                    if b.type == "text":
                        result = _parse_json(b.text)
                        if result and result.get("top_genes"):
                            result["top_genes"] = _pad_genes(result["top_genes"], retrieved)
                            result["tool_calls"] = tool_calls_log
                            result["rounds"]     = round_num
                            result["forced"]     = True
                            return result
            except Exception:
                pass

            # Final fallback: use RAG genes directly
            fallback = _fallback_genes(retrieved)
            return {
                "top_genes":  fallback,
                "tool_calls": tool_calls_log,
                "rounds":     round_num,
                "forced":     True,
                "note":       "RAG fallback — JSON parse failed",
            }

        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"      \u2192 {block.name}({json.dumps(block.input)[:80]})")
                    try:
                        result_str = dispatch(block.name, block.input)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)[:100]})
                    tool_calls_log.append({"tool": block.name, "input": block.input})
                    if len(result_str) > 1500:
                        result_str = result_str[:1500] + "... [truncated]"
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result_str,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            break

    # Max rounds exceeded — use RAG fallback
    fallback = _fallback_genes(retrieved)
    return {
        "top_genes":  fallback,
        "tool_calls": tool_calls_log,
        "rounds":     MAX_TOOL_ROUNDS,
        "forced":     True,
        "note":       f"Max tool rounds ({MAX_TOOL_ROUNDS}) exceeded — RAG fallback",
    }


if __name__ == "__main__":
    from rag_retriever import RetrievedDisease

    dummy_patient = {
        "hpo_ids":    ["HP:0001249", "HP:0001250", "HP:0000750"],
        "hpo_labels": ["Intellectual disability", "Seizures", "Delayed speech"],
    }
    dummy_retrieved = [
        RetrievedDisease(1, "OMIM:300672", "CDKL5 deficiency disorder", 0.91, ["CDKL5"]),
        RetrievedDisease(2, "OMIM:312750", "Rett syndrome",             0.85, ["MECP2"]),
        RetrievedDisease(3, "OMIM:613721", "Dravet syndrome",           0.79, ["SCN1A"]),
        RetrievedDisease(4, "OMIM:300644", "FOXG1 syndrome",            0.74, ["FOXG1"]),
        RetrievedDisease(5, "OMIM:300749", "PCDH19 epilepsy",           0.68, ["PCDH19"]),
    ]

    print("Running smoke test...")
    result = run_agent(
        patient_id = "test_patient",
        hpo_ids    = dummy_patient["hpo_ids"],
        hpo_labels = dummy_patient["hpo_labels"],
        retrieved  = dummy_retrieved,
        verbose    = True,
    )
    print(f"Genes: {len(result.get('top_genes', []))}")
    print(json.dumps(result, indent=2))