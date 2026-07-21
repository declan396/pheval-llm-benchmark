"""
monarch_client.py
=================
Tool functions for the RAG + Agentic pipeline.

Includes:
    Monarch Initiative API  — gene-disease associations
    PubMed API              — literature search (free, no key)
    ClinVar API             — pathogenic variant evidence (free, no key)

Usage (standalone test — run from project root):
    python rag_agentic/monarch_client.py gene CDKL5
    python rag_agentic/monarch_client.py disease MONDO:0100039
    python rag_agentic/monarch_client.py phenotype HP:0001249 HP:0001250
    python rag_agentic/monarch_client.py pubmed CDKL5 epilepsy phenotype
    python rag_agentic/monarch_client.py clinvar CDKL5
"""

import json
import sys
import xml.etree.ElementTree as ET
import requests

MONARCH_BASE = "https://api-v3.monarchinitiative.org/v3/api"
PUBMED_BASE  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CLINVAR_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT      = 12


# ── Monarch Tools ──────────────────────────────────────────────────────────

def _search_entity(query: str, category: str = "biolink:Gene") -> dict | None:
    try:
        resp = requests.get(
            f"{MONARCH_BASE}/search",
            params={"q": query, "category": category,
                    "in_taxon_label": "Homo sapiens", "limit": 3},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return None
        for item in items:
            if item.get("symbol") == query or item.get("name") == query:
                return item
        return items[0]
    except Exception:
        return None


def monarch_gene_lookup(gene_symbol: str) -> dict:
    """
    Look up a gene in Monarch to find associated diseases.
    Falls back to search if association endpoint returns 422.
    """
    try:
        gene = _search_entity(gene_symbol, "biolink:Gene")
        if not gene:
            return {"gene": gene_symbol, "error": "Gene not found in Monarch"}

        gene_id = gene.get("id", "")

        # Try association endpoint
        resp = requests.get(
            f"{MONARCH_BASE}/entity/{gene_id}/biolink:GeneToDiseaseAssociation",
            params={"limit": 10},
            timeout=TIMEOUT,
        )

        if resp.status_code == 200:
            diseases = [
                {
                    "disease_id":   item.get("object", {}).get("id", ""),
                    "disease_name": item.get("object", {}).get("name", "Unknown"),
                }
                for item in resp.json().get("items", [])[:10]
            ]
            return {"gene": gene_symbol, "monarch_id": gene_id, "diseases": diseases}

        # Fallback: search for diseases mentioning this gene
        search_resp = requests.get(
            f"{MONARCH_BASE}/search",
            params={"q": gene_symbol, "category": "biolink:Disease", "limit": 10},
            timeout=TIMEOUT,
        )
        search_resp.raise_for_status()
        diseases = [
            {"disease_id": item.get("id", ""), "disease_name": item.get("name", "")}
            for item in search_resp.json().get("items", [])[:10]
        ]
        return {"gene": gene_symbol, "monarch_id": gene_id,
                "diseases": diseases, "note": "via search fallback"}

    except Exception as e:
        return {"gene": gene_symbol, "error": str(e)}


def monarch_disease_lookup(disease_id: str) -> dict:
    """
    Look up a disease in Monarch to find causal genes and phenotypes.
    Accepts MONDO IDs (e.g. MONDO:0100039). For OMIM IDs, convert first.
    """
    try:
        # If OMIM ID given, find the MONDO equivalent
        mondo_id = disease_id
        if disease_id.startswith("OMIM:"):
            search = requests.get(
                f"{MONARCH_BASE}/search",
                params={"q": disease_id, "category": "biolink:Disease", "limit": 3},
                timeout=TIMEOUT,
            )
            if search.status_code == 200:
                items = search.json().get("items", [])
                for item in items:
                    if isinstance(item, dict):
                        candidate = item.get("id", "")
                        if isinstance(candidate, str) and candidate.startswith("MONDO:"):
                            mondo_id = candidate
                            break
                    elif isinstance(item, str) and item.startswith("MONDO:"):
                        mondo_id = item
                        break

        # Get phenotypes
        pheno = requests.get(
            f"{MONARCH_BASE}/entity/{mondo_id}/biolink:DiseaseToPhenotypicFeatureAssociation",
            params={"limit": 15},
            timeout=TIMEOUT,
        )
        phenotypes = []
        if pheno.status_code == 200:
            for item in pheno.json().get("items", [])[:15]:
                if not isinstance(item, dict):
                    continue
                obj = item.get("object", {})
                if isinstance(obj, dict):
                    phenotypes.append({
                        "hpo_id":    obj.get("id", ""),
                        "hpo_label": obj.get("name", "Unknown"),
                    })

        # Get causal genes
        genes_resp = requests.get(
            f"{MONARCH_BASE}/entity/{mondo_id}/biolink:CausalGeneToDiseaseAssociation",
            params={"limit": 10},
            timeout=TIMEOUT,
        )
        genes = []
        if genes_resp.status_code == 200:
            for item in genes_resp.json().get("items", [])[:10]:
                if not isinstance(item, dict):
                    continue
                subj = item.get("subject", {})
                if isinstance(subj, dict):
                    genes.append({
                        "gene_id":     subj.get("id", ""),
                        "gene_symbol": subj.get("symbol") or subj.get("name", "Unknown"),
                    })

        return {
            "original_id":  disease_id,
            "monarch_id":   mondo_id,
            "causal_genes": genes,
            "phenotypes":   phenotypes,
        }

    except Exception as e:
        return {"disease_id": disease_id, "error": str(e)}


def monarch_phenotype_search(hpo_ids: list[str]) -> dict:
    """Search Monarch for diseases matching a set of HPO terms."""
    try:
        resp = requests.get(
            f"{MONARCH_BASE}/semsim/search",
            params={
                "subjects":  hpo_ids,
                "object_set": "all",
                "metric":    "ancestor_information_content",
                "limit":     10,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            matches = [
                {
                    "disease_id":   m.get("object_id", ""),
                    "disease_name": m.get("object_label", "Unknown"),
                    "score":        round(float(m.get("score", 0)), 3),
                }
                for m in resp.json().get("matches", [])[:10]
            ]
            return {"query_hpo": hpo_ids, "matching_diseases": matches}
        return {"query_hpo": hpo_ids, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"query_hpo": hpo_ids, "error": str(e)}


# ── PubMed Tool ────────────────────────────────────────────────────────────

def pubmed_search(query: str, max_results: int = 5) -> dict:
    """
    Search PubMed for recent literature on a gene-disease topic.
    Returns titles, authors, year, and abstract snippets.
    Free NCBI eUtils API — no key required (rate limited to 3/sec).

    Args:
        query:       search string e.g. "CDKL5 epilepsy phenotype"
        max_results: number of papers to return (max 10)
    """
    try:
        # Search for PMIDs
        search_resp = requests.get(
            f"{PUBMED_BASE}/esearch.fcgi",
            params={
                "db":       "pubmed",
                "term":     query,
                "retmax":   min(max_results, 10),
                "sort":     "relevance",
                "retmode":  "json",
            },
            timeout=TIMEOUT,
        )
        search_resp.raise_for_status()
        pmids = search_resp.json().get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return {"query": query, "results": [], "note": "No results found"}

        # Fetch summaries
        summary_resp = requests.get(
            f"{PUBMED_BASE}/esummary.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "json",
            },
            timeout=TIMEOUT,
        )
        summary_resp.raise_for_status()
        data = summary_resp.json().get("result", {})

        papers = []
        for pmid in pmids:
            article = data.get(pmid, {})
            authors = article.get("authors", [])
            author_str = authors[0].get("name", "") if authors else "Unknown"
            if len(authors) > 1:
                author_str += f" et al."
            papers.append({
                "pmid":    pmid,
                "title":   article.get("title", "Unknown"),
                "authors": author_str,
                "year":    article.get("pubdate", "")[:4],
                "journal": article.get("source", ""),
                "url":     f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        return {"query": query, "results": papers}

    except Exception as e:
        return {"query": query, "error": str(e)}


# ── ClinVar Tool ───────────────────────────────────────────────────────────

def clinvar_gene_lookup(gene_symbol: str, max_results: int = 5) -> dict:
    """
    Look up pathogenic variants in ClinVar for a gene.
    Returns total count and representative variant titles.
    Free NCBI eUtils API — no key required.

    Args:
        gene_symbol: HGNC gene symbol e.g. CDKL5
        max_results: number of variants to return
    """
    try:
        # Search ClinVar for pathogenic/likely pathogenic variants
        search_resp = requests.get(
            f"{CLINVAR_BASE}/esearch.fcgi",
            params={
                "db":      "clinvar",
                "term":    f"{gene_symbol}[gene] AND (pathogenic[clnsig] OR likely+pathogenic[clnsig])",
                "retmax":  min(max_results, 10),
                "retmode": "json",
                "sort":    "relevance",
            },
            timeout=TIMEOUT,
        )
        search_resp.raise_for_status()
        result = search_resp.json().get("esearchresult", {})
        total  = int(result.get("count", 0))
        ids    = result.get("idlist", [])

        if not ids:
            return {"gene": gene_symbol, "total_pathogenic": 0, "variants": [],
                    "note": "No pathogenic variants found in ClinVar"}

        # Fetch XML summaries — more reliable than JSON for ClinVar
        summary_resp = requests.get(
            f"{CLINVAR_BASE}/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(ids), "retmode": "json", "version": "2.0"},
            timeout=TIMEOUT,
        )
        summary_resp.raise_for_status()
        data = summary_resp.json().get("result", {})

        variants = []
        for vid in ids:
            v = data.get(vid, {})
            if not isinstance(v, dict):
                continue

            # ClinVar v2.0 JSON: germline_classification.description
            classification = "Unknown"
            germline = v.get("germline_classification", {})
            if isinstance(germline, dict):
                classification = germline.get("description", "Unknown")

            # Conditions from supporting_submissions or trait_set
            conditions = []
            trait_set = v.get("trait_set", [])
            if isinstance(trait_set, list):
                for t in trait_set[:3]:
                    if isinstance(t, dict):
                        name = t.get("trait_name", "")
                        if name and name != "not specified" and name != "not provided":
                            conditions.append(name)

            variants.append({
                "variant_id":     vid,
                "title":          v.get("title", "Unknown variant"),
                "classification": classification,
                "conditions":     conditions,
            })

        return {
            "gene":             gene_symbol,
            "total_pathogenic": total,
            "variants_shown":   len(variants),
            "variants":         variants,
            "note": f"{total} pathogenic/likely pathogenic variants in ClinVar for {gene_symbol}",
        }

    except Exception as e:
        return {"gene": gene_symbol, "error": str(e)}


# ── Tool definitions for Anthropic API ────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "monarch_gene_lookup",
        "description": (
            "Look up a gene in the Monarch Initiative knowledge base to find its "
            "associated diseases. Use this to verify whether a candidate gene is "
            "known to cause diseases matching the patient's phenotype."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "HGNC gene symbol e.g. CDKL5, TNNI3, SCN1A",
                }
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "monarch_disease_lookup",
        "description": (
            "Look up a disease in Monarch to find its causal genes and characteristic "
            "phenotypes. Use MONDO IDs (e.g. MONDO:0100039) or OMIM IDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease ID e.g. MONDO:0100039 or OMIM:300672",
                }
            },
            "required": ["disease_id"],
        },
    },
    {
        "name": "monarch_phenotype_search",
        "description": (
            "Search Monarch Initiative for diseases that best match a set of HPO terms. "
            "Returns ranked disease matches by phenotype similarity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hpo_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of HPO IDs e.g. ['HP:0001249', 'HP:0001250']",
                }
            },
            "required": ["hpo_ids"],
        },
    },
    {
        "name": "pubmed_search",
        "description": (
            "Search PubMed for recent literature on a gene or disease topic. "
            "Use this to find evidence linking a candidate gene to the patient's phenotype, "
            "or to check recent reports of a gene-disease association."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query e.g. 'CDKL5 epilepsy phenotype' or 'SCN1A Dravet syndrome'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of papers to return (default 5, max 10)",
                    "default": 5,
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "clinvar_gene_lookup",
        "description": (
            "Look up pathogenic and likely pathogenic variants in ClinVar for a gene. "
            "Use this to check whether a candidate gene has established pathogenic variants "
            "and what conditions they are associated with."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "HGNC gene symbol e.g. CDKL5",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of variants to return (default 5)",
                    "default": 5,
                }
            },
            "required": ["gene_symbol"],
        },
    },
]


