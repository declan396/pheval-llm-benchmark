# PhEval LLM Benchmark

MSc Bioinformatics — B2038 — Queen Mary University of London
**Declan Courtney** | Supervisors: Damian Smedley, Yasemin Bridges, Jules Jacobsen (LBNL)

Benchmarking large language model approaches for rare disease gene prioritisation using the [PhEval](https://github.com/monarch-initiative/pheval) evaluation framework.

---

## Project Overview

This project evaluates whether LLM-based approaches can complement or improve upon [Exomiser](https://github.com/exomiser/Exomiser) — the gold-standard rare disease gene prioritisation tool used by the NHS Genomic Medicine Service — for phenotype-driven gene prioritisation.

All experiments use **phenotype-only mode** (no genomic variant data), benchmarked against 200 synthetic phenopackets covering 200 distinct Mendelian diseases.

---

## Results Summary

All approaches benchmarked using PhEval `generate_gene_result` against gene-annotated synthetic phenopackets.

### Gene-level benchmarking (n=158 patients with known Mendelian gene)

| Approach | Model | Top-1 | Top-3 | Top-5 | MRR |
|---|---|---|---|---|---|
| Exomiser phenotype-only | — | 58.4% | 67.1% | 69.1% | 0.645 |
| **Claude RAG v2** | Sonnet 4.6 | **35.8%** | **46.7%** | **50.3%** | **0.423** |
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
| Claude disease-level | Sonnet 4.6 | 9.0% | 12.5% | 14.5% | 0.110 |
| Claude disease-level | Haiku 4.5 | 2.5% | 5.5% | 7.0% | 0.039 |

### Comparison with MALCO paper (Reese, Chimirri, Bridges et al., Eur J Hum Genet 2026)

MALCO benchmarked 7 LLMs vs Exomiser on 5,213 real clinical cases (disease-level):
- Best LLM (o1-preview): 23.6% top-1
- Exomiser: 35.5% top-1

Our RAG v2 approach (35.8% top-1 gene-level) exceeds the MALCO best LLM result, though direct comparison is limited by different task levels (gene vs disease) and cohort types (synthetic vs real).

---

## Repository Structure

```
pheval-llm-benchmark/
├── phenopackets/                    # Redacted synthetic phenopackets (LLM input)
├── hpo_resources/
│   ├── phenotype.hpoa               # HPO Annotation database v2026-02-16
│   └── genes_to_disease.txt         # Gene-disease associations
├── exomiser_results/                # Exomiser parquet output files
│
├── run_llm_batch.py                 # Phenotype-only (Anthropic API)
├── run_llm_batch_gemini.py          # Phenotype-only (Gemini free tier)
├── run_llm_exomiser_assisted.py     # Exomiser-assisted (anchored)
├── run_llm_cot.py                   # Chain-of-thought prompting
├── run_llm_disease_level.py         # Disease-level (OMIM IDs)
├── run_llm_rag.py                   # RAG pipeline (HPOA vector store)
│
├── convert_llm_to_pheval.py         # Gene-level PhEval converter
├── convert_disease_to_pheval.py     # Disease-level PhEval converter
│
├── agentic/                         # Agentic pipeline prototype
│   ├── omim_client.py               # OMIM API wrapper
│   ├── phenopacket_loader.py        # Load HPO terms from phenopacket
│   ├── exomiser_loader.py           # Load Exomiser parquet results
│   ├── agent.py                     # Claude agentic loop (tool use)
│   ├── run_pipeline.py              # Main agentic pipeline runner
│   └── convert_to_pheval.py        # PhEval converter for agentic results
│
└── README.md
```

---

## Data

**200 synthetic phenopackets** generated from HPO Annotation (HPOA v2026-02-16) using [phenotype2phenopacket](https://github.com/monarch-initiative/phenotype2phenopacket):
- 200 distinct Mendelian diseases
- 158/200 have a known Mendelian gene (p2p add-genes)
- 42/200 excluded from gene-level benchmarking (no known gene)
- Phenopackets redacted before LLM input (disease ID, gene, variants stripped)

**Exomiser v15.0.0**, data release 2512, hg19, phenotype-only mode.

---

## Methods

### PhEval benchmarking (corrected methodology)

All results benchmarked using `pheval generate_gene_result` with gene-annotated phenopackets (`synthetic_patients_with_genes/`). PhEval determines true positives from the `interpretations` field internally — no manual flagging.

Stem mapping via `synthetic_patients_lookup.csv` maps `patient_001` → `OMIM_100700_patient_1`.

### RAG pipeline (run_llm_rag.py)

1. Parse HPOA → disease-HPO label mapping
2. Embed disease profiles using `all-MiniLM-L6-v2` sentence transformer
3. Store in ChromaDB (persistent local vector store)
4. For each patient: embed HPO labels → retrieve top-10 similar diseases
5. Inject retrieved diseases + gene associations into Claude prompt
6. Claude returns ranked gene list as JSON

**Critical finding:** Using HPO term **labels** (e.g. "Intellectual disability") rather than **IDs** (e.g. "HP:0001249") for embedding is essential — IDs are opaque strings that sentence transformers cannot match semantically. RAG v1 used IDs (1.2% top-1); RAG v2 used labels (35.8% top-1).

### Agentic pipeline (agentic/)

Prototype Claude agent with OMIM tool use. Claude iteratively calls OMIM to look up gene-disease associations before returning a final ranked list (up to 3 rounds). Awaiting OMIM API access for full PhEval evaluation.

---

## Setup

### Requirements

```bash
pip install anthropic google-generativeai chromadb sentence-transformers polars pyarrow pheval
```

### Environment variables

```bash
export ANTHROPIC_API_KEY="your-key"    # Required for Claude runs
export OMIM_API_KEY="your-key"         # Required for agentic pipeline
```

### Running experiments

```bash
# Phenotype-only (5-gene, Sonnet)
python run_llm_batch.py

# RAG pipeline (builds ChromaDB index on first run)
python run_llm_rag.py

# Exomiser-assisted (no anchoring)
python run_llm_exomiser_assisted.py

# Disease-level
python run_llm_disease_level.py

# Chain-of-thought
python run_llm_cot.py
```

### Converting results for PhEval

```bash
# Gene-level
python convert_llm_to_pheval.py

# Disease-level
python convert_disease_to_pheval.py

# Then benchmark
pheval-utils benchmark --run-yaml benchmark_config.yaml
```

---

## Key Findings

1. **RAG dramatically outperforms all other LLM approaches** — 35.8% top-1 vs 12.7% for phenotype-only. Retrieval of phenotypically similar diseases from HPOA at query time gives Claude the structured knowledge it needs.

2. **HPO label quality is critical for RAG** — using HPO IDs as embedding inputs gives 1.2% top-1; switching to labels gives 35.8%. The sentence transformer model requires natural language, not ontology codes.

3. **Exomiser-assisted approaches underperform phenotype-only** — giving Claude Exomiser's top-10 candidates causes anchoring: Claude stays too close to the Exomiser list. Removing the anchoring instruction made performance worse, not better — suggesting the issue is the 5-gene output constraint, not prompt wording.

4. **Model quality matters more than prompting strategy** — Sonnet disease-level (9.0%) is 3.6× better than Haiku (2.5%). Chain-of-thought with Haiku (7.3%) underperforms standard Sonnet prompting (12.7%).

5. **Exomiser still leads** — 58.4% top-1 vs RAG's 35.8%. Exomiser's systematic HPO ontology scoring over curated disease-gene knowledge remains superior for gene-level prediction from phenotype alone.

---

## Next Steps

- **RAG + Monarch agentic pipeline** — combine HPOA retrieval with iterative Monarch Initiative API tool calls (no API key required)
- **Agentic pipeline evaluation** — full PhEval benchmark once OMIM API key arrives
- **Variant evidence** — add WGS/WES variant data (Exomiser achieves 82.6% top-1 with variants vs 58.4% phenotype-only)
- **Disease-level RAG** — apply RAG to disease-level prediction for direct MALCO comparison
- **Fine-tuning** — train on phenopacket-store cases (longer term, needs GPU compute)

---

## References

- Reese JT, Chimirri L, Bridges Y, et al. Systematic benchmarking demonstrates LLMs have not reached the diagnostic accuracy of traditional rare-disease decision support tools. *Eur J Hum Genet.* 2026;34:498–504.
- Bridges YS, et al. Towards a standard benchmark for variant and gene prioritisation algorithms: PhEval. *BMC Bioinformatics.* 2025;26:87.
- Tu T, Saab K, et al. Genetic Diagnosis with LLMs. *Adv Sci.* 2026. doi:10.1002/advs.202518656
- Yang H, et al. RDguru: Rare disease diagnosis using GPT and RAG. *IEEE J Biomed Health Inform.* 2024.
- Robinson PN, et al. Phenopackets: A GA4GH standard for sharing disease and phenotype data. *Nat Biotechnol.* 2022.