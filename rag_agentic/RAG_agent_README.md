# RAG + Monarch Agentic Pipeline

Combines retrieval-augmented generation (HPOA vector store) with an iterative
Claude agent that calls the Monarch Initiative API before ranking candidate genes.

## Files

| File | Purpose |
|---|---|
| `monarch_client.py` | Monarch API wrapper — 3 tool functions |
| `rag_retriever.py` | ChromaDB index builder and HPO-label retriever |
| `agent.py` | Claude agentic loop with Monarch tool use |
| `run_pipeline.py` | Main runner — processes all 200 patients |
| `convert_to_pheval.py` | Convert results to PhEval parquet for benchmarking |

## How it works

1. **RAG retrieval** — embed patient HPO labels → find top-10 similar diseases in HPOA vector store
2. **Claude reasoning** — receives retrieved diseases + gene associations
3. **Monarch tool calls** — Claude calls gene/disease lookup tools to verify candidates
4. **Iteration** — up to 3 rounds of tool use before final answer
5. **PhEval** — results converted to parquet and benchmarked

## Setup

```bash
pip install anthropic chromadb sentence-transformers requests
export ANTHROPIC_API_KEY="your-key"
```

Requires `chroma_db_v2/` index — built by `run_llm_rag.py` on first run.

## Usage

```bash
# Test Monarch API
python monarch_client.py gene CDKL5
python monarch_client.py disease OMIM:613286
python monarch_client.py phenotype HP:0001249 HP:0001250

# Test retrieval
python rag_retriever.py HP:0001249 HP:0001250

# Test agent on dummy patient
python agent.py

# Run single patient
python run_pipeline.py --patient patient_001 --verbose

# Run all 200
python run_pipeline.py

# Convert for PhEval (on Apocrita)
python3 convert_to_pheval.py
```

## Monarch API tools available to Claude

- **monarch_gene_lookup(gene_symbol)** — diseases associated with a gene
- **monarch_disease_lookup(disease_id)** — causal genes + phenotypes for a disease
- **monarch_phenotype_search(hpo_ids)** — diseases ranked by HPO term match

No API key required. Base: `https://api-v3.monarchinitiative.org/v3/api`