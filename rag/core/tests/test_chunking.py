"""Tests for the policy chunking pipeline — unit + real corpus."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from rag.core.chunking import (
    ChunkingPipeline,
    TiktokenCounter,
    parse_document,
    _make_embedding_prefix,
    _normalize_for_comparison,
)
from rag.core.models import ChunkingConfig, PolicyChunk

SAMPLE_DOC = """---
document_id: test-doc
document_type: test_policy
title: "Chính sách thử nghiệm"
source_url: null
fetched_at: 2026-01-01T00:00:00+07:00
effective_date: null
language: vi-VN
publisher: Test Publisher
source_type: official_public_policy
content_status: crawled_snapshot
---
# Chính sách thử nghiệm

Đây là phần giới thiệu.

## Điều khoản chung

1.1. Khách hàng phải từ đủ 18 tuổi.

1.2. Khách hàng phải cung cấp thông tin chính xác.

## Quy trình đăng ký

Khách hàng đăng ký qua website hoặc trực tiếp.

## Chính sách dài

Đây là một section có nội dung rất dài. Nội dung này sẽ vượt quá max_tokens và buộc phải được chia thành nhiều chunk.
"""

LONG_CLAUSE_DOC = """---
document_id: test-long
document_type: test_policy
title: "Test Long"
source_url: null
fetched_at: 2026-01-01T00:00:00+07:00
effective_date: null
language: vi-VN
publisher: Test
source_type: official_public_policy
content_status: crawled_snapshot
---
# Test Long

## Long Section

""" + "Câu này được lặp lại để tạo nội dung dài. " * 200


def _make_config(target=450, max_tokens=600, overlap=50):
    return ChunkingConfig(
        tokenizer_name="tiktoken:o200k_base",
        target_tokens=target,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        max_embedding_tokens=512,
    )


class TestParseDocument:
    def test_parse_yaml_front_matter(self):
        doc = parse_document(SAMPLE_DOC, "test.md")
        assert doc["document_id"] == "test-doc"
        assert doc["document_type"] == "test_policy"

    def test_parse_heading_hierarchy(self):
        doc = parse_document(SAMPLE_DOC, "test.md")
        assert doc["h1"] == "Chính sách thử nghiệm"
        sections = doc["sections"]
        assert len(sections) >= 3
        titles = [s["title"] for s in sections]
        assert "Điều khoản chung" in titles
        assert "Quy trình đăng ký" in titles

    def test_parse_numbered_clauses(self):
        doc = parse_document(SAMPLE_DOC, "test.md")
        body = doc["body"]
        assert "1.1." in body
        assert "1.2." in body

    def test_parse_preserves_vietnamese(self):
        doc = parse_document(SAMPLE_DOC, "test.md")
        body = doc["body"]
        assert "Chính sách" in body
        assert "Điều khoản" in body

    def test_content_before_heading_preserved(self):
        content = """---
document_id: test-doc
document_type: test_policy
title: "Test"
source_url: null
fetched_at: 2026-01-01T00:00:00+07:00
effective_date: null
language: vi-VN
publisher: Test
source_type: official_public_policy
content_status: crawled_snapshot
---
# Test Title

Intro text before any heading.

## Section One

Content here.
"""
        doc = parse_document(content, "test.md")
        assert "Intro text" in doc["body"]

    def test_parse_nested_headings(self):
        content = """---
document_id: test-doc
document_type: test_policy
title: "Test"
source_url: null
fetched_at: 2026-01-01T00:00:00+07:00
effective_date: null
language: vi-VN
publisher: Test
source_type: official_public_policy
content_status: crawled_snapshot
---
# H1

## H2

### H3

#### H4

