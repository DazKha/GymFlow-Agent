import sys
import types

from rag.research.reranker import Reranker
from rag.research.reranker import CrossEncoderReranker


def test_reranker_keeps_full_pool_and_stable_ties():
    results = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    reranker = Reranker(scorer=lambda query, item: {"a": 1.0, "b": 2.0, "c": 2.0}[item["id"]])

    ranked = reranker.rerank("query", results, top_k=1)

    assert [item["id"] for item in ranked] == ["b", "c", "a"]


def test_cross_encoder_loads_lazily_and_passes_batch_size(monkeypatch):
    calls = []

    class FakeCrossEncoder:
        def __init__(self, name, device):
            calls.append(("construct", name, device))

        def predict(self, pairs, batch_size):
            calls.append(("predict", pairs, batch_size))
            return [1.0]

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=FakeCrossEncoder))
    reranker = CrossEncoderReranker("model", batch_size=7, device="cpu")
    assert calls == []

    reranker.rerank("q", [{"content": "text"}])

    assert calls == [("construct", "model", "cpu"), ("predict", [["q", "text"]], 7)]
