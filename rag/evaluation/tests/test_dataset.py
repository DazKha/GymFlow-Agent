from pathlib import Path

from rag.evaluation.dataset import load_evaluation_dataset


def test_load_evaluation_dataset_reads_jsonl_cases(tmp_path: Path):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        '{"query":"How do I pay?","relevant_chunk_ids":["payment-1"]}\n',
        encoding="utf-8",
    )

    cases = load_evaluation_dataset(path)

    assert len(cases) == 1
    assert cases[0].query == "How do I pay?"
    assert cases[0].relevant_chunk_ids == ("payment-1",)
