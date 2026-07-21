# Methodology
 
## Project overview
 
This project evaluates the ability of large language models (LLMs) to prioritise causal genes for rare genetic disease patients, benchmarked using the PhEval framework. The pipeline follows the workflow proposed by Jules Jacobsen (LBNL/Monarch Initiative):
 
```
HPOA → synthetic phenopackets → redaction → LLM / Exomiser → PhEval benchmark
```
 
---
 
## 1. Synthetic cohort generation
 
### Source data
- Human Phenotype Ontology Annotation (HPOA) file (`phenotype.hpoa`, version 2026-02-16)
- Generated using PhEval's `phenotype2phenopacket` tool
### Process
- 200 synthetic patient phenopackets generated from HPOA disease annotations
- Each phenopacket contains:
  - A unique patient ID (`patient_001` to `patient_200`)
  - A set of HPO phenotypic features (observed clinical signs)
  - The source OMIM disease identifier (in the full version)
### Redaction
- A redacted version of each phenopacket was created for input to the LLM
- Redacted phenopackets contain **only** HPO phenotypic features
- All gene, variant, disease, and publication identifiers are removed
- This ensures the model cannot derive the answer from identifiers in the input
---
 
## 2. Ground truth mapping
 
### Source
- `genes_to_disease.txt` from HPO release 2026-02-16
- `synthetic_patients_lookup.csv` — maps patient IDs to OMIM disease IDs
### Process
- OMIM disease IDs from the lookup file were matched to gene symbols in `genes_to_disease.txt`
- Only **MENDELIAN** association type retained (polygenic/susceptibility excluded)
- Where multiple genes mapped to a disease, the first listed gene was used as ground truth
- 151/200 patients successfully mapped to a ground truth gene
- 49/200 patients excluded — no Mendelian gene association found in the HPO database
---
 
## 3. LLM workflow (phenotype-only)
 
### Model
- Claude (claude-sonnet-4-6, Anthropic API)
### Prompt design
Each redacted phenopacket was converted to a natural language prompt listing the patient's HPO term labels. The model was asked to return a ranked list of the top 5 most likely causal genes in structured JSON format:
 
```json
{
  "patient_id": "patient_001",
  "top_genes": [
    {"rank": 1, "gene_symbol": "GENE1", "score": 0.95},
    ...
  ],
  "likely_diagnosis": "...",
  "confidence": "high/medium/low",
  "reasoning": "..."
}
```
 
### Execution
- Script: `run_llm_batch.py`
- All 200 patients processed automatically
- Results saved as individual JSON files in `llm_results_phenotype_only/`
---
 
## 4. PhEval benchmarking
 
### Conversion
- Script: `convert_llm_json_to_pheval.py`
- LLM JSON outputs converted to PhEval-compatible parquet files
- Each parquet file contains: `gene_symbol`, `gene_identifier`, `score`, `rank`, `grouping_id`, `true_positive`
### True positive flagging
- Script: `add_true_positive.py`
- `true_positive = True` where `gene_symbol` matches the ground truth gene for that patient
- Patients with no ground truth gene receive `true_positive = False` for all entries
### Benchmark execution
- Tool: `pheval-utils benchmark`
- Configuration: `benchmark_config.yaml`
- Gene analysis only (no variant or disease analysis at this stage)
- Score order: descending
### Metrics computed
- Top-k accuracy (k = 1, 3, 5, 10)
- Mean Reciprocal Rank (MRR)
- Mean Average Precision (MAP@k)
- NDCG
- ROC AUC / Precision-Recall AUC
- Sensitivity, specificity, F1
---
 
## 5. Scripts
 
| Script | Purpose |
|---|---|
| `run_llm_batch.py` | Batch LLM inference across all phenopackets |
| `convert_llm_json_to_pheval.py` | Convert LLM JSON results to PhEval parquet format |
| `build_ground_truth.py` | Build ground truth gene CSV from OMIM mappings |
| `add_true_positive.py` | Flag true positives in parquet files |
| `benchmark_config.yaml` | PhEval benchmark configuration |
 
---
 
## 6. Limitations
 
- Ground truth is a single gene per patient — multi-gene diseases handled by selecting the first listed Mendelian gene
- 49/200 patients excluded due to missing Mendelian gene mappings
- LLM outputs only 5 candidate genes — performance at higher k not measurable
- Phenotype-only baseline does not use variant data or Exomiser prioritisation
- Synthetic phenopackets may not fully represent real clinical presentations
 