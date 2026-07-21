"""
phenopacket_loader.py
=====================
Load HPO terms and metadata from a redacted phenopacket JSON file.

Usage (standalone test):
    python phenopacket_loader.py phenopackets/patient_001.json
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class PatientData:
    patient_id: str
    hpo_terms:  list[str]        # "HP:0001249 (Intellectual disability)"
    sex:        str = "Unknown"
    age:        str = "Unknown"
    excluded:   list[str] = field(default_factory=list)  # negated HPO terms


def load_phenopacket(path: Path) -> PatientData:
    """
    Parse a phenopacket JSON and return structured patient data.

    Args:
        path: Path to phenopacket JSON file

    Returns:
        PatientData with HPO terms extracted
    """
    with open(path) as f:
        data = json.load(f)

    patient_id = path.stem

    # Sex
    subject = data.get("subject", {})
    sex = subject.get("sex", "UNKNOWN").capitalize()

    # Age at last encounter
    time_info = subject.get("timeAtLastEncounter", {})
    age_info   = time_info.get("age", {})
    age = age_info.get("iso8601duration", "Unknown")

    # HPO terms — observed and excluded
    hpo_terms = []
    excluded  = []
    for feat in data.get("phenotypicFeatures", []):
        t       = feat.get("type", {})
        hpo_id  = t.get("id", "")
        label   = t.get("label", "")
        is_excl = feat.get("excluded", False)

        if not hpo_id:
            continue

        term_str = f"{hpo_id} ({label})" if label else hpo_id

        if is_excl:
            excluded.append(term_str)
        else:
            hpo_terms.append(term_str)

    return PatientData(
        patient_id = patient_id,
        hpo_terms  = hpo_terms,
        sex        = sex,
        age        = age,
        excluded   = excluded,
    )


def format_for_prompt(patient: PatientData) -> str:
    """
    Format patient data as a clinical description for the LLM prompt.
    """
    lines = [
        f"Patient: {patient.sex}, age {patient.age}",
        "",
        "Observed phenotypes:",
    ]
    for term in patient.hpo_terms:
        lines.append(f"  - {term}")

    if patient.excluded:
        lines.append("")
        lines.append("Excluded phenotypes (not present):")
        for term in patient.excluded:
            lines.append(f"  - {term}")

    return "\n".join(lines)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../phenopackets/patient_001.json")
    patient = load_phenopacket(path)
    print(f"Patient ID: {patient.patient_id}")
    print(f"Sex: {patient.sex}, Age: {patient.age}")
    print(f"HPO terms ({len(patient.hpo_terms)}):")
    for t in patient.hpo_terms:
        print(f"  {t}")
    if patient.excluded:
        print(f"Excluded ({len(patient.excluded)}):")
        for t in patient.excluded:
            print(f"  {t}")
    print()
    print("Formatted prompt section:")
    print(format_for_prompt(patient))
