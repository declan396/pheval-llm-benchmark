python - <<'PY'
import json
from pathlib import Path
import polars as pl

phenopacket_dir = Path("/data/home/bt251044/p2p-work/synthetic_patients_redacted")
results_dir = Path("/data/home/bt251044/p2p-work/synthetic_results/raw_results")
out_dir = Path("/data/home/bt251044/p2p-work/llm_prompts_021_030")
out_dir.mkdir(exist_ok=True)

for i in range(31, 51):
    patient_id = f"patient_{i:03d}"
    phenofile = phenopacket_dir / f"{patient_id}.json"
    exomiser_file = results_dir / f"{patient_id}-exomiser.parquet"

    if not phenofile.exists() or not exomiser_file.exists():
        print(f"Skipping {patient_id}")
        continue

    data = json.loads(phenofile.read_text())
    phenotypes = [
        f"{f['type']['id']} {f['type']['label']}"
        for f in data.get("phenotypicFeatures", [])
    ]

    df = pl.read_parquet(exomiser_file)
    top = df.sort("geneCombinedScore", descending=True).select(
        ["geneSymbol", "geneCombinedScore"]
    ).head(10).to_dicts()

    genes = [
        f"{j+1}. {g['geneSymbol']} ({g['geneCombinedScore']:.3f})"
        for j, g in enumerate(top)
    ]

    prompt = (
        f"Case: {patient_id}\n\n"
        "Patient phenotypes:\n" + "\n".join(f"- {p}" for p in phenotypes) +
        "\n\nTop genes:\n" + "\n".join(genes) +
        "\n\nTask: Diagnose and prioritise genes."
    )

    (out_dir / f"{patient_id}.txt").write_text(prompt)

print("Done")
PY