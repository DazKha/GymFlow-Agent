"""Optional cross-encoder reranking for research benchmarks."""

from __future__ import annotations

from typing import Any, Callable


class Reranker:
    def __init__(self, scorer: Callable[[str, Any], float] | None = None, model: Any = None,
                 batch_size: int = 16) -> None:
        self.scorer = scorer
        self.model = model
        self.batch_size = batch_size

    def rerank(self, query: str, results: list[Any], top_k: int | None = None) -> list[Any]:
        if self.scorer is not None:
            scored = [(self.scorer(query, item), index, item) for index, item in enumerate(results)]
        elif self.model is not None:
            pairs = [[query, item.content if hasattr(item, "content") else item.get("content", "")] for item in results]
            scored = [(score, index, item) for index, (score, item) in enumerate(
                zip(self.model.predict(pairs, batch_size=self.batch_size), results))]
        else:
            raise RuntimeError("A reranker scorer or model is required")
        # Keep the complete sorted pool; benchmark callers slice after metrics
        # can inspect the reranker ordering.
        return [item for _, _, item in sorted(scored, key=lambda value: (-value[0], value[1]))]


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str, batch_size: int = 16, device: str = "cpu") -> None:
        super().__init__(batch_size=batch_size)
        self.model_name = model_name
        self.device = device

    def _load_model(self) -> Any:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(self.model_name, device=self.device)

    def rerank(self, query: str, results: list[Any], top_k: int | None = None) -> list[Any]:
        if self.model is None:
            self.model = self._load_model()
        return super().rerank(query, results, top_k)
