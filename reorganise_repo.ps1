# reorganise_repo.ps1
# Run from: C:\Users\decla\PycharmProjects\Phenopackets_AI
# Reorganises the repo into a clean professional structure

# ── Create new directories ─────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path "pipelines"
New-Item -ItemType Directory -Force -Path "pipelines\rag_agentic"
New-Item -ItemType Directory -Force -Path "converters"
New-Item -ItemType Directory -Force -Path "pheval_results\configs"
New-Item -ItemType Directory -Force -Path "figures"
New-Item -ItemType Directory -Force -Path "docs"

# ── Move pipeline scripts ──────────────────────────────────────────────────
git mv run_llm_batch.py              pipelines/run_phenotype_only.py
git mv run_llm_exomiser_assisted.py  pipelines/run_exomiser_assisted.py
git mv run_llm_cot.py                pipelines/run_cot.py
git mv run_llm_disease_level.py      pipelines/run_disease_level.py
git mv run_llm_rag.py                pipelines/run_rag.py
git mv run_llm_rag_disease.py        pipelines/run_rag_disease.py
git mv llm_rag_v2_exomiser.py        pipelines/run_rag_exomiser.py
git mv run_llm_batch_gemini.py       pipelines/run_phenotype_only_gemini.py

# ── Move agentic pipeline ──────────────────────────────────────────────────
git mv rag_agentic/agent.py              pipelines/rag_agentic/agent.py
git mv rag_agentic/monarch_client.py     pipelines/rag_agentic/monarch_client.py
git mv rag_agentic/rag_retriever.py      pipelines/rag_agentic/rag_retriever.py
git mv rag_agentic/run_pipeline.py       pipelines/rag_agentic/run_pipeline.py
git mv rag_agentic/convert_to_pheval.py  pipelines/rag_agentic/convert_to_pheval.py
git mv rag_agentic/README.md             pipelines/rag_agentic/README.md

# ── Move converters ────────────────────────────────────────────────────────
git mv convert_llm_to_pheval.py     converters/convert_gene_to_pheval.py
git mv convert_disease_to_pheval.py converters/convert_disease_to_pheval.py

# ── Move benchmark configs ─────────────────────────────────────────────────
Get-ChildItem "pheval_results" -Filter "*.yaml" | ForEach-Object {
    git mv "pheval_results\$($_.Name)" "pheval_results\configs\$($_.Name)"
}

# ── Move figures ───────────────────────────────────────────────────────────
git mv pr_curve.svg    figures/pr_curve.svg    2>$null
git mv rank_stats.svg  figures/rank_stats.svg  2>$null
git mv roc_curve.svg   figures/roc_curve.svg   2>$null

# ── Move docs ─────────────────────────────────────────────────────────────
git mv experiment_log.md         docs/experiment_log.md
git mv Methodology.md            docs/methodology_notes.md
git mv Method_correction_log.md  docs/method_correction_log.md

# ── Rename README ─────────────────────────────────────────────────────────
git mv New_README README.md 2>$null

# ── Remove old/deprecated scripts ─────────────────────────────────────────
git rm Batch_prompt.py                  2>$null
git rm main.py                          2>$null
git rm add_true_positive.py             2>$null
git rm build_ground_truth.py            2>$null
git rm convert_llm_json_to_pheval.py    2>$null
git rm convert_llm_disease_to_pheval.py 2>$null
git rm Convert_llm_to_pheval_correct.py 2>$null
git rm inspect_phenopackets.py          2>$null
git rm redact_phenopackets.py           2>$null
git rm test_rag_disease.py              2>$null
git rm benchmark_results_summary.csv    2>$null

# ── Remove old markdown notes ──────────────────────────────────────────────
git rm Agentic_results.md      2>$null
git rm early_results.md        2>$null
git rm Progress_report.md      2>$null
git rm Progress_2_report       2>$null
git rm Results_table.md        2>$null
git rm .Rhistory               2>$null

# ── Update .gitignore ──────────────────────────────────────────────────────
@"
# ChromaDB — rebuilt locally by run_rag.py
chroma_db/
chroma_db_v2/

# DuckDB — rebuilt by PhEval benchmarking
pheval_results/*.duckdb
pheval_results/configs/*.duckdb

# PhEval parquet output — large, reproducible
pheval_results/*/pheval_gene_results/
pheval_results/*/pheval_disease_results/

# LLM results — large JSON files, not tracked
llm_results*/

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# IDE
.idea/

# Large data files — stored on Apocrita HPC
hpo_resources/
exomiser_results/
phenopackets/

# HTML progress reports
*.html

# Logs
*.log
"@ | Out-File -FilePath ".gitignore" -Encoding utf8

git add .gitignore

# ── Status check ───────────────────────────────────────────────────────────
Write-Host "`nReorganisation complete. Current status:" -ForegroundColor Green
git status