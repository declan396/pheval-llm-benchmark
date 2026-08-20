import json
import csv
from pathlib import Path
import pickle

LOOKUP_CSV = Path("synthetic_patients_lookup.csv")
PHENO_WITH_GENES_DIR = Path("synthetic_patients_with_genes")

# Confirmed folder names from tonight's work
APPROACH_RESULT_DIRS = {
    "cot":                   Path("llm_results_cot"),                     # confirm this matches your actual folder
    "rag_v2":                Path("llm_results_rag_v2"),                  # confirm this matches your actual folder
    "rag_agentic":           Path("llm_results_rag_agentic"),             # confirm this matches your actual folder
    "exomiser_no_anchor":    Path("llm_results_exomiser_no_anchor"),
    "exomiser_anchored_5g":  Path("llm_results_exomiser_assisted_sonnet"),
    "exomiser_anchored_10g": Path("llm_results_exomiser_assisted_sonnet_10genes"),
    "rag_exomiser":          Path("llm_results_rag_exomiser"),
}


def load_lookup() -> dict:
    lookup = {}
    with open(LOOKUP_CSV) as f:
        for row in csv.DictReader(f):
            lookup[Path(row["new_file"]).stem] = Path(row["original_file"]).stem
    return lookup


def get_true_gene(patient_id: str, lookup: dict) -> str | None:
    orig = lookup.get(patient_id)
    if not orig:
        return None
    p = PHENO_WITH_GENES_DIR / f"{orig}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    for interp in data.get("interpretations", []):
        for gi in interp.get("diagnosis", {}).get("genomicInterpretations", []):
            g = gi.get("gene", {}).get("symbol", "")
            if g:
                return g.upper()
    return None


def get_top1_gene_from_llm_json(results_dir: Path, patient_id: str) -> str | None:
    f = results_dir / f"{patient_id}.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    if "error" in data:
        return None
    genes = data.get("top_genes", [])
    if not genes:
        return None
    return genes[0].get("gene_symbol", "").upper()


def main():
    lookup = load_lookup()
    all_correctness = {}

    for approach, results_dir in APPROACH_RESULT_DIRS.items():
        if not results_dir.exists():
            print(f"WARNING: {results_dir} does not exist, skipping {approach}")
            continue
        correctness = {}
        for patient_id in lookup:
            true_gene = get_true_gene(patient_id, lookup)
            if not true_gene:
                continue
            top1_gene = get_top1_gene_from_llm_json(results_dir, patient_id)
            if top1_gene is None:
                continue
            correctness[patient_id] = (top1_gene == true_gene)
        all_correctness[approach] = correctness
        n_correct = sum(correctness.values())
        pct = 100 * n_correct / len(correctness) if correctness else 0
        print(f"{approach}: {n_correct}/{len(correctness)} = {pct:.1f}%")

    with open("verified_correctness.pkl", "wb") as f:
        pickle.dump(all_correctness, f)
    print("\nSaved to verified_correctness.pkl")


if __name__ == "__main__":
    main()