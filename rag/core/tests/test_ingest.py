from __future__ import annotations

import sys

import pytest

from rag.core import ingest


def test_main_exits_nonzero_for_blocked_ingestion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["ingest", "--input", "chunks.jsonl"])
    monkeypatch.setattr(ingest, "ingest", lambda *args: {"status": "blocked"})

    with pytest.raises(SystemExit) as raised:
        ingest.main()

    assert raised.value.code != 0
