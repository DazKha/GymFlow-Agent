"""Section-aware chunking pipeline for California Fitness & Yoga policy documents.

Usage:
    python -m rag.core.chunking \\
      --input-dir data \\
      --output data/generated/policy_chunks.jsonl \\
      --report data/generated/policy_chunk_report.json \\
      --target-tokens 450 \\
      --max-tokens 600 \\
      --overlap-tokens 50
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml

from rag.core.models import ChunkReport, ChunkingConfig, PolicyChunk


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...
    @property
    def name(self) -> str: ...


class TiktokenCounter:
    """Token counter using tiktoken (fallback when intfloat/multilingual-e5-base
    tokenizer from Hugging Face transformers is not available in the environment).

    Uses `o200k_base` encoding which is a reasonable proxy for multilingual
    subword tokenization.
    """

    def __init__(self, encoding: str = "o200k_base") -> None:
        import tiktoken

        self._enc = tiktoken.get_encoding(encoding)
        self._encoding_name = f"tiktoken:{encoding}"

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))

    def encode(self, text: str) -> list[int]:
        return self._enc.encode(text)

    def decode(self, tokens: list[int]) -> str:
        return self._enc.decode(tokens)

    @property
    def name(self) -> str:
        return self._encoding_name


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _normalize_for_comparison(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _slugify(text: str, max_len: int = 60) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text


def _short_hash(text: str, length: int = 6) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------

_MISSING_KEYS = {"document_id", "document_type", "fetched_at"}


def _make_embedding_prefix(doc_title: str, section_path: list[str]) -> str:
    return f"Tài liệu: {doc_title}\nSection: {' > '.join(section_path)}\n\n"


def parse_document(content: str, filename: str = "") -> dict[str, Any]:
    """Parse YAML front matter and Markdown heading hierarchy."""
    warnings: list[str] = []

    if not content.startswith("---"):
        raise ValueError(f"Missing YAML front matter in {filename}")

    end = content.index("---", 3)
    fm_text = content[3:end].strip()
    body = content[end + 3:]

    try:
        fm_raw = yaml.load(fm_text, Loader=yaml.BaseLoader) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML front matter in {filename}: {e}") from e

    fm: dict[str, Any] = {}
    for k, v in fm_raw.items():
        if isinstance(v, str) and v.lower() == "null":
            fm[k] = None
        else:
            fm[k] = v

    missing = _MISSING_KEYS - set(fm.keys())
    if missing:
        warnings.append(f"Missing front matter keys: {', '.join(sorted(missing))}")

    if fm.get("source_url") is None:
        warnings.append(f"source_url is null in {filename}")

    doc_id = fm.get("document_id", "")
    if not doc_id:
        raise ValueError(f"Missing document_id in {filename}")

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in heading_pattern.finditer(body)]

    h1 = ""
    h1_headings = [h for h in headings if h[1] == 1]
    if len(h1_headings) == 0:
        warnings.append(f"No H1 heading found in {filename}")
    elif len(h1_headings) > 1:
        warnings.append(f"Multiple H1 headings found in {filename}")
    else:
        h1 = h1_headings[0][2]

    section_boundaries: list[tuple[int, dict[str, Any]]] = []
    for pos, level, title in headings:
        section_boundaries.append((pos, {"title": title, "level": level}))

    sections: list[dict[str, Any]] = []
    for i, (start_pos, sec) in enumerate(section_boundaries):
        end_pos = section_boundaries[i + 1][0] if i + 1 < len(section_boundaries) else len(body)
        raw_content = body[start_pos:end_pos]
        raw_body = raw_content.split("\n", 1)
        if len(raw_body) > 1:
            raw_body = raw_body[1]
        else:
            raw_body = ""
        sec["raw_body"] = raw_body.strip()
        sections.append(sec)

    path_stack: list[str] = []
    for sec in sections:
        level = sec["level"]
        while len(path_stack) >= level:
            path_stack.pop()
        path_stack.append(sec["title"])
        sec["path"] = list(path_stack)

    clause_pattern = re.compile(r"\b(\d+\.\d+|[IVXLCDM]+\.)\s")
    for sec in sections:
        clauses = clause_pattern.findall(sec.get("raw_body", ""))
        sec["clause_ids"] = sorted(set(clauses))

    return {
        "filename": filename,
        "document_id": fm.get("document_id", ""),
        "document_type": fm.get("document_type", ""),
        "title": fm.get("title", h1),
        "source_url": fm.get("source_url"),
        "fetched_at": fm.get("fetched_at", ""),
        "effective_date": fm.get("effective_date"),
        "language": fm.get("language", "vi-VN"),
        "publisher": fm.get("publisher"),
        "h1": h1,
        "body": body.strip(),
        "sections": sections,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

class ChunkingPipeline:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig(
            tokenizer_name="tiktoken:o200k_base",
            target_tokens=450,
            max_tokens=600,
            overlap_tokens=50,
        )
        self._counter = self._create_counter()
        self._prefix_budget = 0

    @staticmethod
    def _create_counter() -> TokenCounter:
        try:
            from transformers import AutoTokenizer

            tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-base")

            class E5Counter:
                def __init__(self, tokenizer):
                    self._tok = tokenizer

                def count(self, text: str) -> int:
                    return len(self._tok.encode(text))

                def encode(self, text: str) -> list[int]:
                    return self._tok.encode(text)

                def decode(self, tokens: list[int]) -> str:
                    return self._tok.decode(tokens, skip_special_tokens=True)

                @property
                def name(self) -> str:
                    return "intfloat/multilingual-e5-base"

            return E5Counter(tok)
        except Exception:
            return TiktokenCounter(encoding="o200k_base")

    def _make_prefix(self, doc_title: str, section_path: list[str]) -> str:
        return _make_embedding_prefix(doc_title, section_path)

    def _prefix_token_count(self, doc_title: str, section_path: list[str]) -> int:
        return self._counter.count(self._make_prefix(doc_title, section_path))

    def _make_chunk_id(self, doc_id: str, sec_title: str, content_for_hash: str) -> str:
        slug = _slugify(sec_title)
        h = _short_hash(content_for_hash, 6)
        if slug:
            return f"{doc_id}__{slug}__{h}"
        return f"{doc_id}__section__{h}"

    def _compute_content_hash(self, doc_id: str, section_path: list[str],
                              clause_ids: list[str], content: str) -> str:
        return hashlib.sha256(
            json.dumps(
                {"document_id": doc_id, "section_path": section_path,
                 "clause_ids": clause_ids, "content": content},
                ensure_ascii=False, sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    def _create_chunk(
        self,
        doc: dict[str, Any],
        section_path: list[str],
        section_title: str,
        section_level: int,
        clause_ids: list[str],
        content: str,
        chunk_index: int,
        clause_fragment_index: int | None = None,
        overlap_text: str = "",
    ) -> PolicyChunk:
        doc_title = doc["title"]
        prefix = self._make_prefix(doc_title, section_path)
        embedding_text = prefix + content

        content_tokens = self._counter.count(content)
        embedding_tokens = self._counter.count(embedding_text)
        overlap_tokens = self._counter.count(overlap_text) if overlap_text else 0

        content_hash = self._compute_content_hash(
            doc["document_id"], section_path, clause_ids, content)

        chunk_id = self._make_chunk_id(
            doc["document_id"], section_title, content)

        return PolicyChunk(
            chunk_id=chunk_id,
            document_id=doc["document_id"],
            document_type=doc["document_type"],
            document_title=doc_title,
            section_path=section_path,
            section_title=section_title,
            section_level=section_level,
            clause_ids=clause_ids,
            clause_fragment_index=clause_fragment_index,
            chunk_index=chunk_index,
            content=content,
            embedding_text=embedding_text,
            content_token_count=content_tokens,
            embedding_token_count=embedding_tokens,
            token_count=content_tokens,
            overlap_token_count=overlap_tokens,
            source_url=doc.get("source_url"),
            fetched_at=doc.get("fetched_at", ""),
            effective_date=doc.get("effective_date"),
            language=doc.get("language", "vi-VN"),
            publisher=doc.get("publisher"),
            content_hash=content_hash,
        )

    def chunk_document(self, doc: dict[str, Any]) -> list[PolicyChunk]:
        chunks: list[PolicyChunk] = []
        doc_title = doc["title"]
        global_chunk_idx = 0

        for sec in doc["sections"]:
            sec_title = sec["title"]
            sec_path = sec.get("path", [sec_title])
            sec_level = sec["level"]
            raw_body = sec.get("raw_body", "")

            if not raw_body.strip():
                continue

            clause_ids = sec.get("clause_ids", [])

            # Reserve token budget for embedding prefix
            prefix_tokens = self._prefix_token_count(doc_title, sec_path)
            # Effective max for content = min(config max, embedding model limit) - prefix budget
            effective_max = min(self.config.max_tokens, self.config.max_embedding_tokens) - prefix_tokens
            if effective_max < 50:
                effective_max = max(50, self.config.max_tokens)

            body_tokens = self._counter.count(raw_body)
            if body_tokens == 0:
                continue

            if body_tokens <= effective_max:
                chunk = self._create_chunk(
                    doc=doc, section_path=sec_path, section_title=sec_title,
                    section_level=sec_level, clause_ids=clause_ids,
                    content=raw_body, chunk_index=global_chunk_idx,
                )
                chunks.append(chunk)
                global_chunk_idx += 1
            else:
                sub_chunks = self._split_section_recursive(
                    doc=doc, section_path=sec_path, section_title=sec_title,
                    section_level=sec_level, clause_ids=clause_ids,
                    content=raw_body, effective_max=effective_max,
                    start_chunk_idx=global_chunk_idx,
                )
                chunks.extend(sub_chunks)
                global_chunk_idx += len(sub_chunks)

        # Re-index with sequential chunk_index (per document)
        for i, c in enumerate(chunks):
            c.chunk_index = i

        return chunks

    def _split_section_recursive(
        self,
        doc: dict[str, Any],
        section_path: list[str],
        section_title: str,
        section_level: int,
        clause_ids: list[str],
        content: str,
        effective_max: int,
        start_chunk_idx: int,
    ) -> list[PolicyChunk]:
        """Split section recursively through boundary hierarchy."""
        # 1. Try clause boundaries
        blocks = self._split_by_clauses(content)
        if len(blocks) > 1:
            return self._process_blocks(
                doc, section_path, section_title, section_level,
                clause_ids, blocks, effective_max, start_chunk_idx)

        # 2. Try list-item boundaries
        blocks = self._split_by_list_items(content)
        if len(blocks) > 1:
            return self._process_blocks(
                doc, section_path, section_title, section_level,
                clause_ids, blocks, effective_max, start_chunk_idx)

        # 3. Try paragraph boundaries (with target_tokens combination)
        blocks = self._split_by_paragraphs(content, effective_max)
        if len(blocks) > 1:
            return self._process_blocks(
                doc, section_path, section_title, section_level,
                clause_ids, blocks, effective_max, start_chunk_idx)

        # 4. Try sentence boundaries
        blocks = self._split_by_sentences(content, effective_max)
        if len(blocks) > 1:
            return self._process_blocks(
                doc, section_path, section_title, section_level,
                clause_ids, blocks, effective_max, start_chunk_idx)

        # 5. Hard token split (last resort)
        return self._hard_split(
            doc, section_path, section_title, section_level,
            clause_ids, content, effective_max, start_chunk_idx)

    def _process_blocks(
        self,
        doc: dict[str, Any],
        section_path: list[str],
        section_title: str,
        section_level: int,
        clause_ids: list[str],
        blocks: list[str],
        effective_max: int,
        start_chunk_idx: int,
    ) -> list[PolicyChunk]:
        """Process split blocks. Recursively split oversized blocks."""
        chunks: list[PolicyChunk] = []
        chunk_idx = start_chunk_idx

        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue

            block_tokens = self._counter.count(block)
            if block_tokens <= effective_max:
                # Determine overlap from previous chunk
                overlap_text = ""
                if i > 0 and self.config.overlap_tokens > 0:
                    prev_chunk = chunks[-1] if chunks else None
                    if prev_chunk and prev_chunk.content:
                        overlap_text = prev_chunk.content
                        # Take last N tokens for overlap (approximate by chars)
                        sep = "\n\n"
                        parts = overlap_text.rsplit(sep, 1)
                        if len(parts) > 1 and self._counter.count(parts[1]) >= self.config.overlap_tokens:
                            overlap_text = parts[1]

                chunk = self._create_chunk(
                    doc=doc, section_path=section_path, section_title=section_title,
                    section_level=section_level, clause_ids=clause_ids,
                    content=block, chunk_index=chunk_idx,
                    clause_fragment_index=None if i == 0 else i,
                    overlap_text=overlap_text,
                )
                chunks.append(chunk)
                chunk_idx += 1
            else:
                # Recursively split oversized block
                sub = self._split_section_recursive(
                    doc, section_path, section_title, section_level,
                    clause_ids, block, effective_max, chunk_idx,
                )
                chunks.extend(sub)
                chunk_idx += len(sub)

        return chunks

    def _split_by_clauses(self, content: str) -> list[str]:
        pattern = re.compile(r"\n(?=(?:\d+\.\d+\.|[IVXLCDM]+\.|\(\w+\))\s)")
        parts = pattern.split(content)
        return [p.strip() for p in parts if p.strip()]

    def _split_by_list_items(self, content: str) -> list[str]:
        """Split at lines starting with (i), (ii), -, etc."""
        pattern = re.compile(r"\n(?=\(\w+\)\s|-\s)")
        parts = pattern.split(content)
        if len(parts) <= 1:
            return parts
        return [p.strip() for p in parts if p.strip()]

    def _split_by_paragraphs(self, content: str, effective_max: int) -> list[str]:
        paragraphs = re.split(r"\n\s*\n", content)
        blocks: list[str] = []
        current = ""
        current_tokens = 0

        # Use target_tokens for combining, but never exceed effective_max
        combine_limit = min(self.config.target_tokens, effective_max)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_tokens = self._counter.count(para)

            if current_tokens == 0:
                current = para
                current_tokens = para_tokens
            else:
                candidate_tokens = current_tokens + para_tokens + 2  # +2 for "\n\n"
                if candidate_tokens <= combine_limit:
                    current += "\n\n" + para
                    current_tokens = candidate_tokens
                else:
                    blocks.append(current)
                    current = para
                    current_tokens = para_tokens

        if current:
            blocks.append(current)

        return blocks if len(blocks) > 1 else [content]

    def _split_by_sentences(self, content: str, effective_max: int) -> list[str]:
        """Split at sentence boundaries (., !, ? followed by space and uppercase or newline)."""
        pattern = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ỸĐ])")
        sentences = pattern.split(content)
        if len(sentences) <= 1:
            return [content]

        blocks: list[str] = []
        current = ""
        current_tokens = 0
        combine_limit = min(self.config.target_tokens, effective_max)

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            sent_tokens = self._counter.count(sent)

            if current_tokens == 0:
                current = sent
                current_tokens = sent_tokens
            else:
                candidate_tokens = current_tokens + sent_tokens + 1  # +1 for space
                if candidate_tokens <= combine_limit:
                    current += " " + sent
                    current_tokens = candidate_tokens
                else:
                    blocks.append(current)
                    current = sent
                    current_tokens = sent_tokens

        if current:
            blocks.append(current)

        return blocks if len(blocks) > 1 else [content]

    def _hard_split(
        self,
        doc: dict[str, Any],
        section_path: list[str],
        section_title: str,
        section_level: int,
        clause_ids: list[str],
        content: str,
        effective_max: int,
        start_chunk_idx: int,
    ) -> list[PolicyChunk]:
        tokens = self._counter.encode(content)

        chunks: list[PolicyChunk] = []
        start = 0
        chunk_idx = start_chunk_idx

        while start < len(tokens):
            end = min(start + effective_max, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._counter.decode(chunk_tokens).strip()

            if not chunk_text:
                start = end
                continue

            # Overlap: include token window from previous chunk
            overlap_text = ""
            if start > 0 and self.config.overlap_tokens > 0:
                overlap_start = max(0, start - self.config.overlap_tokens)
                overlap_tok = tokens[overlap_start:start]
                overlap_text = self._counter.decode(overlap_tok).strip()

            chunk = self._create_chunk(
                doc=doc, section_path=section_path, section_title=section_title,
                section_level=section_level, clause_ids=clause_ids,
                content=chunk_text, chunk_index=chunk_idx,
                clause_fragment_index=chunk_idx - start_chunk_idx,
                overlap_text=overlap_text,
            )
            chunks.append(chunk)
            start = end - self.config.overlap_tokens if end < len(tokens) else len(tokens)
            chunk_idx += 1

        return chunks

    def run(
        self,
        input_dir: Path,
        output_path: Path,
        report_path: Path,
        inspect: bool = False,
    ) -> None:
        input_dir = Path(input_dir)
        md_files = sorted(input_dir.glob("*.md"))

        all_chunks: list[PolicyChunk] = []
        all_warnings: list[str] = []
        docs_parsed = 0
        chunks_by_doc: dict[str, int] = {}
        chunks_by_doc_type: dict[str, int] = {}
        unresolved_docs: list[str] = []

        for md_file in md_files:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.startswith("---"):
                continue
            doc = parse_document(content, str(md_file.name))
            all_warnings.extend(doc["warnings"])
            docs_parsed += 1

            if doc.get("source_url") is None:
                unresolved_docs.append(doc["document_id"])

            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)

            chunks_by_doc[doc["document_id"]] = len(chunks)
            doc_type = doc["document_type"]
            chunks_by_doc_type[doc_type] = chunks_by_doc_type.get(doc_type, 0) + len(chunks)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in all_chunks:
                f.write(chunk.model_dump_json() + "\n")

        content_tokens = [c.content_token_count for c in all_chunks]
        embedding_tokens = [c.embedding_token_count for c in all_chunks]
        sorted_ct = sorted(content_tokens) if content_tokens else [0]
        sorted_et = sorted(embedding_tokens) if embedding_tokens else [0]
        p95_idx = int(len(sorted_ct) * 0.95)
        ep95_idx = int(len(sorted_et) * 0.95)

        empty_count = sum(1 for c in all_chunks if not c.content.strip())
        heading_only = sum(
            1 for c in all_chunks
            if c.content.strip() and all(
                line.strip().startswith("#") or not line.strip()
                for line in c.content.strip().split("\n"))
        )

        # Oversized: exceeds embedding model limit (= embedding_text, not just content)
        oversized = [c.chunk_id for c in all_chunks
                     if c.embedding_token_count > self.config.max_embedding_tokens]

        chunk_ids = [c.chunk_id for c in all_chunks]
        dup_ids = len(chunk_ids) - len(set(chunk_ids))
        content_hashes = [c.content_hash for c in all_chunks]
        dup_hashes = len(content_hashes) - len(set(content_hashes))

        report = ChunkReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            config=self.config,
            document_count=docs_parsed,
            chunk_count=len(all_chunks),
            empty_chunk_count=empty_count,
            heading_only_chunk_count=heading_only,
            duplicate_chunk_id_count=dup_ids,
            duplicate_content_hash_count=dup_hashes,
            oversized_chunk_count=len(oversized),
            unresolved_source_count=len(unresolved_docs),
            token_stats={
                "min": min(content_tokens) if content_tokens else 0,
                "median": statistics.median(sorted_ct) if sorted_ct else 0,
                "p95": sorted_ct[p95_idx] if sorted_ct else 0,
                "max": max(content_tokens) if content_tokens else 0,
            },
            embedding_token_stats={
                "min": min(embedding_tokens) if embedding_tokens else 0,
                "median": statistics.median(sorted_et) if sorted_et else 0,
                "p95": sorted_et[ep95_idx] if sorted_et else 0,
                "max": max(embedding_tokens) if embedding_tokens else 0,
            },
            chunks_by_document=chunks_by_doc,
            chunks_by_document_type=chunks_by_doc_type,
            oversized_chunks=oversized,
            unresolved_sources=unresolved_docs,
            warnings=all_warnings,
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json())

        print(f"Documents: {docs_parsed}")
        print(f"Chunks: {len(all_chunks)}")
        print(f"Content token range: {report.token_stats['min']}–{report.token_stats['max']} (median: {report.token_stats['median']})")
        print(f"Embedding token range: {report.embedding_token_stats['min']}–{report.embedding_token_stats['max']} (median: {report.embedding_token_stats['median']})")
        print(f"Oversized exceptions (embedding > {self.config.max_embedding_tokens}): {len(oversized)}")
        print(f"Unresolved sources: {len(unresolved_docs)}")
        print(f"Duplicate chunk IDs: {dup_ids}")
        validation_ok = empty_count == 0 and heading_only == 0 and dup_ids == 0
        print(f"Validation: {'PASSED' if validation_ok else 'FAILED'}")

        if inspect:
            self._inspect(all_chunks, chunks_by_doc)

    def _inspect(self, chunks: list[PolicyChunk], chunks_by_doc: dict[str, int]) -> None:
        print("\n=== INSPECT ===")
        seen_docs: dict[str, int] = {}
        print("\n--- First 3 chunks per document ---")
        for c in chunks:
            did = c.document_id
            seen_docs.setdefault(did, 0)
            if seen_docs[did] < 3:
                seen_docs[did] += 1
                print(f"\n  [{c.chunk_id}]")
                print(f"  content={c.content_token_count}t  embed={c.embedding_token_count}t")
                print(f"  Section: {c.section_title}")
                print(f"  Content: {c.content[:120]}...")

        if chunks:
            longest = max(chunks, key=lambda x: x.content_token_count)
            print(f"\n--- Longest chunk (by content tokens): {longest.chunk_id} ({longest.content_token_count}t) ---")
            print(f"  {longest.content[:200]}...")

            shortest = min(chunks, key=lambda x: x.content_token_count)
            print(f"\n--- Shortest chunk: {shortest.chunk_id} ({shortest.content_token_count}t) ---")
            print(f"  {shortest.content[:200]}...")

        overlap_chunks = [c for c in chunks if c.overlap_token_count > 0]
        if overlap_chunks:
            print(f"\n--- Overlap chunks ({len(overlap_chunks)}) ---")
            for c in overlap_chunks[:3]:
                print(f"  {c.chunk_id}: {c.overlap_token_count} overlap tokens")

        fragment_chunks = [c for c in chunks if c.clause_fragment_index is not None]
        if fragment_chunks:
            print(f"\n--- Clause fragments ({len(fragment_chunks)}) ---")
            for c in fragment_chunks[:3]:
                print(f"  {c.chunk_id}: fragment={c.clause_fragment_index}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Section-aware policy chunking pipeline")
    parser.add_argument("--input-dir", required=True, help="Directory containing normalized .md files")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--report", required=True, help="Output report JSON path")
    parser.add_argument("--target-tokens", type=int, default=450, help="Target tokens per chunk")
    parser.add_argument("--max-tokens", type=int, default=600, help="Max content tokens per chunk")
    parser.add_argument("--overlap-tokens", type=int, default=50, help="Overlap tokens between chunks")
    parser.add_argument("--max-embedding-tokens", type=int, default=512,
                        help="Max tokens for embedding model (default: 512 for E5)")
    parser.add_argument("--inspect", action="store_true", help="Print detailed inspection output")

    args = parser.parse_args()

    config = ChunkingConfig(
        tokenizer_name=pipeline._counter.name,
        target_tokens=args.target_tokens,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens,
        max_embedding_tokens=args.max_embedding_tokens,
    )

    pipeline = ChunkingPipeline(config=config)
    pipeline.run(
        input_dir=Path(args.input_dir),
        output_path=Path(args.output),
        report_path=Path(args.report),
        inspect=args.inspect,
    )


if __name__ == "__main__":
    main()
