# PhEval LLM Benchmark

**MSc Bioinformatics — B2038 — Queen Mary University of London**  
Declan Courtney | Supervisors: Damian Smedley, Yasemin Bridges, Jules Jacobsen (LBNL)

Systematic benchmarking of large language model approaches for rare disease gene and disease prioritisation using the [PhEval](https://github.com/monarch-initiative/pheval) evaluation framework.

---

## Results Summary

### Gene-level benchmarking (n=158 patients with known Mendelian gene)

| Approach | Model | Top-1 | Top-3 | Top-5 | MRR |
|---|---|---|---|---|---|
| Exomiser phenotype-only (baseline) | — | 58.4% | 67.1% | 69.1% | 0.645 |
| **Claude RAG v2** | Sonnet 4.6 | **35.8%** | **46.7%** | **50.3%** | **0.423** |
| Claude RAG + Agentic | Sonnet 4.6 | 35.2% | 43.0% | 49.1% | 0.415 |
| Claude RAG + Exomiser scores | Sonnet 4.6 | 31.5% | 40.0% | 43.6% | 0.363 |
| Claude phenotype-only (10-gene) | Haiku 4.5 | 14.5% | 23.0% | 30.3% | 0.204 |
| Claude phenotype-only (5-gene) | Sonnet 4.6 | 12.7% | 23.0% | 29.1% | 0.189 |
| Claude + Exomiser assisted (5-gene) | Sonnet 4.6 | 9.7% | 15.2% | 17.0% | 0.124 |
| Claude + Exomiser no-anchor | Sonnet 4.6 | 9.1% | 11.5% | 12.7% | 0.106 |
| Claude + Exomiser assisted (10-gene) | Sonnet 4.6 | 8.5% | 13.9% | 15.8% | 0.116 |
| Claude CoT | Haiku 4.5 | 7.3% | 13.9% | 17.0% | 0.109 |
| Claude RAG v1 (HPO IDs — broken) | Sonnet 4.6 | 1.2% | 3.0% | 4.2% | 0.027 |

### Disease-level benchmarking (n=200 patients)

| Approach | Model | Top-1 | Top-3 | Top-5 | MRR |
|---|---|---|---|---|---|
| **Claude RAG disease-level** | Sonnet 4.6 | **32.5%** | **39.5%** | **45.5%** | **0.380** |
| Claude disease-level | Sonnet 4.6 | 9.0% | 12.5% | 14.5% | 0.110 |
| Claude disease-level | Haiku 4.5 | 2.5% | 5.5% | 7.0% | 0.039 |

### Comparison with MALCO (Reese, Chimirri, Bridges et al., Eur J Hum Genet 2026)

MALCO benchmarked 7 LLMs vs Exomiser on 5,213 real clinical cases (disease-level):

| | Top-1 |
|---|---|
| MALCO best LLM (o1-preview) | 23.6% |
| **Claude RAG disease-level (this work)** | **32.5%** |
| MALCO Exomiser | 35.5% |

**RAG disease-level exceeds the MALCO best LLM by 8.9 percentage points.**

---

## Key Findings

1. **RAG dramatically outperforms all other LLM approaches** — 35.8% top-1 gene-level vs 12.7% for phenotype-only. HPOA retrieval at query time gives Claude the structured disease knowledge it needs.

2. **HPO labels vs IDs is critical** — using HPO term labels ("Intellectual disability") vs IDs ("HP:0001249") for embedding accounts for a 1.2% → 35.8% improvement. The sentence transformer model requires natural language, not ontology codes.

3. **Anchoring effect is consistent** — giving Claude Exomiser's candidates consistently reduces performance vs RAG alone (31.5% vs 35.8%). When the correct gene is absent from Exomiser's top-10, Claude cannot recover it.

4. **Retrieval dominates over reasoning depth** — RAG + Agentic (35.2%) marginally underperforms pure RAG (35.8%), suggesting retrieval quality matters more than iterative tool-call reasoning when the knowledge base is already well-matched.

5. **Model quality matters** — Sonnet disease-level (9.0%) is 3.6× better than Haiku (2.5%). Chain-of-thought with Haiku (7.3%) underperforms standard Sonnet prompting (12.7%).

6. **Exomiser still leads at gene-level** — 58.4% vs RAG 35.8%. Systematic HPO ontology scoring over curated disease-gene knowledge remains superior.

---

## Repository Structure

```
pheval-llm-benchmark/
├── README.md
├── .gitignore
├── reorganise_repo.ps1
│
├── pipelines/                         # LLM pipeline scripts
│   ├── run_phenotype_only.py          # Baseline: HPO terms only
│   ├── run_phenotype_only_gemini.py   # Gemini variant
│   ├── run_exomiser_assisted.py       # Exomiser top genes + Claude re-ranking
│   ├── run_cot.py                     # Chain-of-thought prompting
│   ├── run_disease_level.py           # Disease-level (OMIM IDs)
│   ├── run_rag.py                     # RAG pipeline (HPOA vector store)
│   ├── run_rag_disease.py             # Disease-level RAG
│   ├── run_rag_exomiser.py            # RAG + Exomiser phenotype scores
│   └── rag_agentic/                   # Agentic pipeline
│       ├── agent.py                   # Claude agentic loop
│       ├── monarch_client.py          # Monarch/PubMed/ClinVar tool functions
│       ├── rag_retriever.py           # ChromaDB index and retrieval
│       ├── run_pipeline.py            # Main runner
│       ├── convert_to_pheval.py       # PhEval converter
│       └── README.md
│
├── converters/                        # PhEval post-processing
│   ├── convert_gene_to_pheval.py
│   └── convert_disease_to_pheval.py
│
├── pheval_results/
│   └── configs/                       # PhEval benchmark YAML configs
│
├── figures/                           # PhEval output plots (SVG)
│
└── docs/                              # Notes and logs
    ├── experiment_log.md
    ├── method_correction_log.md
    └── methodology_notes.md
```

---

## Data

**200 synthetic phenopackets** generated from HPO Annotation (HPOA v2026-02-16) using [phenotype2phenopacket](https://github.com/monarch-initiative/phenotype2phenopacket):
- 200 distinct Mendelian diseases
- 158/200 have a known Mendelian gene (`p2p add-genes`)
- 42/200 excluded from gene-level benchmarking (no known Mendelian gene)
- Phenopackets redacted before LLM input — disease ID, gene and variants stripped

**Exomiser v15.0.0**, data release 2512, hg19, phenotype-only mode, run on QMUL Apocrita HPC.

> Note: large data files (phenopackets, Exomiser results, LLM outputs, ChromaDB index) are not tracked in this repo — stored on Apocrita HPC and locally. See `.gitignore`.

---

## Setup

```bash
pip install anthropic chromadb sentence-transformers polars pyarrow pheval requests
export ANTHROPIC_API_KEY="your-key"
```

---

## Running Experiments

```bash
# Phenotype-only baseline
python pipelines/run_phenotype_only.py

# RAG pipeline (builds ChromaDB index from HPOA on first run ~5 min)
python pipelines/run_rag.py

# Disease-level RAG
python pipelines/run_rag_disease.py

# RAG + Exomiser phenotype scores
python pipelines/run_rag_exomiser.py

# Exomiser-assisted re-ranking
python pipelines/run_exomiser_assisted.py

# Agentic pipeline (Monarch + PubMed + ClinVar tools)
python pipelines/rag_agentic/run_pipeline.py --limit 5 --verbose
python pipelines/rag_agentic/run_pipeline.py
```

## Converting and Benchmarking

```bash
# Gene-level
python converters/convert_gene_to_pheval.py

# Disease-level
python converters/convert_disease_to_pheval.py

# Benchmark (on Apocrita with PhEval installed)
pheval-utils benchmark --run-yaml pheval_results/configs/benchmark_config_rag_v2.yaml
```

---

## RAG Pipeline Details

- **Vector store:** ChromaDB (persistent), 12,996 diseases from HPOA
- **Embedding model:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Critical:** embed HPO term **labels** not IDs — IDs are opaque strings that transformers cannot match semantically
- **Gene lookup:** `genes_to_disease.txt` (col 1=gene_symbol, col 3=disease_id) — 10,992 associations

## Agentic Pipeline Tools

Claude has access to three external APIs (no key required):
- **Monarch Initiative** — gene-disease associations, phenotype matching
- **PubMed** — literature search via NCBI eUtils
- **ClinVar** — pathogenic variant counts via NCBI eUtils

---

## Infrastructure

- **HPC:** Apocrita (QMUL), user bt251044, `pheval-env` (Python 3.11)
- **Local:** Windows, PyCharm
- **Models:** Claude Sonnet 4.6 (main), Haiku 4.5 (CoT + disease-level)
- **PhEval:** v0.7.13

---

## References

- Reese JT, Chimirri L, Bridges Y, et al. Systematic benchmarking demonstrates LLMs have not reached the diagnostic accuracy of traditional rare-disease decision support tools. *Eur J Hum Genet.* 2026;34:498–504.
- Bridges YS, et al. Towards a standard benchmark for variant and gene prioritisation algorithms: PhEval. *BMC Bioinformatics.* 2025;26:87.
- Tu T, Saab K, et al. Genetic Diagnosis with LLMs. *Adv Sci.* 2026. doi:10.1002/advs.202518656
- Yang H, et al. RDguru: Rare disease diagnosis using GPT and RAG. *IEEE J Biomed Health Inform.* 2024.
- Robinson PN, et al. Phenopackets: A GA4GH standard for sharing disease and phenotype data. *Nat Biotechnol.* 2022.