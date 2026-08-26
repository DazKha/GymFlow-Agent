# RAG Repository Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete Gym Agent demo GitHub-ready while giving production RAG a small dense-only core and preserving selected retrieval experiments and Ragas evidence.

**Architecture:** Move production RAG code into `rag/core`, keep optional retrieval variants in `rag/research`, and keep metrics/Ragas orchestration in `rag/evaluation`. The agent tool imports only `rag.core.pipeline`; research and evaluation depend on core but are never imported by runtime code.

**Tech Stack:** Python 3.9+, LangGraph, LangChain Core/OpenAI-compatible chat, Chroma, Sentence Transformers, Pydantic, pytest, Ragas.

## Global Constraints

- Production retrieval is dense E5 + Chroma only.
- Multi-query expansion, RRF fusion, and cross-encoder reranking are research-only.
- Ragas is opt-in and runs only for the dense baseline and selected best configuration.
- The default test suite must not download models or call external services.
- The public repository keeps the complete agent/backend demo, policy source documents, evaluation dataset, experiment code, and compact reports.
- Generated chunks, manifests, vector indexes, caches, Python caches, local state, and secrets are not tracked.
- Repository commands use relative paths and must match the final tree.
- Do not revert unrelated existing working-tree changes.

## File Map

Production RAG files:

- Create `rag/core/__init__.py` to expose the production package boundary.
- Move `rag/policy_models.py` to `rag/core/models.py` for chunking models.
- Move `rag/policy_chunker.py` to `rag/core/chunking.py` for document parsing and section-aware chunking.
- Move `rag/policy_vector_store.py` to `rag/core/vector_store.py` for Chroma and embedding providers.
- Move `rag/policy_retriever.py` to `rag/core/retriever.py` for dense search and citations.
- Move `rag/policy_pipeline.py` to `rag/core/pipeline.py` for retrieve-and-generate runtime behavior.
- Move `rag/ingest_policies.py` to `rag/core/ingest.py` for the index build CLI.

Research and evaluation files:

- Move `rag/reranker.py` and `rag/query_expansion.py` to `rag/research/`.
- Move `rag/retrieval_fusion.py` and `rag/benchmark_retrieval.py` to `rag/research/`.
- Keep evaluation implementation under `rag/evaluation/`, grouping dataset loading, models, metrics, reports, generation, and Ragas execution by responsibility.
- Move `rag/tests/` tests into `rag/core/tests/`, `rag/research/tests/`, and `rag/evaluation/tests/` according to the code they exercise.

Repository files:

- Modify `tools/query_gym_policy.py` to import `rag.core.pipeline`.
- Modify `.gitignore`, `README.md`, and `requirements.txt`.
- Create `.env.example`.
- Create `requirements-research.txt` for reranker/benchmark/Ragas-only dependencies.
- Move policy source files into `data/policies/` without changing their content.
- Move normalization scripts from `data/scripts/` to `scripts/`; move explanatory Markdown to `docs/rag/`.
- Store compact evaluation summaries under `docs/evaluation/`; ignore generated run directories.

---

### Task 1: Establish a clean baseline and ignore policy

**Files:**
- Modify: `.gitignore`
- Create: `.env.example`
- Test: no code test; verification uses Git commands and pytest collection

**Interfaces:**
- Produces an ignore policy that excludes local/generated state without hiding source, tests, compact reports, or evaluation data.

- [ ] **Step 1: Record the baseline test command and worktree state**

Run:

```bash
python -m pytest -q
git status --short
```

Save the observed failures and existing modifications in the task notes; do not modify unrelated files.

- [ ] **Step 2: Add explicit ignore rules**

Add rules for `__pycache__/`, `*.py[cod]`, `.langgraph_api/`, `.env`, local SQLite/database files, Chroma persistence directories, `data/generated/`, experiment run outputs, model caches, and notebook checkpoints. Keep `data/policies/`, evaluation datasets, source code, tests, and `docs/evaluation/*.md` trackable.

- [ ] **Step 3: Create the safe environment template**

