"""
Phase 1: Seed Case Vectorization (ChromaDB Ingestion)

Reads all Seed Case JSON files from ./data/seed_cases/, builds searchable
document strings and metadata, then upserts them into a local ChromaDB
collection named 'seed_cases'.

Usage:
    python ingest_seeds.py
"""

import chromadb
import json
import os


SEED_CASES_DIR = "./data/seed_cases"
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "seed_cases"


def build_document_string(data: dict) -> str:
    """
    Concatenates the narrative/logical elements into a single searchable string
    for semantic embedding. Targets: clinical_barriers, physical_barriers,
    reasoning_trace_triples, and unscripted_chaos_signals.
    """
    parts = []

    # Clinical barriers
    clinical_barriers = data.get("clinical_logic", {}).get("clinical_barriers", [])
    if isinstance(clinical_barriers, list):
        parts.append("Clinical Barriers: " + "; ".join(clinical_barriers))
    elif isinstance(clinical_barriers, str):
        parts.append("Clinical Barriers: " + clinical_barriers)

    # Physical barriers
    physical_barriers = data.get("environmental_logic", {}).get("physical_barriers", "")
    if physical_barriers:
        parts.append("Physical Barriers: " + physical_barriers)

    # Reasoning trace triples (summarized as situation + intent)
    triples = data.get("reasoning_trace_triples", [])
    triple_summaries = []
    for triple in triples:
        situation = triple.get("situation", "")
        intent = triple.get("intent", "")
        if situation or intent:
            triple_summaries.append(f"{situation} [{intent}]")
    if triple_summaries:
        parts.append("Reasoning: " + "; ".join(triple_summaries))

    # Unscripted chaos signals
    chaos_signals = data.get("unscripted_chaos_signals", [])
    if isinstance(chaos_signals, list):
        parts.append("Chaos Signals: " + "; ".join(chaos_signals))
    elif isinstance(chaos_signals, str):
        parts.append("Chaos Signals: " + chaos_signals)

    return " | ".join(parts)


def build_metadata_dict(data: dict, raw_json: str) -> dict:
    """
    Builds the ChromaDB metadata dict. ChromaDB only accepts str, int, or float.
    Includes raw_json payload so the LLM can receive the full case in Phase 2.
    """
    header = data.get("case_header", {})
    clinical = data.get("clinical_logic", {})
    env = data.get("environmental_logic", {})

    # complexity_score → int
    try:
        complexity_score = int(header.get("complexity_score", 0))
    except (ValueError, TypeError):
        complexity_score = 0

    # outcome → str
    outcome = str(header.get("outcome", "Unknown"))

    # has_skilled_need → "Yes" or "No"
    skilled_need = clinical.get("skilled_need_verified", "No")
    has_skilled_need = "Yes" if str(skilled_need).strip().lower() in ("yes", "true", "1") else "No"

    # primary_friction: first element of modification_type (list or string)
    modification = env.get("modification_type", "")
    if isinstance(modification, list):
        primary_friction = modification[0] if modification else "Unknown"
    else:
        primary_friction = str(modification) if modification else "Unknown"

    return {
        "complexity_score": complexity_score,
        "outcome": outcome,
        "has_skilled_need": has_skilled_need,
        "primary_friction": primary_friction,
        "raw_json": raw_json,
    }


def ingest_seed_cases():
    # 1. Initialize ChromaDB persistent client
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # 2. Get or create collection (Chroma auto-generates embeddings)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    seed_files = [
        f for f in os.listdir(SEED_CASES_DIR)
        if f.endswith(".json")
    ]

    if not seed_files:
        print(f"No JSON files found in {SEED_CASES_DIR}. Add seed case files and re-run.")
        return

    ids = []
    documents = []
    metadatas = []

    for filename in seed_files:
        filepath = os.path.join(SEED_CASES_DIR, filename)
        print(f"  Loading: {filename}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # a. Extract case_id
        case_id = data.get("case_header", {}).get("case_id", filename.replace(".json", ""))

        # b. Build searchable document string
        document_string = build_document_string(data)

        # c. Serialize full JSON for the payload
        raw_json = json.dumps(data)

        # d. Build metadata
        metadata = build_metadata_dict(data, raw_json)

        ids.append(case_id)
        documents.append(document_string)
        metadatas.append(metadata)

    # 4. Upsert batch into ChromaDB
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    print(f"\nIngestion complete: {len(ids)} case(s) upserted into '{COLLECTION_NAME}' collection.")
    print(f"ChromaDB stored at: {CHROMA_DB_PATH}")


if __name__ == "__main__":
    ingest_seed_cases()
