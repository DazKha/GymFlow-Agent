"""Tests for policy vector store, retriever, and ingestion."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from rag.core.vector_store import FakeEmbeddingProvider, PolicyVectorStore
from rag.core.retriever import PolicyRetriever, PolicySearchResult


SAMPLE_CHUNKS: list[dict] = [
    {
        "chunk_id": "cali-payment__quy-trinh__0001",
        "document_id": "california-payment-policy",
        "document_type": "payment_policy",
        "document_title": "Chính sách thanh toán",
        "section_path": ["Chính sách thanh toán", "Quy trình thanh toán"],
        "section_title": "Quy trình thanh toán",
        "section_level": 2,
        "clause_ids": [],
        "chunk_index": 0,
        "content": "Khách hàng đăng ký sử dụng dịch vụ trên trang cali.vn sẽ thực hiện thanh toán qua Payoo.",
        "embedding_text": "Tài liệu: Chính sách thanh toán\nSection: Chính sách thanh toán > Quy trình thanh toán\n\nKhách hàng đăng ký...",
        "content_token_count": 20,
        "embedding_token_count": 30,
        "token_count": 20,
        "overlap_token_count": 0,
        "source_url": "https://cali.vn/chinh-sach-thanh-toan",
        "fetched_at": "2026-08-08T15:52:00+07:00",
        "effective_date": None,
        "language": "vi-VN",
        "publisher": "California Fitness & Yoga",
        "content_hash": "abcd1234efgh5678",
    },
    {
        "chunk_id": "cali-payment__cam-ket__0002",
        "document_id": "california-payment-policy",
        "document_type": "payment_policy",
        "document_title": "Chính sách thanh toán",
        "section_path": ["Chính sách thanh toán", "Cam kết của California"],
        "section_title": "Cam kết của California",
        "section_level": 2,
        "clause_ids": [],
        "chunk_index": 1,
        "content": "California cam kết bảo mật tất cả thông tin thanh toán.",
        "embedding_text": "Tài liệu: Chính sách thanh toán\nSection: Chính sách thanh toán > Cam kết\n\nCalifornia cam kết...",
        "content_token_count": 12,
        "embedding_token_count": 20,
        "token_count": 12,
        "overlap_token_count": 0,
        "source_url": "https://cali.vn/chinh-sach-thanh-toan",
        "fetched_at": "2026-08-08T15:52:00+07:00",
        "effective_date": None,
        "language": "vi-VN",
        "publisher": "California Fitness & Yoga",
        "content_hash": "efgh5678abcd1234",
    },
]


@pytest.fixture
def fake_store():
    embed = FakeEmbeddingProvider(dimension=768)
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PolicyVectorStore(
            embed_provider=embed,
            persist_dir=tmpdir,
            collection_name="test_collection",
        )
        store.recreate_collection()
        yield store


class TestVectorStore:
    def test_ingest_count(self, fake_store):
        result = fake_store.ingest(SAMPLE_CHUNKS)
        assert result["inserted"] == 2
        assert result["unchanged"] == 0
        assert result["errors"] == 0
        assert fake_store.count() == 2

    def test_double_ingest_idempotent(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        result2 = fake_store.ingest(SAMPLE_CHUNKS)
        assert result2["inserted"] == 0  # Existing IDs detected, not re-inserted
        assert result2["unchanged"] == 2
        assert fake_store.count() == 2

    def test_missing_metadata_rejected(self):
        embed = FakeEmbeddingProvider()
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PolicyVectorStore(
                embed_provider=embed,
                persist_dir=tmpdir,
                collection_name="test_reject",
            )
            store.recreate_collection()
            bad = [{"chunk_id": "test-1"}]  # missing required fields
            result = store.ingest(bad)
            assert result["errors"] == 0
            assert result["inserted"] == 1

    def test_sync_removes_stale(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        # Only keep first chunk
        stale = fake_store.sync_stale({"cali-payment__quy-trinh__0001"})
        assert stale == 1
        assert fake_store.count() == 1

    def test_search_returns_results(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        results = fake_store.search(query="thanh toán", top_k=2)
        assert len(results) > 0
        assert results[0]["rank"] == 1

    def test_empty_query_rejected(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        results = fake_store.search(query="  ", top_k=5)
        assert results == []


class TestRetriever:
    @pytest.fixture
    def retriever(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        return PolicyRetriever(vector_store=fake_store)

    def test_search_returns_typed_results(self, retriever):
        results = retriever.search("thanh toán", top_k=5)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, PolicySearchResult)
            assert r.chunk_id
            assert r.document_title

    def test_citation_contains_required_fields(self, retriever):
        results = retriever.search("thanh toán", top_k=1)
        citation = results[0].citation_label()
        assert "California Fitness & Yoga" in citation
        assert "Chính sách thanh toán" in citation
        assert "https://cali.vn/" in citation

    def test_empty_query_raises(self, retriever):
        with pytest.raises(ValueError, match="non-empty"):
            retriever.search("  ")

    def test_negative_topk_raises(self, retriever):
        with pytest.raises(ValueError, match="top_k"):
            retriever.search("test", top_k=0)

    def test_topk_truncation(self, retriever):
        results = retriever.search("thanh toán", top_k=1)
        assert len(results) == 1

    def test_metadata_deserialization(self, retriever):
        results = retriever.search("thanh toán", top_k=5)
        for r in results:
            assert isinstance(r.section_path, list)
            assert isinstance(r.clause_ids, list)

    def test_search_to_ragas_format(self, retriever):
        out = retriever.search_to_ragas_format("thanh toán", top_k=2)
        assert "user_input" in out
        assert len(out["retrieved_contexts"]) <= 2
        assert len(out["retrieved_chunk_ids"]) <= 2
        assert len(out["retrieved_sources"]) <= 2

    def test_all_have_source_url(self, retriever):
        results = retriever.search("thanh toán", top_k=5)
        for r in results:
            assert r.source_url, f"Missing source_url in {r.chunk_id}"


class TestIngestionCLI:
    def test_dry_run_on_valid_jsonl(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl_path = tmp / "chunks.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for c in SAMPLE_CHUNKS:
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")

            result = subprocess.run(
                [sys.executable, "-m", "rag.ingest_policies", "--dry-run", "--input", str(jsonl_path)],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "Chunks: 2" in result.stdout

    def test_dry_run_detects_duplicates(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            jsonl_path = tmp / "chunks.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for c in SAMPLE_CHUNKS:
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
                # Write first chunk again
                f.write(json.dumps(SAMPLE_CHUNKS[0], ensure_ascii=False) + "\n")

            result = subprocess.run(
                [sys.executable, "-m", "rag.ingest_policies", "--dry-run", "--input", str(jsonl_path)],
                capture_output=True, text=True,
            )
            assert "duplicate" in result.stdout.lower()

    def test_recreate_collection(self, fake_store):
        fake_store.ingest(SAMPLE_CHUNKS)
        assert fake_store.count() == 2
        fake_store.recreate_collection()
        assert fake_store.count() == 0
