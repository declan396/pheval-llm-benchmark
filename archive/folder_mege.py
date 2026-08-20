import pickle

with open("verified_correctness.pkl", "rb") as f:
    all_correctness = pickle.load(f)

with open("phenotype_only_correctness_fresh.pkl", "rb") as f:
    phenotype_only_correctness = pickle.load(f)

all_correctness["phenotype_only"] = phenotype_only_correctness

with open("verified_correctness.pkl", "wb") as f:
    pickle.dump(all_correctness, f)

print(f"Merged. Approaches now: {list(all_correctness.keys())}")
print(f"phenotype_only patient count: {len(phenotype_only_correctness)}")