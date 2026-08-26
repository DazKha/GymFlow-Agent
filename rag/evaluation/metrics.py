"""Deterministic retrieval metrics."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be > 0")
    relevant = set(relevant_ids)
    return sum(item in relevant for item in retrieved_ids[:k]) / k


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be > 0")
    relevant = set(relevant_ids)
    return (sum(item in relevant for item in retrieved_ids[:k]) / len(relevant)) if relevant else 0.0


def mean_reciprocal_rank(rankings: Iterable[Sequence[str]], relevant_ids: Iterable[str]) -> float:
    relevant = set(relevant_ids)
    scores = []
    for ranking in rankings:
        score = 0.0
        for rank, item in enumerate(ranking, 1):
            if item in relevant:
                score = 1.0 / rank
                break
        scores.append(score)
    return sum(scores) / len(scores) if scores else 0.0
