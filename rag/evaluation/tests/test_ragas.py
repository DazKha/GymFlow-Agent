from pathlib import Path

from rag.evaluation.ragas_validation import DEFAULT_RESULT_PATHS, select_result_paths


def test_ragas_defaults_select_only_dense_and_documented_best_configuration():
    assert select_result_paths() == tuple(Path(path) for path in DEFAULT_RESULT_PATHS)
    assert len(select_result_paths(["custom.jsonl"])) == 1
