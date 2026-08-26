# Task 3 Report

## Files Changed

- Moved production pipeline behavior from `rag/policy_pipeline.py` to `rag/core/pipeline.py` and removed the old module.
- Recreated the previously committed ingestion CLI as `rag/core/ingest.py`; `rag/ingest_policies.py` was already absent after Task 2.
- Updated `tools/query_gym_policy.py` to import `rag.core.pipeline`.
- Added `rag/core/tests/test_pipeline.py` covering dense-only retrieval, empty queries, empty results, citations, and safe provider failures.
- Added this report.

## Commands

1. `python -m pytest -q rag/core/tests/test_pipeline.py` during the required red phase
   - Exit status: `2`.
   - Output: collection failed because `rag.core.pipeline` was not available.

2. `python -m pytest -q rag/core/tests/test_pipeline.py` after implementation
   - Exit status: `0`.
   - Output: `4 passed in 0.05s`.

3. `python -m pytest -q rag/core/tests/test_pipeline.py rag/core/tests/test_vector_store.py`
   - Exit status: `0`.
   - Output: `19 passed in 1.05s`.

4. `python -m pytest -q rag/core/tests`
   - Exit status: `0`.
   - Output: `59 passed in 3.19s`.

5. `python -m rag.core.ingest --help`
   - Exit status: `0`.
   - Output: ingestion CLI usage and options were displayed.

6. Production source import-boundary AST check for `rag/core/pipeline.py` and `tools/query_gym_policy.py`
   - Exit status: `0`.
   - Output: imports were limited to `rag.core.retriever`, `langchain_gradient`, `langchain_core.tools`, and `rag.core.pipeline` (plus `__future__`/`typing`); no `rag.research` or `rag.evaluation` imports.

7. `python -m compileall -q rag/core/pipeline.py rag/core/ingest.py tools/query_gym_policy.py`
   - Exit status: `0`.
   - Output: no output.

8. `git diff --check`
   - Exit status: `0`.
   - Output: no whitespace errors.

9. Direct runtime import check using `import tools.query_gym_policy`
   - Exit status: `1`.
   - Output: pre-existing `tools/__init__.py` imports missing `tools.get_booking`; this is unrelated to Task 3 and was not changed.

## Self-Review

- `run_policy_rag(query: str) -> str` is the only pipeline entrypoint and performs exactly one dense `PolicyRetriever.search` call for non-empty queries.
- Query expansion, reranking, fusion, and research/evaluation imports were removed from the production pipeline.
- Empty queries and empty retrieval results return deterministic fallbacks without constructing unnecessary dependencies.
- Provider failures are logged with an exception chain and return a concise message without provider details to callers.
- Runtime configuration uses the core vector-store, embedding, retrieval top-k, and LLM settings; forbidden multi-query, reranker, and RRF settings are not read.
- The pre-existing tracked `rag/__pycache__/__init__.cpython-39.pyc` modification was preserved.

## Concerns

- The repository's `tools/__init__.py` currently imports missing `tools.get_booking`, so importing the tool through the package fails before reaching `query_gym_policy`; fixing that unrelated issue was intentionally out of scope.
- `rag/core/ingest.py` was reconstructed from the last committed `rag/ingest_policies.py` because Task 2 had already removed the source file; its vector-store dependency remains lazy so `--help` stays offline.
