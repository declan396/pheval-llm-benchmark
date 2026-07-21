"""
agent.py
========
Claude agentic loop for gene prioritisation.

Claude receives patient HPO terms and Exomiser candidates, then
iteratively calls the OMIM tool to look up gene-disease associations
before returning a final ranked gene list.

Usage (standalone test):
    python agent.py

Environment:
    ANTHROPIC_API_KEY
"""

import os
import json
import anthropic

from agentic.omim_client import lookup_gene, TOOL_DEFINITION
from agentic.phenopacket_loader import PatientData, format_for_prompt as format_patient
from agentic.exomiser_loader import ExomiserCandidate, format_for_prompt as format_candidates

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"
MAX_TOKENS        = 1500
MAX_TOOL_ROUNDS   = 3
TOP_N_OUTPUT      = 5

SYSTEM_PROMPT = """You are a clinical genetics expert helping to identify the most likely causative gene for a rare disease patient.

You have access to an OMIM lookup tool. Use it to check whether candidate genes' known disease associations match the patient's clinical presentation. You may call it multiple times for different genes.

Think carefully about:
- Which phenotypes are most specific and diagnostically useful
- Whether the inheritance pattern fits (AD, AR, X-linked)
- Whether the candidate gene's OMIM phenotypes overlap with the patient's features

When you have gathered enough information, return your final answer as valid JSON ONLY — no other text, no markdown fences:
{
  "top_genes": [
    {
      "rank": 1,
      "gene_symbol": "GENE1",
      "score": 0.95,
      "reasoning": "brief explanation linking patient phenotype to this gene"
    }
  ]
}"""


def _process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch tool calls and return JSON string result."""
    if tool_name == "omim_gene_lookup":
        result = lookup_gene(tool_input["gene_symbol"])
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agent(
    patient:    PatientData,
    candidates: list[ExomiserCandidate],
    verbose:    bool = False,
) -> dict:
    """
    Run the agentic loop for a single patient.

    Args:
        patient:    PatientData with HPO terms
        candidates: Exomiser top-N candidate genes
        verbose:    print tool call details

    Returns:
        dict with top_genes list, tool_calls made, rounds used
    """
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set", "top_genes": []}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_message = f"""{format_patient(patient)}

Exomiser has ranked these candidate genes by phenotype similarity:
{format_candidates(candidates)}

Please use the OMIM tool to investigate the most promising candidates, then return your final ranked list of up to {TOP_N_OUTPUT} genes most likely to be causative."""

    messages = [{"role": "user", "content": user_message}]
    tool_calls_log = []

    for round_num in range(MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model      = MODEL,
            max_tokens = MAX_TOKENS,
            system     = SYSTEM_PROMPT,
            tools      = [TOOL_DEFINITION],
            messages   = messages,
        )

        if response.stop_reason == "end_turn":
            # Parse final JSON response
            for block in response.content:
                if block.type == "text":
                    text = block.text.strip()
                    # Strip accidental markdown fences
                    if "```" in text:
                        parts = text.split("```")
                        for part in parts:
                            part = part.strip()
                            if part.startswith("json"):
                                part = part[4:].strip()
                            try:
                                result = json.loads(part)
                                if "top_genes" in result:
                                    result["tool_calls"] = tool_calls_log
                                    result["rounds"]     = round_num
                                    return result
                            except json.JSONDecodeError:
                                continue
                    else:
                        try:
                            result = json.loads(text)
                            result["tool_calls"] = tool_calls_log
                            result["rounds"]     = round_num
                            return result
                        except json.JSONDecodeError:
                            pass

            return {
                "top_genes":   [],
                "error":       "Could not parse final JSON from Claude",
                "tool_calls":  tool_calls_log,
                "raw_text":    "\n".join(
                    b.text for b in response.content if b.type == "text"
                ),
            }

        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"    → tool call: {block.name}({block.input})")

                    result_str = _process_tool_call(block.name, block.input)
                    tool_calls_log.append({
                        "tool":   block.name,
                        "input":  block.input,
                        "result": json.loads(result_str),
                    })
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result_str,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            return {
                "top_genes":  [],
                "error":      f"Unexpected stop_reason: {response.stop_reason}",
                "tool_calls": tool_calls_log,
            }

    return {
        "top_genes":  [],
        "error":      f"Max tool rounds ({MAX_TOOL_ROUNDS}) exceeded",
        "tool_calls": tool_calls_log,
    }


if __name__ == "__main__":
    # Quick smoke test with a dummy patient
    from agentic.phenopacket_loader import PatientData
    from agentic.exomiser_loader import ExomiserCandidate

    dummy_patient = PatientData(
        patient_id = "test_patient",
        hpo_terms  = [
            "HP:0001249 (Intellectual disability)",
            "HP:0001250 (Seizures)",
            "HP:0000750 (Delayed speech and language development)",
        ],
        sex = "Female",
        age = "P3Y",
    )

    dummy_candidates = [
        ExomiserCandidate(rank=1, gene_symbol="CDKL5",  score=0.87),
        ExomiserCandidate(rank=2, gene_symbol="MECP2",  score=0.74),
        ExomiserCandidate(rank=3, gene_symbol="SCN1A",  score=0.71),
        ExomiserCandidate(rank=4, gene_symbol="PCDH19", score=0.65),
        ExomiserCandidate(rank=5, gene_symbol="FOXG1",  score=0.61),
    ]

    print("Running agent on test patient...")
    result = run_agent(dummy_patient, dummy_candidates, verbose=True)
    print(json.dumps(result, indent=2))