Create `.env.example` containing variable names only, grouped as:

```dotenv
LLM_API_KEY=
MODEL_NAME=deepseek-v4-flash
OPENAI_BASE_URL=
BACKEND_URL=http://127.0.0.1:8000
CHROMA_PERSIST_DIR=data/generated/chroma
CHROMA_POLICY_COLLECTION=gymflow_policy_e5_v1
POLICY_EMBEDDING_MODEL=intfloat/multilingual-e5-base
POLICY_RETRIEVAL_TOP_K=5
```

- [ ] **Step 4: Verify the ignore boundary**

Run:

```bash
git check-ignore -v .env data/generated/chroma/chroma.sqlite3 rag/evaluation/runs/example/per_case_results.jsonl
git check-ignore -v data/policies/example.md rag/evaluation/policy_eval_set_v1.jsonl
```

Expected: the first command's paths are ignored; source policy and evaluation dataset are not ignored.

- [ ] **Step 5: Commit only hygiene changes**

```bash
git add .gitignore .env.example
git commit -m "chore: define public repository ignore policy"
```

### Task 2: Create and test the production core package

**Files:**
- Create: `rag/core/__init__.py`
- Move: `rag/policy_models.py` to `rag/core/models.py`
- Move: `rag/policy_chunker.py` to `rag/core/chunking.py`
- Move: `rag/policy_vector_store.py` to `rag/core/vector_store.py`
- Move: `rag/policy_retriever.py` to `rag/core/retriever.py`
- Create or move: `rag/core/tests/test_chunking.py`, `rag/core/tests/test_vector_store.py`
- Modify: imports in all moved core modules and core tests

**Interfaces:**
- `rag.core.models.PolicyChunk`, `ChunkingConfig`, and `ChunkReport` retain their current Pydantic fields.
- `rag.core.chunking.parse_document(content: str, filename: str = "") -> dict[str, Any]` retains current behavior.
- `rag.core.vector_store.PolicyVectorStore.search(query: str, top_k: int = 5, where: dict | None = None) -> list[dict]` retains current return shape.
- `rag.core.retriever.PolicyRetriever.search(query: str, top_k: int = 5, document_ids: list[str] | None = None) -> list[PolicySearchResult]` is the runtime retrieval API.

- [ ] **Step 1: Move tests with the code they cover**

Place existing chunker/vector-store tests under `rag/core/tests/` and update imports to `rag.core.*`. Keep test assertions unchanged initially so the move does not silently change behavior.

- [ ] **Step 2: Run the moved tests and verify import failures**

Run:

```bash
python -m pytest -q rag/core/tests
```

Expected: failures identify every stale `rag.*` import or missing package initializer.

- [ ] **Step 3: Move implementation files and update internal imports**

Move the four modules and update imports from `rag.policy_models`, `rag.policy_vector_store`, `rag.policy_retriever`, and related paths to their `rag.core` equivalents. Add `rag/core/__init__.py` without eager imports of optional dependencies.

- [ ] **Step 4: Keep chunking as one focused core module**

Retain parsing, token counting, and chunk creation together in `chunking.py`. Do not split the 772-line implementation unless tests reveal a concrete import or responsibility boundary; the first cleanup goal is package isolation, not speculative fragmentation.

- [ ] **Step 5: Run core tests**

Run:

```bash
python -m pytest -q rag/core/tests
```

Expected: all moved core tests pass without network access or model downloads.

- [ ] **Step 6: Commit the core package move**

```bash
git add rag/core rag/policy_models.py rag/policy_chunker.py rag/policy_vector_store.py rag/policy_retriever.py
git commit -m "refactor: isolate production RAG core"
```

### Task 3: Make production pipeline dense-only

**Files:**
- Move: `rag/policy_pipeline.py` to `rag/core/pipeline.py`
- Move: `rag/ingest_policies.py` to `rag/core/ingest.py`
- Modify: `tools/query_gym_policy.py`
- Create: `rag/core/tests/test_pipeline.py`
- Modify: `rag/core/retriever.py` if dense API cleanup is needed

