# Experiment Log

## Experiment 1 — Phenotype-only LLM baseline (Claude Sonnet)

**Date:** 2026-06-02
**Status:** Complete

### Setup

- **Model:** claude-sonnet-4-6 (Anthropic API)
- **Input:** 200 synthetic redacted phenopackets (HPO terms only)
- **Prompt:** Phenotype-only — Claude given HPO term labels, asked to return top 5 ranked candidate genes as JSON
- **Output:** 200 JSON result files → converted to PhEval parquet format

### Cohort

| Item | Count |
|---|---|
| Total phenopackets | 200 |
| Successfully processed by LLM | 200 |
| Patients with ground truth gene mapped | 151 |
| Patients excluded (no Mendelian gene in HPO database) | 49 |
| Patients contributing to benchmark | 39 |

### Results

| Metric | Value |
|---|---|
| Top-1 accuracy | 43.6% (17/39) |
| Top-3 accuracy | 82.1% (32/39) |
| Top-5 accuracy | 100% (39/39) |
| MRR | 0.659 |
| MAP@1 | 0.436 |
| MAP@5 | 0.659 |

### Observations

- Claude returns correct gene in top-5 for only 39/151 mapped patients (25.8%)
- True overall top-1 rate across full cohort: ~11% (17/151)
- The LLM's constraint of returning only 5 candidate genes means 112 mapped patients scored zero — the correct gene was not among the top 5 returned. This limits direct comparison with Exomiser which ranks all ~35,000 genes
- 49 patients excluded due to missing Mendelian gene mappings in HPO database

### Files

- `llm_results_phenotype_only/` — raw LLM JSON outputs (200 files)
- `pheval_gene_results/` — PhEval parquet files (200 files)
- `ground_truth_genes_all.csv` — ground truth gene mapping for all 200 patients
- `benchmark_config.yaml` — PhEval benchmark configuration
- `llm_phenotype_only_baseline.duckdb` — benchmark results database
- `llm_phenotype_only_baseline_gene_rank_stats.svg`
- `llm_phenotype_only_baseline_gene_roc_curve.svg`
- `llm_phenotype_only_baseline_gene_pr_curve.svg`

---

## Experiment 2 — Exomiser phenotype-only (no LLM)

**Date:** 2026-06-02
**Status:** Complete

### Setup

- **Tool:** Exomiser 15.0.0, data version 2512, hg19
- **Mode:** phenotype-only preset (no VCF, no variant data)
- **Input:** 200 synthetic redacted phenopackets (HPO terms only)
- **Runner:** SLURM array job (200 parallel jobs, 8GB RAM, 30 min each)
- **Output:** 200 parquet files in `synthetic_results/pheval_gene_results/`

### Cohort

| Item | Count |
|---|---|
| Total phenopackets | 200 |
| Exomiser runs completed | 200 |
| Patients with ground truth gene mapped | 149 |
| Patients contributing to benchmark | 149 |

Note: Exomiser ranks all ~35,000 genes so all mapped patients contribute to benchmark.

### Results

| Metric | Value |
|---|---|
| Top-1 accuracy | 58.4% (87/149) |
| Top-3 accuracy | 67.1% (100/149) |
| Top-5 accuracy | 69.1% (103/149) |
| MRR | 0.645 |

### Observations

- Exomiser leads on top-1 accuracy but plateaus sharply — only 69.1% by top-5
- All 149 mapped patients contribute because Exomiser ranks all genes, unlike LLM experiments
- genePhenotypeScore used as ranking metric (geneCombinedScore near-zero without variant data)

### Files

- `synthetic_results/pheval_gene_results/` — 200 parquet files
- `benchmark_config_exomiser_only.yaml`
- `exomiser_only.duckdb`
- `exomiser_only_gene_rank_stats.svg`
- `exomiser_only_gene_roc_curve.svg`
- `exomiser_only_gene_pr_curve.svg`

---

## Experiment 3 — Exomiser-assisted LLM, full 200 patients (Claude Haiku)

**Date:** 2026-06-06
**Status:** Complete

### Setup

- **Model:** claude-haiku-4-5-20251001 (Anthropic API, used for patients 112-200)
- **Model (patients 1-111):** claude-sonnet-4-6
- **Exomiser version:** 15.0.0, data version 2512, hg19, phenotype-only preset
- **Input:** 200 redacted phenopackets + Exomiser top 10 candidate genes per patient
- **Prompt:** Phenotypes + Exomiser ranked candidates → Claude interpretation, top 5 genes as JSON
- **Output:** 200 JSON result files → PhEval parquet format

### Cohort

| Item | Count |
|---|---|
| Total phenopackets | 200 |
| Exomiser runs completed | 200 |
| LLM processed | 200 |
| Patients with ground truth gene mapped | 151 |
| Patients contributing to benchmark | 28 |

### Results

| Metric | Value |
|---|---|
| Top-1 accuracy | 53.6% (15/28) |
| Top-3 accuracy | 89.3% (25/28) |
| Top-5 accuracy | 100% (28/28) |
| MRR | 0.708 |

### Final three-way comparison

| Metric | Exomiser only (n=149) | Claude phenotype (n=39) | Claude + Exomiser (n=28) |
|---|---|---|---|
| Top-1 accuracy | 58.4% | 43.6% | 53.6% |
| Top-3 accuracy | 67.1% | 82.1% | 89.3% |
| Top-5 accuracy | 69.1% | 100% | 100% |
| MRR | 0.645 | 0.659 | 0.708 |

### Key findings

- Exomiser leads top-1 (58.4%) but plateaus sharply — only 69.1% by top-5
- Both LLM approaches reach 100% by top-5 — they cast a much broader net within their 5-gene window
- Claude + Exomiser achieves the best top-3 (89.3%) and highest MRR (0.708) — combining both approaches outperforms either alone
- The sample size disparity (149 vs 28-39) reflects a methodological difference: LLM returns only 5 genes so patients where the correct gene falls outside this window score zero and are excluded from ranked metrics. Increasing the LLM candidate output from 5 to 10 would significantly improve benchmark coverage
- Mixed model note: patients 1-111 used claude-sonnet-4-6, patients 112-200 used claude-haiku-4-5. This should be controlled in future experiments

### Files

- `llm_results_exomiser_assisted_full/` — raw LLM JSON outputs (200 files)
- `pheval_gene_results_exomiser_assisted_full/` — PhEval parquet files (200 files)
- `exomiser_assisted_full_run/` — benchmark run directory
- `benchmark_config_exomiser_assisted_full.yaml`
- `llm_exomiser_assisted_full.duckdb`
- `llm_exomiser_assisted_full_gene_rank_stats.svg`
- `llm_exomiser_assisted_full_gene_roc_curve.svg`
- `llm_exomiser_assisted_full_gene_pr_curve.svg`

---

## Experiment 4 — Increase LLM candidate genes from 5 to 10

**Date:** TBD
**Status:** Planned
**Rationale:** Currently 112+ mapped patients score zero because correct gene falls outside top-5. Returning top 10 genes would dramatically improve benchmark coverage and make comparison with Exomiser more valid.

---

## Experiment 5 — Controlled model comparison (Haiku vs Sonnet)

**Date:** TBD
**Status:** Planned
**Rationale:** Experiment 3 mixed two models. Rerunning all 200 with a single model (Haiku for cost) would give cleaner results.

---

## Experiment 6 — Agent-based workflow (Open Scientist)

**Date:** TBD
**Status:** Planned — Open Scientist access obtained, integration in progress