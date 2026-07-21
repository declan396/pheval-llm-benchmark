"""
rag_retriever.py
================
HPOA vector store builder and retriever.

Builds a ChromaDB index from HPOA using HPO term LABELS (not IDs) for
semantic embedding. Reuses existing index if already built.

Usage (standalone test):
    python rag_retriever.py HP:0001249 HP:0001250 HP:0000750
"""

import sys
import json
import csv
from pathlib import Path
from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer

# Resolve paths relative to project root (parent of rag_agentic/)
_HERE          = Path(__file__).parent
BASE_DIR       = _HERE.parent

HPOA_PATH       = BASE_DIR / "hpo_resources" / "phenotype.hpoa"
CHROMA_DIR      = BASE_DIR / "chroma_db_v2"
PHENOPACKET_DIR_DEFAULT = BASE_DIR / "phenopackets"
GENES_FILE      = BASE_DIR / "hpo_resources" / "genes_to_disease.txt"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "hpoa_diseases_v2"


@dataclass
class RetrievedDisease:
    rank:         int
    disease_id:   str
    disease_name: str
    similarity:   float
    genes:        list[str]


def parse_hpo_labels(phenopacket_dir: Path | None = None) -> dict[str, str]:
    if phenopacket_dir is None:
        phenopacket_dir = PHENOPACKET_DIR_DEFAULT
    """
    Build HPO ID → label mapping from local phenopackets.
    Falls back gracefully if hp.obo is not present.
    """
    # Try hp.obo first
    obo_path = HPOA_PATH.parent / "hp.obo"
    id_to_label: dict[str, str] = {}

    if obo_path.exists():
        print("Loading HPO labels from hp.obo...")
        current_id = None
        with open(obo_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("id: HP:"):
                    current_id = line.replace("id: ", "").strip()
                elif line.startswith("name: ") and current_id:
                    id_to_label[current_id] = line.replace("name: ", "").strip()
                    current_id = None
        print(f"Loaded {len(id_to_label)} HPO labels from hp.obo")
        return id_to_label

    # Fall back to phenopackets
    print("hp.obo not found — extracting labels from phenopackets...")
    for ppath in sorted(phenopacket_dir.glob("patient_*.json")):
        data = json.loads(ppath.read_text())
        for feat in data.get("phenotypicFeatures", []):
            t = feat.get("type", {})
            hid   = t.get("id", "")
            label = t.get("label", "")
            if hid and label:
                id_to_label[hid] = label
    print(f"Extracted {len(id_to_label)} HPO labels from phenopackets")
    return id_to_label


def parse_hpoa(hpoa_path: Path) -> dict:
    """Parse HPOA file into disease_id -> {name, hpo_ids} mapping."""
    diseases: dict = {}
    with open(hpoa_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("database_id"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            disease_id   = parts[0].strip()
            disease_name = parts[1].strip()
            qualifier    = parts[2].strip()
            hpo_id       = parts[3].strip()
            if qualifier == "NOT" or not hpo_id.startswith("HP:"):
                continue
            if disease_id not in diseases:
                diseases[disease_id] = {"name": disease_name, "hpo_ids": []}
            diseases[disease_id]["hpo_ids"].append(hpo_id)
    print(f"Parsed {len(diseases)} diseases from HPOA")
    return diseases


def build_gene_lookup(genes_file: Path | None = None) -> dict[str, list[str]]:
    if genes_file is None:
        genes_file = GENES_FILE
    """
    Build disease_id -> [gene_symbols] mapping.
    Format: ncbi_gene_id  gene_symbol  association_type  disease_id  source
    """
    lookup: dict[str, list[str]] = {}
    if not genes_file.exists():
        print(f"Warning: {genes_file} not found")
        return lookup
    with open(genes_file) as f:
        for line in f:
            if line.startswith("#") or line.startswith("ncbi_gene_id"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            gene_symbol = parts[1].strip()
            disease_id  = parts[3].strip()
            if not gene_symbol or not disease_id:
                continue
            if disease_id not in lookup:
                lookup[disease_id] = []
            if gene_symbol not in lookup[disease_id]:
                lookup[disease_id].append(gene_symbol)
    print(f"Gene lookup: {len(lookup)} disease-gene associations")
    return lookup


def build_or_load_index(
    hpoa_path:   Path,
    chroma_dir:  Path,
    id_to_label: dict[str, str],
) -> chromadb.Collection:
    """
    Build or load ChromaDB index. Uses HPO labels for semantic embedding.
    Index is built once and reused on subsequent runs.
    """
    chroma_client = chromadb.PersistentClient(path=str(chroma_dir))

    try:
        collection = chroma_client.get_collection(COLLECTION_NAME)
        if collection.count() > 0:
            print(f"Loaded existing ChromaDB index ({collection.count()} diseases)")
            return collection
    except Exception:
        pass

    print("Building ChromaDB index with HPO labels — ~5 minutes...")
    diseases = parse_hpoa(hpoa_path)
    model    = SentenceTransformer(EMBEDDING_MODEL)

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 500
    ids, documents, metadatas = [], [], []

    for disease_id, data in diseases.items():
        labels = [id_to_label.get(hid, hid) for hid in data["hpo_ids"]]
        doc    = f"{data['name']}: {', '.join(labels)}"
        ids.append(disease_id)
        documents.append(doc)
        metadatas.append({
            "disease_id":   disease_id,
            "disease_name": data["name"],
            "hpo_ids":      ",".join(data["hpo_ids"][:20]),
        })

        if len(ids) >= batch_size:
            embeddings = model.encode(documents, show_progress_bar=False).tolist()
            collection.add(ids=ids, documents=documents,
                           metadatas=metadatas, embeddings=embeddings)
            print(f"  Indexed {collection.count()} diseases...")
            ids, documents, metadatas = [], [], []

    if ids:
        embeddings = model.encode(documents, show_progress_bar=False).tolist()
        collection.add(ids=ids, documents=documents,
                       metadatas=metadatas, embeddings=embeddings)

    print(f"Index complete: {collection.count()} diseases")
    return collection


def retrieve(
    hpo_labels:  list[str],
    collection:  chromadb.Collection,
    embed_model: SentenceTransformer,
    gene_lookup: dict[str, list[str]],
    top_n:       int = 10,
) -> list[RetrievedDisease]:
    """
    Retrieve top-N diseases most similar to patient HPO labels.

    Args:
        hpo_labels:  list of HPO term labels e.g. ['Intellectual disability']
        collection:  ChromaDB collection
        embed_model: SentenceTransformer model
        gene_lookup: disease_id -> gene_symbols mapping
        top_n:       number of diseases to retrieve

    Returns:
        list of RetrievedDisease sorted by similarity descending
    """
    query     = ", ".join(hpo_labels)
    embedding = embed_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=top_n,
        include=["metadatas", "distances"],
    )

    retrieved = []
    for i, (meta, dist) in enumerate(zip(
        results["metadatas"][0],
        results["distances"][0],
    )):
        disease_id = meta["disease_id"]
        retrieved.append(RetrievedDisease(
            rank         = i + 1,
            disease_id   = disease_id,
            disease_name = meta["disease_name"],
            similarity   = round(1 - dist, 3),
            genes        = gene_lookup.get(disease_id, [])[:5],
        ))

    return retrieved


def format_for_prompt(diseases: list[RetrievedDisease]) -> str:
    """Format retrieved diseases for inclusion in Claude prompt."""
    lines = []
    for d in diseases:
        genes = ", ".join(d.genes) if d.genes else "unknown"
        lines.append(
            f"{d.rank}. {d.disease_name} ({d.disease_id}) "
            f"[similarity: {d.similarity}] genes: {genes}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick retrieval test
    hpo_ids = sys.argv[1:] if len(sys.argv) > 1 else ["HP:0001249", "HP:0001250"]
    print(f"Testing retrieval for: {hpo_ids}")

    id_to_label = parse_hpo_labels()
    labels      = [id_to_label.get(h, h) for h in hpo_ids]
    gene_lookup = build_gene_lookup()
    collection  = build_or_load_index(HPOA_PATH, CHROMA_DIR, id_to_label)
    model       = SentenceTransformer(EMBEDDING_MODEL)

    results = retrieve(labels, collection, model, gene_lookup)
    for r in results:
        print(f"  {r.rank}. {r.disease_name} ({r.disease_id}) sim={r.similarity} genes={r.genes}")
