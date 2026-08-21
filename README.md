# PhEval LLM Benchmark: Improving Genomic Disease Diagnosis with Large Language Models

MSc dissertation project (B2038) benchmarking LLM-based approaches for rare disease gene and disease prioritisation against Exomiser, using the PhEval evaluation framework.

**Author:** Declan Courtney, MSc Bioinformatics, Queen Mary University of London
**Supervisors:** Damian Smedley, Yasemin Bridges, Julius Jacobsen (WHRI, Medical School)
**Date:** 21st August 2026

## Overview

This project systematically evaluates whether large language models, used alone, combined with retrieval-augmented generation (RAG), or combined with agentic tool use, can match or complement Exomiser's phenotype-driven variant prioritisation for rare disease diagnosis. Ten gene-level approaches and three disease-level approaches were benchmarked against Exomiser v15.0.0 (phenotype-only mode) on 200 synthetic phenopackets covering 200 distinct Mendelian diseases, using PhEval v0.7.13, with pairwise significance assessed by McNemar's test.

**Research question:** Can retrieval-augmented generation or agentic approaches substantially improve LLM performance for rare disease gene and disease prioritisation, and how do these approaches compare to Exomiser and published benchmarks?

## Repository structure

```
pipelines/       LLM-calling scripts for each benchmarked approach
rag_agentic/      Agentic pipeline (RAG + Monarch/PubMed/ClinVar tool use)
analysis/         Statistical analysis and verification scripts
figures/          Figure-generation scripts
output/           Generated figure files (SVG/PNG)
data/             Final CSVs, pickled correctness data, PhEval result summaries
pheval_results/   Converted PhEval gene/disease result parquet folders
archive/          Superseded scripts and intermediate outputs, kept for provenance
```

## Approaches benchmarked

**Gene-level (n=158, patients with a known Mendelian gene):**

- **Phenotype-only prompting**: HPO terms only, no external evidence (Sonnet 4.6, 5-gene; Haiku 4.5, 10-gene)
- **Exomiser-assisted** (anchored 5-gene, anchored 10-gene, no-anchor): Claude given Exomiser's genuine top candidate genes
- **Chain-of-thought (CoT) prompting** (Haiku 4.5): step-by-step reasoning before final answer
- **RAG v1 / v2**: retrieval over an HPOA-derived ChromaDB vector store, comparing HPO identifiers (v1) vs. HPO term labels (v2) as embedding input
- **RAG + Agentic**: RAG retrieval plus up to 3 rounds of external tool calls (Monarch Initiative, PubMed, ClinVar)
- **RAG + Exomiser**: RAG retrieval combined with Exomiser's genuine phenotype-similarity candidates

**Disease-level (n=200):**

- Disease-level prompting (Sonnet 4.6, Haiku 4.5)
- Disease-level RAG (Sonnet 4.6)

Full prompt text for every approach is given in Appendix A of the dissertation.

## Key results

| Approach | Model | Top-1 (%) | MRR | n |
|---|---|---|---|---|
| Exomiser (phenotype-only) | – | **58.4** | 0.645 | 149 |
| RAG + Exomiser (fixed) | Sonnet 4.6 | 55.2 | 0.625 | 158 |
| Exomiser-assisted, 5-gene (fixed) | Sonnet 4.6 | 43.6 | 0.529 | 158 |
| Exomiser-assisted, 10-gene (fixed) | Sonnet 4.6 | 41.8 | 0.528 | 158 |
| Exomiser no-anchor (fixed) | Sonnet 4.6 | 38.8 | 0.504 | 158 |
| RAG v2 (HPO labels) | Sonnet 4.6 | 35.8 | 0.423 | 158 |
| RAG + Agentic | Sonnet 4.6 | 35.2 | 0.415 | 158 |
| Phenotype-only (10-gene) | Haiku 4.5 | 14.5 | 0.204 | 158 |
| Phenotype-only (5-gene) | Sonnet 4.6 | 12.7 | 0.189 | 158 |
| Chain-of-thought | Haiku 4.5 | 7.3 | 0.109 | 158 |
| RAG v1 (HPO IDs) | Sonnet 4.6 | 1.2 | 0.027 | 158 |
| **Disease-level RAG** | Sonnet 4.6 | 32.5 | 0.380 | 200 |
| Disease-level (no RAG) | Sonnet 4.6 | 9.0 | 0.110 | 200 |
| Disease-level (no RAG) | Haiku 4.5 | 2.5 | 0.039 | 200 |

Full metrics (top-1/3/5, MRR) for every approach, including comparison against Reese et al. (2026), are in Table 1 of the dissertation.

### Headline findings