def dispatch(tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return JSON string result."""
    if tool_name == "monarch_gene_lookup":
        result = monarch_gene_lookup(tool_input["gene_symbol"])
    elif tool_name == "monarch_disease_lookup":
        result = monarch_disease_lookup(tool_input["disease_id"])
    elif tool_name == "monarch_phenotype_search":
        result = monarch_phenotype_search(tool_input["hpo_ids"])
    elif tool_name == "pubmed_search":
        result = pubmed_search(tool_input["query"],
                               tool_input.get("max_results", 5))
    elif tool_name == "clinvar_gene_lookup":
        result = clinvar_gene_lookup(tool_input["gene_symbol"],
                                     tool_input.get("max_results", 5))
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python rag_agentic/monarch_client.py gene CDKL5")
        print("       python rag_agentic/monarch_client.py disease MONDO:0100039")
        print("       python rag_agentic/monarch_client.py phenotype HP:0001249 HP:0001250")
        print("       python rag_agentic/monarch_client.py pubmed 'CDKL5 epilepsy'")
        print("       python rag_agentic/monarch_client.py clinvar CDKL5")
        sys.exit(1)

    mode = args[0]
    if mode == "gene" and len(args) > 1:
        print(json.dumps(monarch_gene_lookup(args[1]), indent=2))
    elif mode == "disease" and len(args) > 1:
        print(json.dumps(monarch_disease_lookup(args[1]), indent=2))
    elif mode == "phenotype" and len(args) > 1:
        print(json.dumps(monarch_phenotype_search(args[1:]), indent=2))
    elif mode == "pubmed" and len(args) > 1:
        print(json.dumps(pubmed_search(" ".join(args[1:])), indent=2))
    elif mode == "clinvar" and len(args) > 1:
        print(json.dumps(clinvar_gene_lookup(args[1]), indent=2))
    else:
        print("Unknown mode")