**Interfaces:**
- `rag.core.pipeline.run_policy_rag(query: str) -> str` is the only production RAG entrypoint.
- `tools.query_gym_policy` calls `run_policy_rag` and does not import research or evaluation modules.
- `rag.core.ingest.main()` remains executable with `python -m rag.core.ingest`.

- [ ] **Step 1: Write dense-only pipeline tests**

Add tests that patch `PolicyRetriever.search`, `_get_llm`, and the LLM response. Assert that a normal query calls only `search`, builds citation context, and returns the provider content; assert that an empty query returns the deterministic fallback without constructing the retriever or LLM; assert that an empty result returns the no-document fallback without invoking the LLM.

- [ ] **Step 2: Run the new tests to confirm they fail against the old boundary**

Run:

```bash
python -m pytest -q rag/core/tests/test_pipeline.py
```

Expected: import failures or assertions show the old module path and optional retrieval branch must be removed.

- [ ] **Step 3: Move pipeline and ingestion entrypoints**

Move the files, change imports to `rag.core.*`, and remove `RetrievalConfig` branching from the production pipeline. Use one `PolicyRetriever.search(query, top_k=...)` call for every non-empty query.

- [ ] **Step 4: Keep only runtime configuration**

Read vector-store, embedding, retrieval top-k, and LLM settings in core. Do not read `POLICY_MULTI_QUERY_*`, `POLICY_RERANKER_*`, or `POLICY_RRF_K` from the production path.

- [ ] **Step 5: Make failures controlled**

Catch vector-store/embedding/LLM provider failures at the pipeline boundary and return a concise user-safe message. Preserve the original exception as a chained cause for logs/tests; do not expose API keys or stack traces in tool output.

- [ ] **Step 6: Update the tool import and run focused tests**

Run:

```bash
python -m pytest -q rag/core/tests/test_pipeline.py rag/core/tests/test_vector_store.py
```

Expected: PASS, with no imports from `rag.research` or `rag.evaluation` in the production import graph.

- [ ] **Step 7: Commit the dense runtime**

```bash
git add rag/core tools/query_gym_policy.py
git commit -m "refactor: simplify policy RAG runtime to dense search"
```

### Task 4: Isolate research variants and preserve experiment coverage

**Files:**
- Create: `rag/research/__init__.py`
- Move: `rag/reranker.py` to `rag/research/reranker.py`
- Move: `rag/query_expansion.py` to `rag/research/query_expansion.py`
- Move: `rag/retrieval_fusion.py` to `rag/research/retrieval_fusion.py`
- Move: `rag/benchmark_retrieval.py` to `rag/research/benchmark.py`
- Move: `rag/retrieval_config.py` to `rag/research/retrieval_config.py`
- Move: related tests to `rag/research/tests/`
- Modify: research imports to use `rag.core.retriever` and `rag.research.*`

**Interfaces:**
- `rag.research.retrieval_config.RetrievalConfig` remains the experiment configuration object.
- `rag.research.query_expansion.LLMQueryExpander` and `CachedQueryExpander` retain current expansion APIs.
- `rag.research.retrieval_fusion.fuse_ranked_results(...)` retains deterministic RRF ordering.
- `rag.research.reranker.Reranker.rerank(...)` retains full-pool stable ordering for benchmark metrics.
- `rag.research.benchmark.main()` runs the four retrieval configurations without being imported by runtime code.

- [ ] **Step 1: Move and relink research tests**

Move enhancement, reranker smoke, and fusion tests under `rag/research/tests/`; update imports and mark real-model tests with the existing opt-in marker.

- [ ] **Step 2: Run research tests before implementation changes**

Run:

```bash
python -m pytest -q rag/research/tests -m "not real_model"
```

Expected: failures list stale module imports only.

- [ ] **Step 3: Move research modules and update imports**

Move the five modules, make them import `PolicySearchResult` and dense retrieval only from `rag.core`, and ensure `rag/core` never imports them.

- [ ] **Step 4: Verify all experiment variants remain available**

Run:

