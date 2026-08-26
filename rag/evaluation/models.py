"""Small, serializable models shared by evaluation modules."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    relevant_chunk_ids: tuple[str, ...] = ()
    reference_answer: str = ""
    reference_contexts: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "EvaluationCase":
        return cls(
            query=str(value["query"]),
            relevant_chunk_ids=tuple(value.get("relevant_chunk_ids", ())),
            reference_answer=str(value.get("reference_answer", "")),
            reference_contexts=tuple(value.get("reference_contexts", ())),
        )


@dataclass(frozen=True)
class EvaluationReport:
    experiment: str
    corpus_version: str = "policy-eval-set-v1"
    metrics: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
