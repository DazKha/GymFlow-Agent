from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from rag.core import pipeline
from rag.core.retriever import PolicySearchResult


def _result(content: str = "Refunds are available under clause 4.2.") -> PolicySearchResult:
    return PolicySearchResult(
        chunk_id="chunk-1",
        content=content,
        document_id="policy-1",
        document_title="Refund policy",
        section_path=["Refunds"],
        clause_ids=["4.2"],
        source_url="https://example.test/refunds",
    )


def test_normal_query_uses_dense_search_and_citation_context(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    class FakeRetriever:
        def search(self, query: str, top_k: int) -> list[PolicySearchResult]:
            calls.append((query, top_k))
            return [_result()]

    class FakeLLM:
        def invoke(self, prompt: str) -> SimpleNamespace:
            assert "Refunds are available under clause 4.2." in prompt
            assert "https://example.test/refunds" in prompt
            return SimpleNamespace(content="Provider answer")

    monkeypatch.setattr(pipeline, "PolicyRetriever", FakeRetriever)
    monkeypatch.setattr(pipeline, "_get_llm", lambda: FakeLLM())

    assert pipeline.run_policy_rag("How do refunds work?") == "Provider answer"
    assert calls == [("How do refunds work?", pipeline.RETRIEVE_TOP_K)]


def test_empty_query_returns_fallback_without_constructing_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "PolicyRetriever",
        lambda: pytest.fail("retriever should not be constructed"),
    )
    monkeypatch.setattr(
        pipeline,
        "_get_llm",
        lambda: pytest.fail("LLM should not be constructed"),
    )

    assert pipeline.run_policy_rag("  ") == "Câu hỏi trống, không thể tra cứu."


def test_empty_search_result_returns_no_document_fallback_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRetriever:
        def search(self, query: str, top_k: int) -> list[PolicySearchResult]:
            return []

    monkeypatch.setattr(pipeline, "PolicyRetriever", FakeRetriever)
    monkeypatch.setattr(
        pipeline,
        "_get_llm",
        lambda: pytest.fail("LLM should not be constructed"),
    )

    assert pipeline.run_policy_rag("unknown policy") == "Không đủ dữ liệu để trả lời chắc chắn."


def test_provider_failure_returns_safe_message_with_chained_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = RuntimeError("secret-provider-token")

    class FakeRetriever:
        def search(self, query: str, top_k: int) -> list[PolicySearchResult]:
            raise failure

    monkeypatch.setattr(pipeline, "PolicyRetriever", FakeRetriever)

    message = pipeline.run_policy_rag("refunds")

    assert message == "Không thể tra cứu chính sách lúc này."
    assert "secret-provider-token" not in message


def test_llm_construction_failure_is_safe_and_chained(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    failure = RuntimeError("provider-key=secret-provider-token")

    monkeypatch.setattr(pipeline, "PolicyRetriever", lambda: SimpleNamespace(
        search=lambda query, top_k: [_result()]
    ))
    monkeypatch.setattr(pipeline, "_get_llm", lambda: (_ for _ in ()).throw(failure))

    message = pipeline.run_policy_rag("refunds")

    assert message == "Không thể tra cứu chính sách lúc này."
    assert "secret-provider-token" not in message
    logged = caplog.records[-1].exc_info[1]
    assert logged.__cause__ is failure


def test_llm_invocation_failure_is_safe_and_chained(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    failure = RuntimeError("provider-response=secret-provider-token")

    class FailingLLM:
        def invoke(self, prompt: str) -> SimpleNamespace:
            raise failure

    monkeypatch.setattr(pipeline, "PolicyRetriever", lambda: SimpleNamespace(
        search=lambda query, top_k: [_result()]
    ))
    monkeypatch.setattr(pipeline, "_get_llm", lambda: FailingLLM())

    message = pipeline.run_policy_rag("refunds")

    assert message == "Không thể tra cứu chính sách lúc này."
    assert "secret-provider-token" not in message
    logged = caplog.records[-1].exc_info[1]
    assert logged.__cause__ is failure


def test_tools_package_imports_query_policy_tool() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import tools.query_gym_policy"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
