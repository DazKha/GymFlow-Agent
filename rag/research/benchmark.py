"""Command-line entry point for the four retrieval experiments."""

from __future__ import annotations

import argparse
from typing import Protocol

from rag.core.retriever import PolicySearchResult, PolicyRetriever

from .query_expansion import ExpansionResult, LLMQueryExpander
from .reranker import CrossEncoderReranker, Reranker
from .retrieval_config import RetrievalConfig, experiment_configs
from .retrieval_fusion import fuse_ranked_results


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[PolicySearchResult]: ...


class Expander(Protocol):
    def expand(self, query: str) -> ExpansionResult: ...


class ResultReranker(Protocol):
    def rerank(self, query: str, results: list[PolicySearchResult],
               top_k: int | None = None) -> list[PolicySearchResult]: ...


def run_variant(
    query: str,
    config: RetrievalConfig,
    retriever: Retriever | None = None,
    expander: Expander | None = None,
    reranker: ResultReranker | None = None,
) -> list[PolicySearchResult]:
    """Run one configured experiment with injectable offline-test dependencies."""
    config.validate()
    retriever = retriever or PolicyRetriever()
    if config.multi_query_enabled:
        expander = expander or LLMQueryExpander(config.query_variant_count)
        variants = expander.expand(query).queries
    else:
        variants = [query]

    if config.multi_query_enabled:
        ranked_lists = [retriever.search(variant, config.candidate_pool_size) for variant in variants]
        results = fuse_ranked_results(ranked_lists, config.candidate_pool_size, config.rrf_k)
    else:
        pool_size = config.candidate_pool_size if config.reranker_enabled else config.final_top_k
        results = retriever.search(query, pool_size)

    if config.reranker_enabled:
        reranker = reranker or CrossEncoderReranker(
            config.reranker_model_name, config.reranker_batch_size, config.reranker_device)
        results = reranker.rerank(query, results)
    return results[:config.final_top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark dense and optional retrieval variants")
    parser.add_argument("--config", choices=[config.name for config in experiment_configs()],
                        help="Run one variant; omit to run all variants")
    parser.add_argument("--query", help="Benchmark query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    configs = experiment_configs()
    selected = [config for config in configs if not args.config or config.name == args.config]
    if not args.query:
        for config in selected:
            print(config.name)
        return
    for config in selected:
        results = run_variant(args.query, RetrievalConfig(
            name=config.name,
            multi_query_enabled=config.multi_query_enabled,
            reranker_enabled=config.reranker_enabled,
            query_variant_count=config.query_variant_count,
            candidate_pool_size=max(config.candidate_pool_size, args.top_k),
            final_top_k=args.top_k,
            rrf_k=config.rrf_k,
            reranker_model_name=config.reranker_model_name,
            reranker_batch_size=config.reranker_batch_size,
            reranker_device=config.reranker_device,
        ))
        print(f"{config.name}: {len(results)} results")


if __name__ == "__main__":
    main()
