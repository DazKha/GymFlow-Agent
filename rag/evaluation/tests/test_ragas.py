from pathlib import Path
import sys

import pytest

from rag.evaluation.ragas_validation import DEFAULT_RESULT_PATHS, main, run_ragas_validation, select_result_paths


def test_ragas_defaults_select_only_dense_and_documented_best_configuration():
    assert select_result_paths() == tuple(Path(path) for path in DEFAULT_RESULT_PATHS)
    assert len(select_result_paths(["custom.jsonl"])) == 1
    assert select_result_paths([]) == ()


def test_ragas_execution_converts_selected_rows_to_ragas_dataset(tmp_path):
    first = tmp_path / "dense.jsonl"
    second = tmp_path / "best.jsonl"
    first.write_text('{"user_input":"q1","retrieved_contexts":["a"]}\n', encoding="utf-8")
    second.write_text('{"user_input":"q2","retrieved_contexts":["b"]}\n', encoding="utf-8")
    captured = {}

    def fake_evaluate(dataset):
        captured["dataset"] = dataset
        return "result"

    result = run_ragas_validation([str(first), str(second)], evaluator=fake_evaluate)

    assert result == "result"
    assert captured["dataset"].to_list() == [
        {"user_input": "q1", "retrieved_contexts": ["a"]},
        {"user_input": "q2", "retrieved_contexts": ["b"]},
    ]


def test_injected_evaluator_does_not_import_ragas(tmp_path, monkeypatch):
    result_path = tmp_path / "results.jsonl"
    result_path.write_text('{"user_input":"q","retrieved_contexts":[]}', encoding="utf-8")
    real_import = __import__("builtins").__import__

    def reject_ragas(name, *args, **kwargs):
        if name == "ragas" or name.startswith("ragas."):
            raise AssertionError("injected evaluators must not import Ragas")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", reject_ragas)
    assert run_ragas_validation([str(result_path)], evaluator=lambda dataset: "ok") == "ok"


def test_empty_ragas_selection_passes_empty_dataset_to_mocked_evaluator():
    captured = {}

    def fake_evaluate(dataset):
        captured["dataset"] = dataset
        return "empty-result"

    assert run_ragas_validation([], evaluator=fake_evaluate) == "empty-result"
    assert captured["dataset"].samples == []


def test_ragas_path_selection_does_not_import_ragas():
    sys.modules.pop("ragas", None)
    assert select_result_paths([]) == ()
    assert "ragas" not in sys.modules


def test_ragas_list_does_not_import_or_execute_ragas(monkeypatch, capsys):
    sys.modules.pop("ragas", None)
    monkeypatch.setattr(sys, "argv", ["ragas_validation", "--list"])

    main()

    assert capsys.readouterr().out.splitlines() == list(DEFAULT_RESULT_PATHS)
    assert "ragas" not in sys.modules


def test_ragas_main_reports_missing_default_results_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ragas_validation"])

    with pytest.raises(SystemExit) as raised:
        main()

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert "missing" in captured.err.lower()
    assert "FileNotFoundError" not in captured.err


def test_ragas_main_reports_explicit_missing_result_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ragas_validation", "--result-path", "missing.jsonl"])

    with pytest.raises(SystemExit) as raised:
        main()

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert "missing.jsonl" in captured.err
    assert "FileNotFoundError" not in captured.err
