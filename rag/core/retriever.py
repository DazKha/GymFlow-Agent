"""Policy retriever with citation support."""

from __future__ import annotations

import json
import os

from pydantic import BaseModel

_TOP_K = int(os.getenv("POLICY_RETRIEVAL_TOP_K", "5"))


class PolicySearchResult(BaseModel):
    chunk_id: str
    content: str
    document_id: str
    document_title: str
    section_path: list[str]
    clause_ids: list[str]
    source_url: str
    effective_date: str = ""
    distance: float | None = None
    similarity_score: float | None = None
    rank: int = 0
    dense_score: float | None = None
    reranker_score: float | None = None
    fused_score: float | None = None
    initial_rank: int | None = None
    final_rank: int | None = None
    query_variant: str = ""

    def citation_label(self) -> str:
        parts = [f"California Fitness & Yoga — {self.document_title}"]
        if self.section_path:
            parts.append(f"Section: {' > '.join(self.section_path)}")
        if self.source_url:
            parts.append(f"Source: {self.source_url}")
        if self.clause_ids:
            parts.append(f"Clause: {', '.join(self.clause_ids)}")
        return "\n".join(parts)

    def model_dump_json(self, **kwargs) -> str:
        kwargs.setdefault("ensure_ascii", False)
        return super().model_dump_json(**kwargs)


def _parse_section_path(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [raw]


def _parse_clause_ids(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [raw]


class PolicyRetriever:
    def __init__(self, vector_store=None) -> None:
        if vector_store is None:
            from rag.core.vector_store import PolicyVectorStore

            vector_store = PolicyVectorStore()
        self._store = vector_store

    def _search_dense(
        self,
        query: str,
        top_k: int = _TOP_K,
        document_ids: list[str] | None = None,
    ) -> list[PolicySearchResult]:
        if not query.strip():
            raise ValueError("Query must be non-empty")
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, got {top_k}")

        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}

        raw = self._store.search(query=query, top_k=top_k, where=where)
        results = []
        for r in raw:
            meta = r.get("metadata", {})
            results.append(PolicySearchResult(
                chunk_id=r.get("id", ""),
                content=r.get("document", ""),
                document_id=meta.get("document_id", ""),
                document_title=meta.get("document_title", ""),
                section_path=_parse_section_path(meta.get("section_path_text", "")),
                clause_ids=_parse_clause_ids(meta.get("clause_ids_text", "")),
                source_url=meta.get("source_url", ""),
                effective_date=meta.get("effective_date", ""),
                distance=r.get("distance"),
                similarity_score=r.get("similarity_score"),
                rank=r.get("rank", 0),
                dense_score=r.get("similarity_score"),
                initial_rank=r.get("rank", 0),
                final_rank=r.get("rank", 0),
            ))
        return results

    def search(
        self,
        query: str,
        top_k: int = _TOP_K,
        document_ids: list[str] | None = None,
    ) -> list[PolicySearchResult]:
        return self._search_dense(query, top_k, document_ids)

    def search_to_ragas_format(
        self,
        query: str,
        top_k: int = _TOP_K,
    ) -> dict:
        results = self.search(query, top_k)
        return {
            "user_input": query,
            "retrieved_contexts": [r.content for r in results],
            "retrieved_chunk_ids": [r.chunk_id for r in results],
            "retrieved_sources": [
                {
                    "document_id": r.document_id,
                    "section_path": r.section_path,
                    "source_url": r.source_url,
                }
                for r in results
            ],
        }


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Query policy vector store")
    parser.add_argument("--query", required=True, help="Search query (Vietnamese)")
    parser.add_argument("--top-k", type=int, default=_TOP_K, help="Number of results")
    args = parser.parse_args()

    if not args.query.strip():
        print("Error: empty query", file=sys.stderr)
        sys.exit(1)

    retriever = PolicyRetriever()
    results = retriever.search(args.query, top_k=args.top_k)

    print(f"Query: {args.query}\n")
    for r in results:
        print(f"--- Rank {r.rank} (similarity: {r.similarity_score:.4f}) ---")
        print(r.citation_label())
        print(f"\n{r.content[:200]}...\n")


if __name__ == "__main__":
    main()
