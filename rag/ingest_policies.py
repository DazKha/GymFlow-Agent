"""Chroma ingestion CLI for policy chunks.

Usage:
    python -m rag.ingest_policies \\
      --input data/generated/policy_chunks.jsonl \\
      --collection gymflow_policy_e5_v1

    python -m rag.ingest_policies --dry-run \\
      --input data/generated/policy_chunks.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/generated/chroma")
_COLLECTION = os.getenv("CHROMA_POLICY_COLLECTION", "gymflow_policy_e5_v1")
_EMBED_MODEL = os.getenv("POLICY_EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
_BATCH_SIZE = int(os.getenv("POLICY_EMBEDDING_BATCH_SIZE", "32"))


def _compute_corpus_version(chunks: list[dict], embed_model: str) -> str:
    """Deterministic corpus version from chunk IDs + content hashes + model."""
    ids = sorted(c["chunk_id"] for c in chunks)
    hashes = sorted(c["content_hash"] for c in chunks)
    key = "|".join(ids) + "|" + "|".join(hashes) + "|" + embed_model
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _load_chunks(jsonl_path: str) -> list[dict]:
    chunks = []
    ids_seen = set()
    errors = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {lineno}: invalid JSON — {e}")
                continue
            cid = c.get("chunk_id")
            if not cid:
                errors.append(f"Line {lineno}: missing chunk_id")
                continue
            if cid in ids_seen:
                errors.append(f"Line {lineno}: duplicate chunk_id '{cid}'")
                continue
            ids_seen.add(cid)
            required = ["document_id", "content", "embedding_text", "content_hash"]
            missing = [k for k in required if not c.get(k)]
            if missing:
                errors.append(f"Line {lineno}: missing fields {missing}")
                continue
            chunks.append(c)
    return chunks, errors


def dry_run(jsonl_path: str) -> dict:
    chunks, errors = _load_chunks(jsonl_path)
    doc_ids = set(c["document_id"] for c in chunks)
    null_urls = [c["chunk_id"] for c in chunks if not c.get("source_url")]
    corpus_version = _compute_corpus_version(chunks, _EMBED_MODEL)

    print(f"Dry-run on {jsonl_path}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Documents: {len(doc_ids)}")
    print(f"  Duplicate IDs: {len(errors)}")
    print(f"  Missing source_url: {len(null_urls)}")
    print(f"  Corpus version: {corpus_version}")
    if errors:
        print("  Validation errors:")
        for e in errors[:10]:
            print(f"    {e}")
    if null_urls:
        print("  Chunks with null source_url:")
        for cid in null_urls[:5]:
            print(f"    {cid}")
    return {"chunks": len(chunks), "documents": len(doc_ids), "errors": len(errors),
            "null_urls": len(null_urls), "corpus_version": corpus_version}


def ingest(
    jsonl_path: str,
    persist_dir: str = _PERSIST_DIR,
    collection_name: str = _COLLECTION,
    embed_model: str = _EMBED_MODEL,
    batch_size: int = _BATCH_SIZE,
    device: str = "cpu",
    recreate: bool = False,
    sync: bool = False,
) -> dict:
    from rag.core.vector_store import HuggingFaceE5Provider, PolicyVectorStore

    chunks, errors = _load_chunks(jsonl_path)
    if errors:
        print(f"Validation errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return {"status": "failed", "errors": len(errors)}

    print(f"Embedding model: {embed_model}")
    print(f"Loading model...")

    try:
        provider = HuggingFaceE5Provider(model_name=embed_model, device=device)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("You may need to download the model first or check network connectivity.")
        return {"status": "blocked", "error": str(e)}

    print(f"Model loaded: {provider.model_name} (dim={provider.dimension})")

    store = PolicyVectorStore(
        embed_provider=provider,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    if recreate:
        print(f"Recreating collection '{collection_name}'...")
        store.recreate_collection()

    print(f"Ingesting {len(chunks)} chunks into '{collection_name}'...")
    result = store.ingest(chunks, batch_size=batch_size)

    print(f"  Inserted: {result['inserted']}")
    print(f"  Updated: {result['updated']}")
    print(f"  Unchanged: {result['unchanged']}")
    print(f"  Errors: {result['errors']}")

    if sync:
        valid_ids = {c["chunk_id"] for c in chunks}
        stale = store.sync_stale(valid_ids)
        result["removed_stale"] = stale
        print(f"  Removed stale: {stale}")
    else:
        result["removed_stale"] = 0

    corpus_version = _compute_corpus_version(chunks, embed_model)

    # Write ingestion manifest
    manifest = {
        "collection_name": collection_name,
        "corpus_version": corpus_version,
        "embedding_model": provider.model_name,
        "embedding_dimension": provider.dimension,
        "distance_metric": "cosine",
        "chunk_count": len(chunks),
        "document_count": len(set(c["document_id"] for c in chunks)),
        "source_jsonl": jsonl_path,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }

    manifest_path = Path(persist_dir) / "chroma_ingestion_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nCorpus version: {corpus_version}")
    print(f"Manifest: {manifest_path}")
    print(f"Collection count: {store.count()}")

    result["corpus_version"] = corpus_version
    result["status"] = "ok"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest policy chunks into Chroma")
    parser.add_argument("--input", required=True, help="Path to policy_chunks.jsonl")
    parser.add_argument("--persist-dir", default=_PERSIST_DIR, help="Chroma persistence directory")
    parser.add_argument("--collection", default=_COLLECTION, help="Chroma collection name")
    parser.add_argument("--batch-size", type=int, default=_BATCH_SIZE, help="Embedding batch size")
    parser.add_argument("--embedding-model", default=_EMBED_MODEL, help="Embedding model name")
    parser.add_argument("--device", default="cpu", help="Device: cpu, cuda, mps")
    parser.add_argument("--sync", action="store_true", help="Remove stale chunks not in input")
    parser.add_argument("--recreate-collection", action="store_true", help="Drop and recreate collection")
    parser.add_argument("--dry-run", action="store_true", help="Validate JSONL without ingesting")

    args = parser.parse_args()

    if args.dry_run:
        result = dry_run(args.input)
        sys.exit(1 if result["errors"] > 0 else 0)

    result = ingest(
        jsonl_path=args.input,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        embed_model=args.embedding_model,
        batch_size=args.batch_size,
        device=args.device,
        recreate=args.recreate_collection,
        sync=args.sync,
    )

    if result.get("status") == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
