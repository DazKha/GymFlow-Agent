# Task 4 Report

## Files Changed

- Added `rag/research/__init__.py` as the optional research package boundary.
- Added `rag/research/retrieval_config.py` with the `RetrievalConfig` interface and four variants: dense, reranker, multi-query, and combined.
- Added `rag/research/query_expansion.py` with `LLMQueryExpander`, `CachedQueryExpander`, and expansion result metadata. LLM construction remains lazy.
- Added `rag/research/retrieval_fusion.py` with deterministic reciprocal-rank fusion and stable tie ordering.
- Added `rag/research/reranker.py` with stable full-pool `Reranker.rerank(...)` ordering and lazy `CrossEncoderReranker` model loading.
- Added `rag/research/benchmark.py` with an offline-safe CLI exposing all four configurations.
- Added research tests under `rag/research/tests/` for cache behavior, fusion ordering, and stable full-pool reranking.
- Added this report. The progress ledger was not modified.

## Commands

1. `python -m pytest -q rag/research/tests -m "not real_model"` before implementation
   - Exit status: `1`.
   - Output: collection failed with stale top-level imports: `rag.query_expansion`, `rag.reranker`, and `rag.retrieval_fusion` were not present.

2. `python -m pytest -q rag/research/tests/test_reranker.py` after adding the full-pool assertion and before its fix
   - Exit status: `1`.
   - Output: expected red regression; `top_k=1` returned only `['b']` instead of the complete stable order `['b', 'c', 'a']`.

3. `python -m pytest -q rag/research/tests -m "not real_model"`
   - Exit status: `0`.
   - Output: `3 passed in 0.01s`.

4. `python -m rag.research.benchmark --help`
   - Exit status: `0`.
   - Output: help lists `--config {dense,reranker,multi_query,combined}` and query/top-k options.

5. `python -m pytest -q rag/core/tests`
   - Exit status: `0`.
   - Output: `62 passed in 3.81s`.

6. `python -m compileall -q rag/research`
   - Exit status: `0`.
   - Output: no output.

7. Core import-boundary AST check over `rag/core/{pipeline,retriever,vector_store,ingest}.py`
   - Exit status: `0`.
   - Output: `core import boundary: no rag.research imports`.

8. `git diff --check`
   - Exit status: `0`.
   - Output: no whitespace errors.

## Self-Review

- Research code is isolated under `rag/research`; no core module imports it.
- `RetrievalConfig` validates experiment parameters and exposes all four named variants.
- Fusion deduplicates by result identifier, uses deterministic RRF scores, and preserves first-seen order for ties.
- Reranking sorts the complete candidate pool stably, allowing benchmark code to slice after ranking.
- Optional OpenAI and sentence-transformer dependencies are imported only when their implementations are used.
- The benchmark help path does not construct a vector store, LLM, or reranker model.
- Existing unrelated worktree changes were preserved; at the time of implementation the worktree was clean.

## Concerns

- The checkout at Task 4 start did not contain the five historical top-level research modules or their related tests, so there were no literal files to move. The research tests and implementations were recreated from the Task 4 interfaces and available cleanup history rather than relocated from existing source.
- Because the prior dense-only Task 3 retriever intentionally removed `search_with_trace`, `benchmark.py` keeps its default and help paths offline and currently enumerates configurations; running a real query currently performs the core dense search for each selected configuration rather than composing expansion, fusion, and reranking. The optional components are independently available for a future benchmark orchestration task.
- Real-model smoke tests were not run, consistent with the required `not real_model` command and offline default-suite policy.

## Review Fix Report

### Findings Addressed

- Replaced label-only benchmark execution with `run_variant(...)` composition: dense search, optional expansion per variant, deterministic fusion, and optional reranking.
- Added fake-driven coverage proving each of the four configurations invokes only its intended components.
- Made `CrossEncoderReranker` lazy; construction no longer imports or constructs `CrossEncoder`, which happens on the first scoring call.
- Passed configured `batch_size` to `CrossEncoder.predict(...)`.
- Added typed benchmark protocols for core-compatible retrievers, query expanders, and rerankers, with explicit `PolicySearchResult` lists.
- Validated every configuration returned by `experiment_configs()` and every configuration accepted by `run_variant(...)`.

### Fix Verification

1. `python -m pytest -q rag/research/tests/test_benchmark.py`
   - Exit status: `0`.
   - Output: `1 passed in 0.05s`.

2. `python -m pytest -q rag/research/tests/test_reranker.py`
   - Exit status: `0`.
   - Output: `2 passed in 0.01s`.

3. `python -m pytest -q rag/research/tests -m "not real_model"`
   - Exit status: `0`.
   - Output: `5 passed in 0.05s`.

4. `python -m pytest -q rag/core/tests`
   - Exit status: `0`.
   - Output: `62 passed in 3.77s`.

5. `python -m rag.research.benchmark --help`
   - Exit status: `0`.
   - Output: help listed `--config {dense,reranker,multi_query,combined}` and stated that omitting config runs all variants.

6. `git diff --check`
   - Exit status: `0`.
   - Output: no whitespace errors.

### Remaining Concerns

- Real reranker and LLM execution remains opt-in and was not run; required tests use deterministic fakes and no network/model downloads.
- A real benchmark query requires the configured vector store and optional model/provider dependencies by design; `--help` remains free of those side effects.
