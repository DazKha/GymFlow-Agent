from dataclasses import replace

from rag.core.retriever import PolicySearchResult
from rag.evaluation.pipeline import evaluate_retrieval
from rag.research.retrieval_config import experiment_configs


def _result(chunk_id: str) -> PolicySearchResult:
    return PolicySearchResult(
        chunk_id=chunk_id, content=chunk_id, document_id="doc", document_title="Title",
        section_path=[], clause_ids=[], source_url="",
    )


class FakeRetriever:
    def search(self, query: str, top_k: int = 5) -> list[PolicySearchResult]:
        return [_result("gold"), _result("other")][:top_k]


def test_evaluate_retrieval_uses_explicit_configuration():
    case = {"query": "q", "relevant_chunk_ids": ["gold"]}
    config = replace(experiment_configs()[0], final_top_k=1, candidate_pool_size=1)

    report = evaluate_retrieval([case], FakeRetriever(), config)

    assert report.experiment == "dense"
    assert report.metrics["recall_at_1"] == 1.0


class QueryAwareRetriever(FakeRetriever):
    def search(self, query: str, top_k: int = 5) -> list[PolicySearchResult]:
        first = "gold-b" if query == "a" else "gold-a"
        second = "gold-a" if query == "a" else "gold-b"
        return [_result(first), _result(second)][:top_k]


def test_evaluate_retrieval_scores_relevance_per_case():
    config = replace(experiment_configs()[0], final_top_k=2, candidate_pool_size=2)
    cases = [
        {"query": "a", "relevant_chunk_ids": ["gold-a"]},
        {"query": "b", "relevant_chunk_ids": ["gold-b"]},
    ]

    report = evaluate_retrieval(cases, QueryAwareRetriever(), config)

    assert report.metrics["mrr"] == 0.5
