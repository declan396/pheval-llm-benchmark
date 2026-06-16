"""
Build ground_truth_genes_all.csv by mapping:
  synthetic_patients_lookup.csv (patient_id → OMIM disease ID)
  genes_to_disease.txt          (gene_symbol → OMIM disease ID)

Output: ground_truth_genes_all.csv
  patient_id, true_disease_id, true_disease_label, ground_truth_gene
"""

import csv
from pathlib import Path
from collections import defaultdict

LOOKUP_FILE       = Path("synthetic_patients_lookup.csv")
GENES_TO_DISEASE  = Path("hpo_resources/genes_to_disease.txt")
OUTPUT_FILE       = Path("ground_truth_genes_all.csv")

# ── Step 1: Build disease_id → gene_symbol mapping from genes_to_disease.txt ──
# A disease may have multiple genes; we keep only MENDELIAN associations
disease_to_genes = defaultdict(list)

with open(GENES_TO_DISEASE) as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        assoc = row.get("association_type", "").strip()
        disease_id = row.get("disease_id", "").strip()
        gene_symbol = row.get("gene_symbol", "").strip()
        if assoc == "MENDELIAN" and disease_id and gene_symbol:
            disease_to_genes[disease_id].append(gene_symbol)

print(f"Loaded gene mappings for {len(disease_to_genes)} diseases")

# ── Step 2: Load patient lookup and map to genes ───────────────────────────────
results = []
no_gene = []

with open(LOOKUP_FILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        patient_id      = row["new_patient_id"].strip()
        disease_id      = row["true_disease_id"].strip()
        disease_label   = row["true_disease_label"].strip()

        genes = disease_to_genes.get(disease_id, [])

        if genes:
            # If multiple genes map to a disease, take the first (most common case)
            ground_truth_gene = genes[0]
            if len(genes) > 1:
                print(f"  ℹ {patient_id} ({disease_id}): multiple genes {genes} → using {ground_truth_gene}")
        else:
            ground_truth_gene = "?"
            no_gene.append(f"{patient_id} ({disease_id})")

        results.append({
            "patient_id":         patient_id,
            "true_disease_id":    disease_id,
            "true_disease_label": disease_label,
            "ground_truth_gene":  ground_truth_gene,
        })

# ── Step 3: Write output ───────────────────────────────────────────────────────
with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["patient_id", "true_disease_id", "true_disease_label", "ground_truth_gene"])
    writer.writeheader()
    writer.writerows(results)

mapped   = sum(1 for r in results if r["ground_truth_gene"] != "?")
unmapped = len(no_gene)

print(f"\nDone. Written to {OUTPUT_FILE}")
print(f"  ✓ Mapped   : {mapped}")
print(f"  ? Unmapped : {unmapped}")
if no_gene:
    print("\nUnmapped patients:")
    for p in no_gene:
        print(f"  {p}")