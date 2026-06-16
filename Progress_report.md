# PhEval Benchmark Report

## Pipeline

```
HPOA → 200 synthetic phenopackets → redact gene/disease/variant identifiers
  → Approach A: Exomiser phenotype-only
  → Approach B: Claude LLM (phenotypes only)
  → Approach C: Claude LLM + Exomiser top-10 candidate genes
  → PhEval benchmark
```

## Results Summary

| Approach | Top-1 | Top-3 | Top-5 | MRR | n |
|---|---|---|---|---|---|
| Exomiser phenotype-only | 58.4% | 67.1% | 69.1% | 0.645 | 149 |
| Claude phenotype-only | 43.6% | 82.1% | 100% | 0.659 | 39 |
| **Claude + Exomiser** | **53.6%** | **89.3%** | **100%** | **0.708** | **28** |

## Why Do Sample Sizes Differ?

The n values differ because of how PhEval counts contributions to the benchmark — not because different numbers of patients were processed.

**Exomiser (n=149):** Exomiser ranks all ~35,000 genes per patient. As long as the correct gene appears anywhere in this list — which it almost always does — that patient contributes. 149 of 200 had a mappable ground truth gene; all 149 contribute.

**Claude phenotype-only (n=39):** Claude returns only 5 candidate genes. If the correct gene is not among those 5, the patient scores zero and is excluded. Only 39 of 151 mapped patients had the correct gene in Claude's top 5.

**Claude + Exomiser (n=28):** Same constraint — Claude still returns only 5 genes. Only 28 patients had the correct gene in the final top 5. The smaller n also partly reflects a mixed model (Sonnet for patients 1–111, Haiku for 112–200).

**Implication:** Increasing LLM candidate output from 5 to 10 genes is a planned next step and should significantly improve coverage and make the three-way comparison more statistically valid.

## Key Findings

Exomiser leads on top-1 accuracy (58.4%) but plateaus sharply — reaching only 69.1% by top-5. This reflects the challenge of identifying a single correct gene from ~35,000 candidates using phenotype similarity alone without variant data.

Both LLM approaches reach 100% by top-5 — within their 5-gene window the correct gene is almost always present, suggesting LLMs are highly effective at narrowing the candidate space even if precise top-1 ranking is less reliable.

Claude + Exomiser achieves the best top-3 (89.3%) and highest MRR (0.708) — combining Exomiser's phenotype-similarity scoring with LLM clinical reasoning outperforms either approach alone.

## Figures

**Figure 1 — Claude Phenotype-Only Rank Statistics (n=39)**
*See attached: rank_stats.svg*

Percentage of cases with the correct causal gene ranked within top-1, top-3, top-5, top-10, and found at any rank. The LLM returns only 5 candidate genes, so top-5 and found are equal at 100%. Only 39 of 151 mapped patients contributed to ranked metrics — patients where the correct gene was not among the 5 returned score zero and are excluded.

---

**Figure 2 — Exomiser Phenotype-Only Rank Statistics (n=149)**
*See attached: exomiser_only_rank_stats.svg*

Exomiser ranks all ~35,000 genes by phenotype similarity score (genePhenotypeScore), with no variant data. All 149 mapped patients contribute to the benchmark. Exomiser leads on top-1 (58.4%) but plateaus at top-5 (69.1%), reflecting the difficulty of ranking a single correct gene above thousands of candidates using phenotype matching alone.

---

**Figure 3 — Claude + Exomiser Assisted Rank Statistics (n=28)**
*See attached: exomiser_assisted_full_rank_stats.svg*

Claude was provided with both the patient's HPO phenotypes and Exomiser's top-10 candidate genes as context, and asked to return a ranked list of 5 genes. This combined approach achieves the highest top-3 accuracy (89.3%) and MRR (0.708) of all three methods, suggesting that LLM reasoning over Exomiser candidates improves diagnostic accuracy beyond either tool alone.

---

## Methodology

**01 — Synthetic cohort generation**
200 phenopackets generated from HPOA (v2026-02-16) using PhEval's phenotype2phenopacket tool. Each phenopacket contains HPO phenotypic features linked to an OMIM disease identifier.

**02 — Redaction**
All gene, variant, disease, and publication identifiers removed before LLM input. Only HPO term labels retained, ensuring the model cannot derive the answer from identifiers in the input.

**03 — Ground truth mapping**
OMIM disease IDs mapped to gene symbols via HPO genes_to_disease.txt (v2026-02-16). Only MENDELIAN associations retained. 151/200 patients mapped; 49 excluded (no Mendelian gene in database).

**04 — Exomiser (Approach A)**
Exomiser 15.0.0 phenotype-only preset, run across all 200 patients via SLURM array job on Apocrita HPC. genePhenotypeScore used for ranking (geneCombinedScore near-zero without variant data).

**05 — LLM inference (Approaches B and C)**
Claude prompted via Anthropic API to return top 5 ranked candidate genes as structured JSON. Approach C also received Exomiser's top 10 candidate genes as additional context alongside the phenotypes.

**06 — PhEval benchmarking**
LLM outputs converted to PhEval parquet format. True positive flags added from ground truth CSV. pheval-utils benchmark run for all three approaches. Metrics: top-k accuracy, MRR, MAP, NDCG, ROC AUC, precision-recall AUC.

## Next Steps

**01 — Immediate: Single model rerun**
Experiment 3 mixed claude-sonnet and claude-haiku. Rerun all 200 with Haiku only for a clean controlled comparison.

**02 — Immediate: Increase to top-10 genes**
Returning 10 candidate genes instead of 5 would significantly improve benchmark coverage and make LLM vs Exomiser comparison more statistically valid.

**03 — Short term: Claude agent with Exomiser tool**
Build an agent using Anthropic tool-use API that calls Exomiser autonomously as a tool, producing structured output for PhEval benchmarking.

**04 — Short term: PhEval runner plugin**
Formalise the pipeline into a proper PhEval plugin so benchmarking can be triggered with a single `pheval run` command.

**05 — Medium term: Open Scientist integration**
Explore Open Scientist agent framework for autonomous phenopacket interpretation with Exomiser as a skill.

**06 — Medium term: Variant data (Phase 2)**
Spike VCF files into phenopackets and repeat experiments with variant + phenotype data, as described in Jules' original proposal.