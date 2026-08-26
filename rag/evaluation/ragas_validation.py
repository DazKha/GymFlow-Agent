"""Opt-in Ragas validation for selected result files only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Iterable

DEFAULT_RESULT_PATHS = (
    "rag/evaluation/runs/dense/results.jsonl",
    "rag/evaluation/runs/combined/results.jsonl",
)


def select_result_paths(paths: Iterable[str] | None = None) -> tuple[Path, ...]:
    return tuple(Path(path) for path in (DEFAULT_RESULT_PATHS if paths is None else paths))


def run_ragas_validation(paths: Iterable[str] | None = None, evaluator: Callable | None = None):
    """Run Ragas only for the selected files; importing Ragas is deliberately lazy."""
    selected = select_result_paths(paths)
    rows = [json.loads(line) for path in selected for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    from ragas.dataset_schema import EvaluationDataset  # noqa: PLC0415

    dataset = EvaluationDataset.from_list(rows) if rows else EvaluationDataset(samples=[])
    if evaluator is not None:
        return evaluator(dataset)
    from ragas import evaluate  # noqa: PLC0415

    return evaluate(dataset)


def main() -> None:
    parser = argparse.ArgumentParser(description="Opt-in Ragas validation for selected result files")
    parser.add_argument("--result-path", action="append", nargs="?", const=None,
                        dest="result_paths", metavar="PATH",
                        help="Result JSONL path; repeat to select multiple files")
    parser.add_argument("--list", action="store_true", help="Print selected paths without running Ragas")
    args = parser.parse_args()
    supplied_paths = args.result_paths is not None
    selected = select_result_paths(
        [path for path in args.result_paths if path is not None] if supplied_paths else None
    )
    if args.list:
        for path in selected:
            print(path)
        return
    run_ragas_validation(selected)


if __name__ == "__main__":
    main()
