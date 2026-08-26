"""Pydantic models for the policy chunking pipeline."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class ChunkingConfig(BaseModel):
    tokenizer_name: str
    target_tokens: int = 450
    max_tokens: int = 600
    overlap_tokens: int = 50
    max_embedding_tokens: int = 512  # intfloat/multilingual-e5-base limit


class PolicyChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_type: str

    document_title: str
    section_path: list[str]
    section_title: str
    section_level: int

    clause_ids: list[str] = Field(default_factory=list)
    clause_fragment_index: int | None = None

    chunk_index: int = 0

    content: str
    embedding_text: str

    content_token_count: int = 0
    embedding_token_count: int = 0
    token_count: int = 0  # = content_token_count for backward compat
    overlap_token_count: int = 0

    source_url: str | None = None
    fetched_at: str = ""
    effective_date: str | None = None
    language: str = "vi-VN"
    publisher: str | None = None

    content_hash: str = ""

    def model_dump_json(self, **kwargs) -> str:
        ensure_ascii = kwargs.pop("ensure_ascii", False)
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        return json.dumps(data, ensure_ascii=ensure_ascii, **kwargs)


class ChunkReport(BaseModel):
    generated_at: str
    config: ChunkingConfig
    document_count: int
    chunk_count: int
    empty_chunk_count: int = 0
    heading_only_chunk_count: int = 0
    duplicate_chunk_id_count: int = 0
    duplicate_content_hash_count: int = 0
    oversized_chunk_count: int = 0
    unresolved_source_count: int = 0
    token_stats: dict = Field(default_factory=lambda: {"min": 0, "median": 0, "p95": 0, "max": 0})
    embedding_token_stats: dict = Field(default_factory=lambda: {"min": 0, "median": 0, "p95": 0, "max": 0})
    chunks_by_document: dict[str, int] = Field(default_factory=dict)
    chunks_by_document_type: dict[str, int] = Field(default_factory=dict)
    oversized_chunks: list[str] = Field(default_factory=list)
    unresolved_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def model_dump_json(self, **kwargs) -> str:
        ensure_ascii = kwargs.pop("ensure_ascii", False)
        kwargs.setdefault("indent", 2)
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        return json.dumps(data, ensure_ascii=ensure_ascii, **kwargs)
