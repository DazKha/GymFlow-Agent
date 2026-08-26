from dataclasses import replace

from rag.core.retriever import PolicySearchResult
from rag.evaluation.pipeline import evaluate_retrieval
from rag.evaluation.pipeline import compare_retrieval_variants
from rag.research.query_expansion import ExpansionResult
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


class RecordingRetriever(FakeRetriever):
    def __init__(self):
        self.calls = []

    def search(self, query: str, top_k: int = 5) -> list[PolicySearchResult]:
        self.calls.append((query, top_k))
        return [_result(f"{query}-1"), _result(f"{query}-2")]


class RecordingExpander:
    def __init__(self):
        self.calls = []

    def expand(self, query: str) -> ExpansionResult:
        self.calls.append(query)
        return ExpansionResult([query, f"{query}-expanded"])


class RecordingReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, results, top_k=None):
        self.calls.append((query, results, top_k))
        return results


def test_compare_retrieval_variants_injects_fakes_for_all_four_variants():
    config = [replace(item, candidate_pool_size=2, final_top_k=1) for item in experiment_configs()]
    retriever, expander, reranker = RecordingRetriever(), RecordingExpander(), RecordingReranker()

    reports = compare_retrieval_variants(
        [{"query": "q", "relevant_chunk_ids": ["q-1"]}], retriever, config,
        expander=expander, reranker=reranker,
    )

    assert [report.experiment for report in reports] == ["dense", "reranker", "multi_query", "combined"]
    assert retriever.calls == [
        ("q", 1), ("q", 2), ("q", 2), ("q-expanded", 2),
        ("q", 2), ("q-expanded", 2),
    ]
    assert expander.calls == ["q", "q"]
    assert len(reranker.calls) == 2
