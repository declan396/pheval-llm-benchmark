#!/bin/bash
#SBATCH --job-name=exomiser_200
#SBATCH --output=/data/home/bt251044/p2p-work/logs/exomiser_%A_%a.out
#SBATCH --error=/data/home/bt251044/p2p-work/logs/exomiser_%A_%a.err
#SBATCH --array=1-200
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2

# Load Java
module load openjdk/21.0.0_35-gcc-12.2.0

# Paths
EXOMISER_JAR=/data/home/bt251044/pheval-run/configurations/exomiser-15.0.0/2512/exomiser-cli-15.0.0/exomiser-cli-15.0.0.jar
APP_PROPERTIES=/data/home/bt251044/pheval-run/configurations/exomiser-15.0.0/2512/exomiser-cli-15.0.0/application.properties
DATA_DIR=/data/home/bt251044/pheval-run/configurations/exomiser-15.0.0/2512
PHENOPACKET_DIR=/data/home/bt251044/p2p-work/synthetic_corpus/phenopackets
OUTPUT_DIR=/data/home/bt251044/p2p-work/exomiser_results

mkdir -p $OUTPUT_DIR

# Get patient ID from array index
PATIENT_ID=$(printf "patient_%03d" $SLURM_ARRAY_TASK_ID)
PHENOPACKET=$PHENOPACKET_DIR/${PATIENT_ID}.json
OUTPUT_FILE=$OUTPUT_DIR/${PATIENT_ID}.parquet

# Skip if already done
if [ -f "$OUTPUT_FILE" ]; then
    echo "Skipping $PATIENT_ID - already done"
    exit 0
fi

echo "Running Exomiser for $PATIENT_ID"

java -Xmx6g \
  -Dspring.config.location=$APP_PROPERTIES \
  -Dexomiser.data-directory=$DATA_DIR \
  -jar $EXOMISER_JAR \
  analyse \
  --sample $PHENOPACKET \
  --preset phenotype_only \
  --output-directory $OUTPUT_DIR \
  --output-filename $PATIENT_ID \
  --output-format PARQUET

echo "Done: $PATIENT_ID"