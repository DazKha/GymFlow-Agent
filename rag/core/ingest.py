"""Ingest policy chunks into the dense production vector store."""

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
    ids = sorted(c["chunk_id"] for c in chunks)
    hashes = sorted(c["content_hash"] for c in chunks)
    key = "|".join(ids) + "|" + "|".join(hashes) + "|" + embed_model
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _load_chunks(jsonl_path: str) -> tuple[list[dict], list[str]]:
    chunks: list[dict] = []
    ids_seen: set[str] = set()
    errors: list[str] = []
    with open(jsonl_path, "r", encoding="utf-8") as file:
        for lineno, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"Line {lineno}: invalid JSON — {error}")
                continue
            chunk_id = chunk.get("chunk_id")
            if not chunk_id:
                errors.append(f"Line {lineno}: missing chunk_id")
                continue
            if chunk_id in ids_seen:
                errors.append(f"Line {lineno}: duplicate chunk_id '{chunk_id}'")
                continue
            ids_seen.add(chunk_id)
            required = ["document_id", "content", "embedding_text", "content_hash"]
            missing = [key for key in required if not chunk.get(key)]
            if missing:
                errors.append(f"Line {lineno}: missing fields {missing}")
                continue
            chunks.append(chunk)
    return chunks, errors


def dry_run(jsonl_path: str) -> dict:
    chunks, errors = _load_chunks(jsonl_path)
    doc_ids = {chunk["document_id"] for chunk in chunks}
    null_urls = [chunk["chunk_id"] for chunk in chunks if not chunk.get("source_url")]
    corpus_version = _compute_corpus_version(chunks, _EMBED_MODEL)
    print(f"Dry-run on {jsonl_path}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Documents: {len(doc_ids)}")
    print(f"  Duplicate IDs: {len(errors)}")
    print(f"  Missing source_url: {len(null_urls)}")
    print(f"  Corpus version: {corpus_version}")
    return {
        "chunks": len(chunks),
        "documents": len(doc_ids),
        "errors": len(errors),
        "null_urls": len(null_urls),
        "corpus_version": corpus_version,
    }


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
        return {"status": "failed", "errors": len(errors)}

    try:
        provider = HuggingFaceE5Provider(model_name=embed_model, device=device)
        store = PolicyVectorStore(
            embed_provider=provider,
            persist_dir=persist_dir,
            collection_name=collection_name,
        )
        if recreate:
            store.recreate_collection()
        result = store.ingest(chunks, batch_size=batch_size)
        result["removed_stale"] = store.sync_stale({c["chunk_id"] for c in chunks}) if sync else 0
        result["corpus_version"] = _compute_corpus_version(chunks, embed_model)
        result["status"] = "ok"
        manifest = {
            "collection_name": collection_name,
            "corpus_version": result["corpus_version"],
            "embedding_model": provider.model_name,
            "embedding_dimension": provider.dimension,
            "distance_metric": "cosine",
            "chunk_count": len(chunks),
            "document_count": len({c["document_id"] for c in chunks}),
            "source_jsonl": jsonl_path,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            **result,
        }
        manifest_path = Path(persist_dir) / "chroma_ingestion_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return result
    except Exception as error:  # noqa: BLE001
        return {"status": "blocked", "error": str(error)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest policy chunks into Chroma")
    parser.add_argument("--input", required=True, help="Path to policy_chunks.jsonl")
    parser.add_argument("--persist-dir", default=_PERSIST_DIR)
    parser.add_argument("--collection", default=_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=_BATCH_SIZE)
    parser.add_argument("--embedding-model", default=_EMBED_MODEL)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--recreate-collection", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        sys.exit(1 if dry_run(args.input)["errors"] else 0)
    if ingest(
        args.input,
        args.persist_dir,
        args.collection,
        args.embedding_model,
        args.batch_size,
        args.device,
        args.recreate_collection,
        args.sync,
    ).get("status") == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