```bash
python -m rag.research.benchmark --help
python -m pytest -q rag/research/tests -m "not real_model"
```

Expected: the CLI help lists the benchmark options and all non-network research tests pass.

- [ ] **Step 5: Commit the research boundary**

```bash
git add rag/research rag/core
git commit -m "refactor: isolate retrieval research variants"
```

### Task 5: Simplify evaluation and selective Ragas validation

**Files:**
- Modify: `rag/evaluation/` modules and imports
- Move: evaluation tests into `rag/evaluation/tests/`
- Modify: `rag/evaluate_policy_rag.py`
- Move: `rag/evaluate_ragas_comparison.py` to `rag/evaluation/ragas_validation.py`
- Create: `docs/evaluation/retrieval-experiments.md`
- Create: `docs/evaluation/ragas-validation.md`

**Interfaces:**
- Evaluation remains callable without importing production pipeline code into the agent.
- Retrieval evaluation accepts an explicit retriever/configuration and can compare dense, reranker, multi-query, and combined variants.
- Ragas validation accepts an explicit list of selected experiment result files and never requires all four combinations.

- [ ] **Step 1: Move evaluation tests and run them**

Move dataset, metrics, citation, and evaluation-pipeline tests under `rag/evaluation/tests/` and run:

```bash
python -m pytest -q rag/evaluation/tests
```

Expected: only import paths fail after the move; no real provider calls occur.

- [ ] **Step 2: Update evaluation imports and command paths**

Change evaluation imports to `rag.core`, `rag.research`, and local `rag.evaluation` modules. Keep the existing deterministic retrieval and generation modes, but make the selected retrieval configuration explicit rather than relying on production environment flags.

- [ ] **Step 3: Limit Ragas selection**

Add CLI arguments to the Ragas validation entrypoint for selected result paths, defaulting to the dense baseline and the documented best configuration. Do not enqueue or generate Ragas results for dense+rereanker, multi-query, and combined variants unless explicitly selected.

- [ ] **Step 4: Keep compact reports and remove bulky defaults**

Document experiment names, corpus version, retrieval metrics, latency, and the selected Ragas results in Markdown. Do not commit per-case JSONL, query-expansion caches, or model-generated responses.

- [ ] **Step 5: Run evaluation tests without Ragas/network**

Run:

```bash
python -m pytest -q rag/evaluation/tests -m "not real_model"
```

Expected: PASS without downloading models or contacting an LLM provider.

- [ ] **Step 6: Commit evaluation boundary**

```bash
git add rag/evaluation docs/evaluation
git commit -m "refactor: keep evaluation and Ragas opt-in"
```

### Task 6: Normalize source data, dependencies, and documentation

**Files:**
- Move: policy Markdown sources into `data/policies/`
- Move: `data/scripts/normalize_policies.py` to `scripts/normalize_policies.py`
- Move: `data/scripts/validate_normalized.py` to `scripts/validate_policies.py`
- Move or consolidate: `data/scripts/*.md` into `docs/rag/`
- Modify: `README.md`
- Modify: `requirements.txt` and `backend/backend/requirements.txt` only where required by the final imports
- Create: `requirements-research.txt` if research/evaluation dependencies cannot stay optional

**Interfaces:**
- `python scripts/normalize_policies.py` and `python scripts/validate_policies.py` use repository-relative defaults.
- README quickstart documents backend startup, policy normalization/chunking/ingestion, and `langgraph dev`.
- README documents dense runtime separately from research benchmark and opt-in Ragas commands.

- [ ] **Step 1: Move canonical policy sources**

Move policy documents into `data/policies/` and update every default path in chunking, evaluation, scripts, and README. Preserve front matter and document IDs.

- [ ] **Step 2: Move and simplify preparation scripts**

Move normalization/validation scripts to `scripts/`, replace absolute paths with `Path` values relative to the repository root, and keep their current validation behavior.

- [ ] **Step 3: Separate dependency groups**

