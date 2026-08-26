"""Configuration for reproducible retrieval experiments."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalConfig:
    name: str = "dense"
    multi_query_enabled: bool = False
    reranker_enabled: bool = False
    query_variant_count: int = 3
    candidate_pool_size: int = 20
    final_top_k: int = 5
    rrf_k: int = 60
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    reranker_batch_size: int = 16
    reranker_device: str = "cpu"

    def validate(self) -> None:
        if self.query_variant_count < 1:
            raise ValueError("query_variant_count must be > 0")
        if self.candidate_pool_size < 1 or self.final_top_k < 1:
            raise ValueError("candidate_pool_size and final_top_k must be > 0")
        if self.final_top_k > self.candidate_pool_size:
            raise ValueError("final_top_k cannot exceed candidate_pool_size")
        if self.rrf_k < 1 or self.reranker_batch_size < 1:
            raise ValueError("rrf_k and reranker_batch_size must be > 0")


def experiment_configs() -> tuple[RetrievalConfig, ...]:
    """Return the dense, reranker, multi-query, and combined variants."""
    return (
        RetrievalConfig(name="dense"),
        RetrievalConfig(name="reranker", reranker_enabled=True),
        RetrievalConfig(name="multi_query", multi_query_enabled=True),
        RetrievalConfig(name="combined", multi_query_enabled=True, reranker_enabled=True),
    )
