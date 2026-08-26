"""Chroma persistent vector store + E5 embedding provider."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings

_COLLECTION_NAME = os.getenv("CHROMA_POLICY_COLLECTION", "gymflow_policy_e5_v1")
_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/generated/chroma")
_EMBED_MODEL = os.getenv("POLICY_EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
_DEVICE = os.getenv("POLICY_EMBEDDING_DEVICE", "cpu")
_BATCH_SIZE = int(os.getenv("POLICY_EMBEDDING_BATCH_SIZE", "32"))


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    @property
    def model_name(self) -> str: ...
    @property
    def dimension(self) -> int: ...


class HuggingFaceE5Provider:
    """intfloat/multilingual-e5-base embedding provider with query/document prefixes."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name or _EMBED_MODEL
        self._device = device or _DEVICE
        self._model = SentenceTransformer(self._model_name, device=self._device)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return self._embed(prefixed)

    def embed_query(self, text: str) -> list[float]:
        prefixed = f"query: {text}"
        return self._embed([prefixed])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        result = self._model.encode(
            texts,
            batch_size=_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [vec.tolist() for vec in result]

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension


class FakeEmbeddingProvider:
    """Deterministic fake embedding provider for testing."""

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        results = []
        for i, t in enumerate(texts):
            h = hashlib.sha256(f"doc:{i}:{t}".encode()).digest()
            vec = [(b / 255.0) for b in h[:self._dimension]]
            while len(vec) < self._dimension:
                vec.append(0.0)
            results.append(vec)
        return results

    def embed_query(self, text: str) -> list[float]:
        import hashlib

        h = hashlib.sha256(f"query:{text}".encode()).digest()
        vec = [(b / 255.0) for b in h[:self._dimension]]
        while len(vec) < self._dimension:
            vec.append(0.0)
        return vec

    @property
    def model_name(self) -> str:
        return "fake-e5-test"

    @property
    def dimension(self) -> int:
        return self._dimension


def _serialize_meta(value: list | dict | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _none_to_str(value: str | None) -> str:
    return value if value is not None else ""


class PolicyVectorStore:
    """Persistent Chroma vector store for policy chunks."""

    def __init__(
        self,
        embed_provider: EmbeddingProvider | None = None,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self._persist_dir = persist_dir or _PERSIST_DIR
        self._collection_name = collection_name or _COLLECTION_NAME
        self._embed = embed_provider or HuggingFaceE5Provider()

        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def embed_provider(self) -> EmbeddingProvider:
        return self._embed

    def _get_or_create_collection(self):
        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def recreate_collection(self) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._client.create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(
        self,
        chunks: list[dict],
        batch_size: int = _BATCH_SIZE,
    ) -> dict:
        """Ingest chunks into Chroma. Returns counts: {inserted, updated, unchanged, errors}."""
        collection = self._get_or_create_collection()
        result = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}

        # Load the fields needed to distinguish a true no-op from an update.
        existing_records = {}
        try:
            existing = collection.get(include=["documents", "metadatas", "embeddings"])
            if existing and existing.get("ids"):
                existing_records = {
                    chunk_id: (document, metadata or {}, embedding)
                    for chunk_id, document, metadata, embedding in zip(
                        existing["ids"],
                        existing.get("documents") or [],
                        existing.get("metadatas") or [],
                        existing.get("embeddings") or [],
                    )
                }
        except Exception:
            pass

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids = []
            documents = []
            metadatas = []
            texts_to_embed = []

            for c in batch:
                chunk_id = c.get("chunk_id", "")
                if not chunk_id:
                    result["errors"] += 1
                    continue

                ids.append(chunk_id)
                documents.append(c.get("content", ""))
                metadatas.append({
                    "chunk_id": chunk_id,
                    "document_id": c.get("document_id", ""),
                    "document_title": c.get("document_title", ""),
                    "document_type": c.get("document_type", ""),
                    "source_url": _none_to_str(c.get("source_url")),
                    "effective_date": _none_to_str(c.get("effective_date")),
                    "section_path_text": _serialize_meta(c.get("section_path")),
                    "clause_ids_text": _serialize_meta(c.get("clause_ids")),
                    "chunk_index": int(c.get("chunk_index", 0)),
                    "content_hash": c.get("content_hash", ""),
                    "content_token_count": int(c.get("content_token_count", 0)),
                    "embedding_token_count": int(c.get("embedding_token_count", 0)),
                    "embedding_model": self._embed.model_name,
                    "corpus_version": "",
                })
                texts_to_embed.append(c.get("embedding_text", ""))

            embeddings = self._embed.embed_documents(texts_to_embed)

            inserts = []
            insert_indexes = []
            updates = []
            update_indexes = []
            for j, chunk_id in enumerate(ids):
                existing_record = existing_records.get(chunk_id)
                if existing_record is None:
                    inserts.append(chunk_id)
                    insert_indexes.append(j)
                elif (
                    existing_record[0] == documents[j]
                    and existing_record[1].get("content_hash", "") == metadatas[j]["content_hash"]
                    and existing_record[1].get("embedding_model", "") == metadatas[j]["embedding_model"]
                    and list(existing_record[2] or []) == list(embeddings[j])
                ):
                    result["unchanged"] += 1
                else:
                    updates.append(chunk_id)
                    update_indexes.append(j)

            try:
                if inserts:
                    result["inserted"] += len(inserts)
                    collection.add(
                        ids=inserts,
                        embeddings=[embeddings[j] for j in insert_indexes],
                        documents=[documents[j] for j in insert_indexes],
                        metadatas=[metadatas[j] for j in insert_indexes],
                    )
                if updates:
                    result["updated"] += len(updates)
                    collection.upsert(
                        ids=updates,
                        embeddings=[embeddings[j] for j in update_indexes],
                        documents=[documents[j] for j in update_indexes],
                        metadatas=[metadatas[j] for j in update_indexes],
                    )
            except Exception as e:
                result["errors"] += len(inserts) + len(updates)
                continue

        return result

    def sync_stale(self, valid_chunk_ids: set[str]) -> int:
        """Remove chunks that are no longer in the valid set. Returns count removed."""
        collection = self._get_or_create_collection()
        existing = collection.get()
        if not existing or not existing.get("ids"):
            return 0

        stale = [cid for cid in existing["ids"] if cid not in valid_chunk_ids]
        if stale:
            collection.delete(ids=stale)
        return len(stale)

    def count(self) -> int:
        collection = self._get_or_create_collection()
        return collection.count()

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Search the vector store. Returns list of {id, document, metadata, distance}."""
        if not query.strip():
            return []

        collection = self._get_or_create_collection()
        query_embedding = self._embed.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        out = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i] if results.get("distances") else None
                # Cosine distance in [0, 2]; convert to similarity in [0, 1]
                sim = 1.0 - (distance / 2.0) if distance is not None else None
                out.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": distance,
                    "similarity_score": sim,
                    "rank": i + 1,
                })
        return out

    def close(self) -> None:
        pass