- **A three-tier performance structure emerged at gene level**: RAG + Exomiser stood significantly apart at the top (p<0.001 vs. every other LLM approach); a middle tier of five approaches (RAG v2, RAG+Agentic, and the three Exomiser-assisted variants) were statistically indistinguishable from one another; phenotype-only and chain-of-thought prompting formed the weakest, mutually indistinguishable tier.
- **HPO term representation was the single largest RAG design factor tested**: natural-language labels (35.8% top-1) vastly outperformed raw HPO identifiers (1.2% top-1) as embedding input, a 29.8 percentage point difference.
- **Agentic tool use (Monarch Initiative, PubMed, ClinVar) added no measurable benefit over retrieval alone** (RAG+Agentic vs. RAG v2, χ²=0.00, p=1.0), though it remained significantly below RAG + Exomiser.
- **Disease-level RAG (32.5% top-1) exceeded the best LLM result reported by Reese et al. (2026)** (o1-preview, 23.6% top-1) by 8.9 percentage points, though the two cohorts differ in size, origin, and pairing, so no cross-study significance test was possible.
- **Exomiser remained the strongest approach overall** (58.4% top-1, phenotype-only mode), with RAG + Exomiser the only LLM approach approaching it (3.2 percentage point gap).

## Statistical methods

Pairwise significance between LLM approaches was assessed using McNemar's test (Yates-corrected) on paired top-1 correct/incorrect outcomes, implemented via `statsmodels`. Exomiser was evaluated on a slightly different patient subset (n=149 vs. n=158) and so was instead compared using non-overlapping 95% Wilson confidence intervals. No correction was applied a priori across the 31 pairwise comparisons, as these characterised differences between conditions rather than a single confirmatory hypothesis; robustness to Bonferroni and Holm-Bonferroni correction was checked directly and all 20 uncorrected-significant results remained significant under both; see `analysis/multiple_comparisons_check.py`.

## Known methodological corrections

Three data-processing issues were identified and corrected during this project, and are disclosed in full in the dissertation's Methods and Limitations sections:

1. **Redacted-phenopacket ground truth.** An initial run passed redacted phenopackets (no `interpretations` field) into PhEval's post-processing, so no ground-truth gene could be resolved and only a small, non-representative subset of patients were scored. Corrected by using separately gene-annotated phenopackets (n=158) that were never passed to any LLM.
2. **Exomiser candidate-gene extraction bug.** A sort/deduplication ordering bug (deduplicating after sorting by score, rather than before) caused near-arbitrary gene lists to be shown to Claude instead of Exomiser's genuine top candidates, affecting the Exomiser-assisted, no-anchor, and RAG + Exomiser conditions. This was identified through manual inspection of individual patient outputs, not from summary statistics: an apparent "anchoring" effect in an earlier analysis (Exomiser evidence *reducing* LLM accuracy) turned out to be an artefact of this bug and disappeared once corrected. All three affected experiments were re-run in full.
3. **True-positive labelling.** A data-quality issue in one converted PhEval result set caused unreliable `true_positive` labelling; patient-level correctness for all statistical comparisons was independently re-derived by comparing each approach's top-ranked gene directly against the ground-truth causal gene.

A subsequent ablation investigated whether a padding fallback in the RAG + Exomiser pipeline (which backfills short candidate lists using Exomiser/RAG genes when Claude's own output falls short) materially affected the headline result. Padded vs. unpadded runs achieved 55.2% vs. 37.3% top-1 accuracy respectively, but padding directly changed the rank-1 prediction for only 2 of 200 patients; most of the gap reflects run-to-run variance in Claude's own reasoning (173/198 patients agreed exactly across both runs). See `data/padding_comparison_full.csv` and Appendix B of the dissertation.

## Limitations

- **Synthetic cohort**, generated by `phenotype2phenopacket` from HPOA, likely has more complete/idealised phenotype profiles than real clinical cases, and shares a knowledge base with the RAG retrieval step. A direct circularity check found RAG's top-retrieved disease matched the true source disease in 29.1% of patients (42.4% in the top three), both below RAG's actual gene-level accuracy, suggesting circularity is a real but partial contributor, not the primary driver of RAG's performance.
- **Exomiser n=149 vs. 158 discrepancy**, traced to PhEval's internal `check_incomplete_gene_record` filtering step; only one of the nine excluded cases was fully resolved.
- **Phenotype-only mode only**: no genomic variant data was used for either Exomiser or the LLM approaches.
- **Single model family** (Claude Sonnet 4.6 / Haiku 4.5): cross-provider comparison was attempted but not completed within the project timeline.
- Fine-tuning, one of five originally planned approach categories, was not attempted due to compute/budget constraints.

Full discussion is in the dissertation's Limitations and Future Work sections.

## Reproducing the analysis

Each script in `analysis/` and `figures/` reads from the corresponding CSV/pickle files in `data/`. The original PhEval benchmark configurations (`benchmark_config_*.yaml`) and raw LLM outputs are not included in this repository due to size; contact the author for access if needed for reproducibility purposes.

## Dependencies

Key packages: `anthropic`, `polars`, `duckdb`, `statsmodels`, `pheval`, `matplotlib`. See `requirements.txt` for the full list.

