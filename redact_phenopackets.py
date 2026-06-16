import csv
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KEEP_FIELDS = {"phenotypicFeatures"}


def extract_disease_info(data: dict) -> tuple[str, str]:
    diseases = data.get("diseases", [])
    if not diseases:
        return "", ""

    term = diseases[0].get("term", {})
    disease_id = term.get("id", "")
    disease_label = term.get("label", "")
    return disease_id, disease_label


def redact_patient(data: dict, new_id: str) -> dict:
    redacted = {
        "id": new_id,
        "subject": {"id": new_id},
    }

    for field in KEEP_FIELDS:
        if field in data:
            redacted[field] = data[field]
        else:
            logger.warning("Missing field '%s' in %s", field, new_id)

    return redacted


def process_phenopackets(input_dir: Path, output_dir: Path, lookup_csv: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lookup_csv.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.json"))
    if not files:
        logger.warning("No JSON files found in %s", input_dir)
        return

    success, failed = 0, 0

    with lookup_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "new_file",
            "new_patient_id",
            "original_file",
            "true_disease_id",
            "true_disease_label",
        ])

        for idx, infile in enumerate(files, start=1):
            new_id = f"patient_{idx:03d}"
            new_file = f"{new_id}.json"
            outfile = output_dir / new_file

            try:
                data = json.loads(infile.read_text(encoding="utf-8"))
                disease_id, disease_label = extract_disease_info(data)
                redacted = redact_patient(data, new_id)

                outfile.write_text(json.dumps(redacted, indent=2), encoding="utf-8")

                writer.writerow([
                    new_file,
                    new_id,
                    infile.name,
                    disease_id,
                    disease_label,
                ])
                success += 1

            except json.JSONDecodeError as e:
                logger.error("Skipping %s — invalid JSON: %s", infile.name, e)
                failed += 1
            except OSError as e:
                logger.error("Skipping %s — file error: %s", infile.name, e)
                failed += 1

    logger.info("Done: %d redacted, %d failed → %s", success, failed, output_dir)
    logger.info("Lookup table written to %s", lookup_csv)


if __name__ == "__main__":
    process_phenopackets(
        input_dir=Path("/data/home/bt251044/p2p-work/synthetic_patients"),
        output_dir=Path("/data/home/bt251044/p2p-work/synthetic_patients_redacted"),
        lookup_csv=Path("/data/home/bt251044/p2p-work/synthetic_patients_lookup.csv"),
    )