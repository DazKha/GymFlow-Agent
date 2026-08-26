from __future__ import annotations

from dataclasses import replace

from rag.core.retriever import PolicySearchResult
from rag.research.benchmark import run_variant
from rag.research.query_expansion import ExpansionResult
from rag.research.retrieval_config import RetrievalConfig, experiment_configs


def result(chunk_id: str, query: str) -> PolicySearchResult:
    return PolicySearchResult(
        chunk_id=chunk_id, content=f"{query}:{chunk_id}", document_id="doc",
        document_title="title", section_path=[], clause_ids=[], source_url="",
    )


class FakeRetriever:
    def __init__(self):
        self.queries = []

    def search(self, query: str, top_k: int = 5) -> list[PolicySearchResult]:
        self.queries.append((query, top_k))
        return [result(f"{query}-a", query), result(f"{query}-b", query)]


class FakeExpander:
    def __init__(self):
        self.queries = []

    def expand(self, query: str) -> ExpansionResult:
        self.queries.append(query)
        return ExpansionResult([query, f"{query}-expanded"])


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query: str, results: list[PolicySearchResult], top_k: int | None = None):
        self.calls.append((query, results, top_k))
        return list(reversed(results))


def test_run_variant_composes_each_retrieval_strategy():
    for config in experiment_configs():
        retriever, expander, reranker = FakeRetriever(), FakeExpander(), FakeReranker()
        results = run_variant("q", replace(config, candidate_pool_size=2, final_top_k=1),
                              retriever, expander, reranker)

        assert results
        if config.name == "dense":
            assert retriever.queries == [("q", 1)]
            assert not expander.queries and not reranker.calls
        elif config.name == "reranker":
            assert retriever.queries == [("q", 2)]
            assert not expander.queries and len(reranker.calls) == 1
        elif config.name == "multi_query":
            assert len(retriever.queries) == 2
            assert expander.queries == ["q"]
            assert not reranker.calls
        else:
            assert len(retriever.queries) == 2
            assert expander.queries == ["q"]
            assert len(reranker.calls) == 1