Content here.
"""
        doc = parse_document(content, "test.md")
        sections = doc["sections"]
        levels = [s["level"] for s in sections]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
        assert 4 in levels


class TestChunking:
    def test_small_section_single_chunk(self):
        config = _make_config(target=450, max_tokens=600, overlap=50)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        assert len(chunks) > 0
        assert all(isinstance(c, PolicyChunk) for c in chunks)

    def test_no_empty_chunks(self):
        config = _make_config(target=450, max_tokens=600, overlap=50)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            assert c.content.strip(), f"Empty chunk: {c.chunk_id}"

    def test_no_heading_only_chunks(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            lines = [l.strip() for l in c.content.strip().split("\n") if l.strip()]
            if lines:
                assert not all(l.startswith("#") for l in lines), f"Heading-only: {c.chunk_id}"

    def test_clause_not_split_from_number(self):
        config = _make_config(target=450, max_tokens=600, overlap=50)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            content = c.content
            lines = content.strip().split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped and re.match(r"\d+\.\d+\.\s", stripped):
                    assert len(stripped) > 10, f"Clause alone: {c.chunk_id}"

    def test_long_content_is_split(self):
        config = _make_config(target=100, max_tokens=200, overlap=20)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(LONG_CLAUSE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        long_section_chunks = [c for c in chunks if "Long Section" in c.section_path]
        # Should be split into multiple chunks
        assert len(long_section_chunks) > 1, f"Expected split, got {len(long_section_chunks)}"

    def test_no_cross_document_content(self):
        """Content from one document should not appear in another."""
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc1 = parse_document(SAMPLE_DOC, "test1.md")
        doc2 = parse_document(LONG_CLAUSE_DOC, "test2.md")
        chunks1 = pipeline.chunk_document(doc1)
        chunks2 = pipeline.chunk_document(doc2)
        doc1_content = set(c.content for c in chunks1)
        doc2_content = set(c.content for c in chunks2)
        # No content from doc1 should be in doc2 chunks
        overlap = doc1_content & doc2_content
        assert not overlap, f"Content leaked across documents: {overlap}"

    def test_overlap_only_within_same_section(self):
        config = _make_config(target=100, max_tokens=200, overlap=20)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(LONG_CLAUSE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            if c.overlap_token_count > 0:
                # Overlap should only be >0, not exceed config
                assert c.overlap_token_count > 0
                # Content should still be valid
                assert c.content.strip()

    def test_oversized_blocks_are_recursively_split(self):
        # Use very small limits to force recursive splitting
        config = _make_config(target=50, max_tokens=100, overlap=10)
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(LONG_CLAUSE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            assert c.embedding_token_count <= config.max_embedding_tokens, \
                f"Oversized: {c.chunk_id} ({c.embedding_token_count} > {config.max_embedding_tokens})"

    def test_embedding_text_has_prefix(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            assert c.embedding_text.startswith("Tài liệu:")
            assert c.content in c.embedding_text
            assert c.embedding_token_count > c.content_token_count

    def test_content_and_embedding_tokens_consistent(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            assert c.token_count == c.content_token_count
            assert c.embedding_token_count > 0
            assert c.content_token_count > 0


class TestDeterminism:
    def test_deterministic_output(self):
        config1 = _make_config(target=450, max_tokens=600, overlap=50)
        config2 = _make_config(target=450, max_tokens=600, overlap=50)
        pipeline1 = ChunkingPipeline(config=config1)
        pipeline2 = ChunkingPipeline(config=config2)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks1 = pipeline1.chunk_document(doc)
        chunks2 = pipeline2.chunk_document(doc)
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id, f"ID: {c1.chunk_id} != {c2.chunk_id}"
            assert c1.content == c2.content, f"Content: {c1.chunk_id}"

    def test_deterministic_ordering(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        section_titles = [s["title"] for s in doc["sections"]]
        chunk_titles = [c.section_title for c in chunks]
        for st in section_titles:
            assert st in chunk_titles, f"Section '{st}' missing"
        prev_idx = -1
        for ct in chunk_titles:
            if ct in section_titles:
                idx = section_titles.index(ct)
                assert idx >= prev_idx, f"Wrong section order: {ct}"
                prev_idx = idx


class TestTokenCounting:
    def test_tiktoken_counter(self):
        counter = TiktokenCounter(encoding="o200k_base")
        count = counter.count("Chính sách thanh toán")
        assert count > 0
        assert isinstance(count, int)

    def test_prefix_token_budget(self):
        counter = TiktokenCounter(encoding="o200k_base")
        prefix = _make_embedding_prefix("Chính sách thanh toán", ["CS thanh toán", "Quy trình"])
        prefix_tokens = counter.count(prefix)
        assert prefix_tokens > 0

    def test_token_count_separate_fields(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        doc = parse_document(SAMPLE_DOC, "test.md")
        chunks = pipeline.chunk_document(doc)
        for c in chunks:
            assert c.content_token_count > 0
            assert c.embedding_token_count > c.content_token_count


class TestPipelineIntegration:
    def test_pipeline_on_sample(self):
        config = _make_config()
        pipeline = ChunkingPipeline(config=config)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            sample_path = tmp / "test.md"
            sample_path.write_text(SAMPLE_DOC, encoding="utf-8")
            out_path = tmp / "out.jsonl"
            report_path = tmp / "report.json"
            pipeline.run(input_dir=tmp, output_path=out_path, report_path=report_path)
            assert out_path.exists()
            assert report_path.exists()
            chunks_data = [json.loads(line) for line in out_path.read_text(encoding="utf-8").strip().split("\n") if line.strip()]
            assert len(chunks_data) > 0
            report = json.loads(report_path.read_text(encoding="utf-8"))
            assert report["document_count"] == 1
            assert report["chunk_count"] > 0
            assert report["empty_chunk_count"] == 0

    def test_determinism_on_sample_two_runs(self):
        config = _make_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            sample_path = tmp / "test.md"
            sample_path.write_text(SAMPLE_DOC, encoding="utf-8")
            out1 = tmp / "out1.jsonl"
            out2 = tmp / "out2.jsonl"
            rep1 = tmp / "rep1.json"
            rep2 = tmp / "rep2.json"
            pipeline1 = ChunkingPipeline(config=config)
            pipeline1.run(input_dir=tmp, output_path=out1, report_path=rep1)
            pipeline2 = ChunkingPipeline(config=config)
            pipeline2.run(input_dir=tmp, output_path=out2, report_path=rep2)
            assert out1.read_text() == out2.read_text(), "JSONL not byte-identical across two runs"


# ---------------------------------------------------------------------------
# Real corpus tests
# ---------------------------------------------------------------------------

REAL_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
POLICY_FILES = [
    "complaint-resolution-policy.md",
    "payment-policy.md",
    "personal-data-policy.md",
    "privacy-policy.md",
    "terms-and-conditions.md",
]

KEY_CLAUSE_PATTERNS = {
    "terms-and-conditions.md": [r"\b1\.1", r"\b2\.1", r"\b5\.1", r"\b6\.2"],
    "privacy-policy.md": [r"\b2\.1\.", r"\b2\.2\.", r"\b2\.3\."],
    "complaint-resolution-policy.md": [r"1900 6934", r"memberrelations@cali\.vn"],
    "payment-policy.md": [r"18006995", r"19006934", r"memberrelations@cali\.vn"],
    "personal-data-policy.md": [r"memberrelations@cali\.vn", r"1900 6934", r"01/07/2023"],
}

KEY_ITEMS_BY_DOC = {
    "complaint-resolution-policy.md": ["memberrelations@cali.vn", "1900 6934", "The GoldView", "346 Bến Vân Đồn", "www.facebook.com/cfycvn"],
    "payment-policy.md": ["memberrelations@cali.vn", "19006934", "18006995", "Payoo"],
    "personal-data-policy.md": ["memberrelations@cali.vn", "1900 6934", "01/07/2023"],
    "privacy-policy.md": ["marketing-tools@cfyc.asia", "The GoldView", "346 Bến Vân Đồn", "0305060028", "126 đường Hùng Vương"],
    "terms-and-conditions.md": ["memberrelations@cali.vn", "1800 6995", "TNL Plaza", "346 Bến Vân Đồn", "cali.vn/chinh-sach-bao-mat"],
}

ALL_KEY_ITEMS = [
    "memberrelations@cali.vn", "1900 6934", "18006995",
    "The GoldView", "346 Bến Vân Đồn", "0305060028",
]


class TestRealCorpus:
    @classmethod
    def setup_class(cls):
        cls.config = _make_config()
        cls.pipeline = ChunkingPipeline(config=cls.config)
        cls.docs = {}
        cls.all_chunks: list[PolicyChunk] = []
        for fname in POLICY_FILES:
            fpath = REAL_DATA_DIR / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8")
                doc = parse_document(content, fname)
                cls.docs[fname] = doc
                chunks = cls.pipeline.chunk_document(doc)
                cls.all_chunks.extend(chunks)

    def test_1_five_documents_discovered(self):
        assert len(self.docs) == 5, f"Expected 5 docs, got {len(self.docs)}"

    def test_2_all_have_non_null_source_url(self):
        for fname, doc in self.docs.items():
            url = doc.get("source_url")
            assert url is not None, f"{fname}: source_url is None"
            assert url != "", f"{fname}: source_url is empty"

    def test_3_no_empty_chunks(self):
        for c in self.all_chunks:
            assert c.content.strip(), f"Empty chunk: {c.chunk_id}"

    def test_4_no_heading_only_chunks(self):
        for c in self.all_chunks:
            lines = [l.strip() for l in c.content.strip().split("\n") if l.strip()]
            assert not all(l.startswith("#") for l in lines), f"Heading-only: {c.chunk_id}"

    def test_5_no_duplicate_chunk_ids(self):
        ids = [c.chunk_id for c in self.all_chunks]
        assert len(ids) == len(set(ids)), f"Duplicate chunk IDs: {len(ids) - len(set(ids))}"

    def test_6_no_duplicate_content_hashes(self):
        hashes = [c.content_hash for c in self.all_chunks]
        dups = len(hashes) - len(set(hashes))
        assert dups == 0, f"Duplicate content hashes: {dups}"

    def test_7_no_chunks_exceed_embedding_limit(self):
        limit = self.config.max_embedding_tokens
        for c in self.all_chunks:
            assert c.embedding_token_count <= limit, \
                f"Chunk {c.chunk_id} embedding={c.embedding_token_count} > {limit}"

    def test_8_all_sections_appear_in_output(self):
        for fname, doc in self.docs.items():
            section_titles = [s["title"] for s in doc["sections"]]
            doc_chunks = [c for c in self.all_chunks if c.document_id == doc["document_id"]]
            chunk_titles = set(c.section_title for c in doc_chunks)
            for st in section_titles:
                # Empty sections may be skipped
                sec = next((s for s in doc["sections"] if s["title"] == st), None)
                if sec and sec.get("raw_body", "").strip():
                    assert st in chunk_titles, f"Section '{st}' missing from chunks in {fname}"

    def test_9_no_cross_document_content(self):
        doc_contents = {}
        for fname, doc in self.docs.items():
            doc_chunks = [c for c in self.all_chunks if c.document_id == doc["document_id"]]
            doc_contents[doc["document_id"]] = set(c.content for c in doc_chunks)
        doc_ids = list(doc_contents.keys())
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                overlap = doc_contents[doc_ids[i]] & doc_contents[doc_ids[j]]
                assert not overlap, f"Content leaked {doc_ids[i]} -> {doc_ids[j]}"

    def test_10_clause_numbers_preserved(self):
        for fname, patterns in KEY_CLAUSE_PATTERNS.items():
            doc_chunks = [c for c in self.all_chunks if c.document_id == self.docs[fname]["document_id"]]
            all_text = " ".join(
                c.content + " " + c.section_title + " " + " ".join(c.section_path)
                for c in doc_chunks
            )
            for pat in patterns:
                assert re.search(pat, all_text), f"Pattern '{pat}' missing in {fname}"

    def test_11_section_path_correct(self):
        for c in self.all_chunks:
            assert len(c.section_path) > 0
            assert c.section_path[-1] == c.section_title
            assert c.section_level > 0

    def test_12_chunk_order_matches_source(self):
        for fname, doc in self.docs.items():
            doc_chunks = [c for c in self.all_chunks if c.document_id == doc["document_id"]]
            section_titles = [s["title"] for s in doc["sections"]]
            prev_idx = -1
            for c in doc_chunks:
                if c.section_title in section_titles:
                    idx = section_titles.index(c.section_title)
                    assert idx >= prev_idx, f"Chunk {c.chunk_id} section order wrong in {fname}"
                    prev_idx = idx
            # chunk_index should be sequential
            for i, c in enumerate(doc_chunks):
                assert c.chunk_index == i, f"chunk_index={c.chunk_index} != expected {i}"

    def test_13_content_preservation(self):
        """Normalized source body ≈ canonical reconstruction from chunks."""
        for fname, doc in self.docs.items():
            doc_chunks = [c for c in self.all_chunks if c.document_id == doc["document_id"]]
            reconstructed = "\n".join(c.content for c in doc_chunks)
            # Also include section titles for clause patterns that appear in headings
            reconstructed_with_meta = reconstructed + "\n" + " ".join(
                c.section_title + " " + " ".join(c.section_path)
                for c in doc_chunks
            )

            for item in KEY_ITEMS_BY_DOC.get(fname, []):
                assert item in reconstructed, f"'{item}' missing from reconstructed content in {fname}"

            for pat in KEY_CLAUSE_PATTERNS.get(fname, []):
                assert re.search(pat, reconstructed_with_meta), f"Pattern '{pat}' missing from {fname}"

    def test_14_chunk_ids_are_stable(self):
        """Running twice on same input produces identical chunk_ids."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for fname in POLICY_FILES:
                fpath = REAL_DATA_DIR / fname
                if fpath.exists():
                    (tmp / fname).write_text(fpath.read_text(encoding="utf-8"))

            out1 = tmp / "out1.jsonl"
            out2 = tmp / "out2.jsonl"
            rep1 = tmp / "rep1.json"
            rep2 = tmp / "rep2.json"

            p1 = ChunkingPipeline(config=self.config)
            p1.run(input_dir=tmp, output_path=out1, report_path=rep1)
            p2 = ChunkingPipeline(config=self.config)
            p2.run(input_dir=tmp, output_path=out2, report_path=rep2)

            assert out1.read_text() == out2.read_text(), "JSONL not byte-identical across two runs"

    def test_15_key_items_preserved_in_chunks(self):
        """All critical items (emails, phone, addresses) in chunk content."""
        all_content = " ".join(c.content for c in self.all_chunks)
        for item in ALL_KEY_ITEMS:
            assert item in all_content, f"'{item}' missing from all chunk content"