Keep runtime dependencies in `requirements.txt`; put reranker, benchmark, and Ragas-only dependencies in `requirements-research.txt` if they are not needed by the agent/backend. Ensure a clean runtime install does not import Ragas during normal startup.

- [ ] **Step 4: Rewrite README around verified flows**

Replace stale tool names, old notebook references, absolute backend paths, and references to `rag/policy_pipeline.py`. Add a short architecture diagram, dense-only runtime explanation, chunking/index rebuild commands, research variant commands, Ragas selection policy, environment setup, and test commands.

- [ ] **Step 5: Verify documentation commands**

Run each local command documented in README with `--help` or dry-run where it would download a model or start a long-running service. Fix any path or module mismatch before continuing.

- [ ] **Step 6: Commit public-facing cleanup**

```bash
git add data/policies scripts docs/rag README.md requirements.txt requirements-research.txt
git commit -m "docs: publish reproducible RAG workflows"
```

### Task 7: Remove generated artifacts and run the complete verification suite

**Files:**
- Delete from tracking: `__pycache__/`, `.langgraph_api/`, Chroma persistence files, `data/generated/`, bulky run artifacts, `rag/archive/`, obsolete notebooks
- Modify: `.gitignore` if any generated path remains visible
- Test: all `rag/**/tests/`

**Interfaces:**
- A clean clone can rebuild generated RAG outputs from tracked source and documented commands.
- The default test command succeeds without external services.

- [ ] **Step 1: Identify generated files before removal**

Run:

```bash
git ls-files | rg '(__pycache__|\.pyc$|\.langgraph_api|chroma|data/generated|rag/archive|\.ipynb$)'
```

Review the result and remove only generated/obsolete files covered by the approved scope; retain any explicitly documented source notebook only if no CLI replacement exists.

- [ ] **Step 2: Remove generated files and stale compatibility paths**

Delete tracked caches, local indexes, archive code, and obsolete notebooks. Remove old top-level RAG modules only after all imports and documentation use the new paths.

- [ ] **Step 3: Run static import checks**

Run:

```bash
python -c "import agent.graph; import tools.query_gym_policy; import rag.core.pipeline"
python -c "import rag.core.pipeline; import sys; assert not any(name.startswith('rag.research') for name in sys.modules)"
```

Expected: imports succeed and importing production pipeline does not load research modules.

- [ ] **Step 4: Run the default test suite**

Run:

```bash
python -m pytest -q -m "not real_model"
```

Expected: all default tests pass without network/model download.

- [ ] **Step 5: Run opt-in command validation**

Run:

```bash
python -m rag.core.chunking --help
python -m rag.core.ingest --help
python -m rag.research.benchmark --help
python -m rag.evaluate_policy_rag --help
```

Expected: all commands exit successfully and show repository-relative defaults.

- [ ] **Step 6: Inspect the final public diff**

Run:

```bash
git status --short
git diff --stat
git ls-files | rg '(^|/)(\.env|.*\.sqlite3|.*\.pyc|__pycache__|data/generated|\.langgraph_api)'
```

Expected: no secrets or generated runtime files are tracked; any pre-existing unrelated worktree changes remain untouched.

- [ ] **Step 7: Commit final verification changes**

```bash
git add .gitignore README.md requirements.txt requirements-research.txt .env.example scripts data/policies docs/rag docs/evaluation rag/core rag/research rag/evaluation tools/query_gym_policy.py
git commit -m "chore: finalize GitHub-ready repository"
```

Before staging, inspect `git diff --name-only` and remove any path that was
changed by the user or another task rather than this plan. Never use `git add .`
for the final commit.

## Completion Checklist

- [ ] Production imports only `rag.core.pipeline` for policy RAG.
- [ ] Production retrieval is dense-only.
- [ ] Chunking and ingestion are documented core build steps.
- [ ] Dense, reranker, multi-query, and combined experiments remain runnable.
- [ ] Ragas is retained for selected configurations only and is opt-in.
- [ ] Default tests pass without external services.
- [ ] README commands were verified against the final tree.
- [ ] Secrets, caches, indexes, and generated artifacts are not tracked.
