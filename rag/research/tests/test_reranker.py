from rag.research.reranker import Reranker


def test_reranker_keeps_full_pool_and_stable_ties():
    results = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    reranker = Reranker(scorer=lambda query, item: {"a": 1.0, "b": 2.0, "c": 2.0}[item["id"]])

    ranked = reranker.rerank("query", results, top_k=1)

    assert [item["id"] for item in ranked] == ["b", "c", "a"]
