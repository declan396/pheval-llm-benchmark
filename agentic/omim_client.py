"""
omim_client.py
==============
OMIM API wrapper for gene-disease lookups.

Usage (standalone test):
    python omim_client.py CDKL5
    python omim_client.py TNNI3

Environment:
    OMIM_API_KEY — get free key at https://omim.org/api
"""

import os
import json
import sys
import requests

OMIM_API_KEY = os.environ.get("OMIM_API_KEY", "")
OMIM_BASE    = "https://api.omim.org/api"


def lookup_gene(gene_symbol: str, max_diseases: int = 5) -> dict:
    """
    Look up a gene in OMIM and return associated diseases and inheritance patterns.

    Args:
        gene_symbol:   HGNC gene symbol e.g. CDKL5, TNNI3
        max_diseases:  max number of disease associations to return

    Returns:
        dict with keys: gene, diseases (list), error (if any)
    """
    if not OMIM_API_KEY:
        return {"gene": gene_symbol, "error": "OMIM_API_KEY not set"}

    try:
        resp = requests.get(
            f"{OMIM_BASE}/geneMap",
            params={
                "search":  gene_symbol,
                "format":  "json",
                "apiKey":  OMIM_API_KEY,
                "include": "geneMap",
                "limit":   5,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        entries = (
            data.get("omim", {})
                .get("searchResponse", {})
                .get("geneMapList", [])
        )

        if not entries:
            return {"gene": gene_symbol, "diseases": [], "note": "No OMIM entries found"}

        diseases = []
        for entry in entries:
            gm = entry.get("geneMap", {})
            for ph in gm.get("phenotypeMapList", [])[:max_diseases]:
                pm = ph.get("phenotypeMap", {})
                diseases.append({
                    "disease":     pm.get("phenotype", "Unknown"),
                    "omim_id":     str(pm.get("phenotypeMimNumber", "")),
                    "inheritance": pm.get("phenotypeInheritance", "Unknown"),
                })

        return {"gene": gene_symbol, "diseases": diseases[:max_diseases]}

    except requests.RequestException as e:
        return {"gene": gene_symbol, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"gene": gene_symbol, "error": str(e)}


# ── Tool schema for Anthropic API ──────────────────────────────────────────
TOOL_DEFINITION = {
    "name": "omim_gene_lookup",
    "description": (
        "Look up a gene in OMIM to find its associated diseases, inheritance patterns, "
        "and phenotype descriptions. Use this to check whether a candidate gene's known "
        "disease associations match the patient's clinical presentation before ranking it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gene_symbol": {
                "type":        "string",
                "description": "HGNC gene symbol e.g. CDKL5, TNNI3, SCN1A",
            }
        },
        "required": ["gene_symbol"],
    },
}


if __name__ == "__main__":
    gene = sys.argv[1] if len(sys.argv) > 1 else "CDKL5"
    result = lookup_gene(gene)
    print(json.dumps(result, indent=2))
