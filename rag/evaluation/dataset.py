"""Evaluation dataset loading and validation without external dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import EvaluationCase


def validate_evaluation_dataset(cases: Iterable[EvaluationCase]) -> list[EvaluationCase]:
    validated = list(cases)
    for index, case in enumerate(validated, 1):
        if not case.query.strip():
            raise ValueError(f"case {index} query must be non-empty")
        if len(set(case.relevant_chunk_ids)) != len(case.relevant_chunk_ids):
            raise ValueError(f"case {index} contains duplicate relevant_chunk_ids")
    return validated


def load_evaluation_dataset(path: str | Path) -> list[EvaluationCase]:
    cases = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            cases.append(EvaluationCase.from_mapping(json.loads(line)))
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid evaluation case on line {line_number}") from error
    return validate_evaluation_dataset(cases)
