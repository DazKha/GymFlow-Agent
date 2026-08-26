"""Explicit, deterministic retrieval evaluation orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter

from rag.research.benchmark import run_variant
from rag.research.retrieval_config import RetrievalConfig

from .metrics import mean_reciprocal_rank, precision_at_k, recall_at_k
from .models import EvaluationCase, EvaluationReport


def _case(value: EvaluationCase | dict) -> EvaluationCase:
    return value if isinstance(value, EvaluationCase) else EvaluationCase.from_mapping(value)


def evaluate_retrieval(
    cases: Iterable[EvaluationCase | dict],
    retriever: object,
    configuration: RetrievalConfig,
) -> EvaluationReport:
    """Evaluate one explicit retrieval configuration using an injected retriever."""
    configuration.validate()
    normalized = [_case(value) for value in cases]
    start = perf_counter()
    rankings = [
        [result.chunk_id for result in run_variant(case.query, configuration, retriever=retriever)]
        for case in normalized
    ]
    elapsed = (perf_counter() - start) * 1000
    k = configuration.final_top_k
    relevant = [case.relevant_chunk_ids for case in normalized]
    reciprocal_ranks = [
        mean_reciprocal_rank([ranking], ids) for ranking, ids in zip(rankings, relevant)
    ]
    return EvaluationReport(
        experiment=configuration.name,
        metrics={
            f"precision_at_{k}": sum(precision_at_k(ranking, ids, k) for ranking, ids in zip(rankings, relevant)) / len(rankings) if rankings else 0.0,
            f"recall_at_{k}": sum(recall_at_k(ranking, ids, k) for ranking, ids in zip(rankings, relevant)) / len(rankings) if rankings else 0.0,
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        },
        latency_ms=elapsed / len(normalized) if normalized else 0.0,
    )


def compare_retrieval_variants(cases, retriever, configurations):
    """Compare any explicitly supplied dense/research configurations."""
    return [evaluate_retrieval(cases, retriever, configuration) for configuration in configurations]
