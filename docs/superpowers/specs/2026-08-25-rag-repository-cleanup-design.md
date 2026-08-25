# RAG Repository Cleanup Design

## Goal

Polish the Gym Agent repository for public GitHub use while keeping the complete
demo, selected RAG experiments, and useful Ragas evidence. The production path
must be easy to understand and use dense retrieval only.

## Scope

Included:

- RAG runtime, policy ingestion, and chunking organization.
- Retrieval experiments for dense, reranker, multi-query, and combined variants.
- Ragas validation for the dense baseline and selected best configuration.
- Repository hygiene, documentation, dependencies, and tests.
- Existing agent, tools, backend, and guardrails demo behavior.

Excluded:

- Adding a new retrieval algorithm.
- Enabling multi-query or reranking in the production path.
- Running Ragas for every retrieval combination.
- Unrelated product features or backend redesign.

## Package Boundaries

The RAG package will have three explicit areas:

```text
rag/
  core/
    chunking.py
    models.py
    vector_store.py
    retriever.py
    pipeline.py
    ingest.py
  evaluation/
    dataset.py
    models.py
    metrics.py
    reports.py
    pipeline.py
    ragas.py
  research/
    reranker.py
    query_expansion.py
    retrieval_fusion.py
    benchmark.py
  tests/
```

`rag/core` owns production retrieval and build-time corpus preparation.
Chunking belongs here because it transforms canonical policy documents into the
indexable corpus. The current `policy_chunker.py` maps to `core/chunking.py`,
`policy_models.py` to `core/models.py`, `policy_vector_store.py` to
`core/vector_store.py`, and `ingest_policies.py` to `core/ingest.py`.

`rag/research` contains optional retrieval improvements and must only depend on
core interfaces. `rag/evaluation` measures behavior and must not be imported by
runtime code. The production tool will import only `rag.core.pipeline`.

The existing top-level `agent/`, `tools/`, `backend/`, and `guardrails/`
boundaries remain in place.

## Production Data Flow

```text
query_gym_policy(query)
  -> rag.core.pipeline.run(query)
  -> rag.core.retriever.search(query, top_k=5)
  -> cited context construction
  -> Vietnamese LLM response
```

Production behavior:

- Dense E5 retrieval with Chroma is the only retrieval strategy.
- Multi-query expansion, RRF fusion, and cross-encoder reranking are not loaded.
- Runtime configuration is limited to vector-store, embedding, retrieval top-k,
  and LLM settings.
- Citation metadata includes document, section, clause, and source URL when
  available.
- Empty queries and no-result searches return deterministic fallback messages.
- Provider and model failures return controlled errors rather than crashing the
  graph.

The research flow may compose core retrieval with expansion, fusion, and
reranking, then feed results into deterministic metrics and selected Ragas
validation.

## Corpus Preparation

Canonical policy documents live under `data/policies/`. Preparation is:

```text
policy documents
  -> normalize and validate
  -> section-aware chunking
  -> embedding and Chroma ingestion
  -> dense retrieval
```

Normalization and validation scripts move to a top-level `scripts/` directory.
Chunking remains a reusable core module and exposes a CLI. Generated chunks,
manifests, indexes, and caches are reproducible outputs, not source files.

## Research and Evaluation

The public repository keeps:

- The evaluation dataset and its validation tests.
- Benchmark code for dense baseline, reranker, multi-query, and combined
  retrieval variants.
- Compact Markdown summaries and configuration metadata for the reported runs.
- Ragas validation for the dense baseline and selected best configuration.

It does not keep large generated per-case artifacts, model caches, query
expansion caches, or local vector indexes. Ragas is opt-in and is not required
for the default test suite.

## Repository Hygiene

The repository will ignore and remove from tracking runtime/generated content:

- Python caches and `.langgraph_api/` state.
- Chroma SQLite/index files and other local vector-store data.
- `data/generated/` outputs and expansion caches.
- Obsolete archive files and notebooks whose workflows have CLI equivalents.
- `.env` and any local database/runtime state not required for the demo.

The repository will add `.env.example`, use relative paths, and update the
README with one verified quickstart for backend, corpus/index preparation, and
LangGraph execution. Runtime and research/evaluation dependencies will be
separated or clearly grouped.

## Testing and Error Handling

Core tests cover front matter and Markdown parsing, chunk boundaries and token
limits, metadata/citations, dense retrieval with fake embeddings, empty/no-hit
queries, and LLM failure handling. Research tests cover expansion validation,
cache behavior, RRF ordering, reranker ordering, and benchmark configuration.
Evaluation tests cover dataset validation, metrics, and report generation.

The default suite does not download models or call external services. Real model
smoke tests and Ragas runs use explicit opt-in markers.

Runtime fallback behavior is deterministic for empty input and no results;
configuration, vector-store, embedding, and LLM errors are surfaced with clear
messages suitable for the agent tool.

## Success Criteria

- A new reader can identify the production RAG path without reading research
  code.
- `query_gym_policy` uses dense retrieval only and does not import research
  modules.
- The four retrieval variants remain reproducible from source documents and the
  evaluation dataset.
- Ragas evidence remains available for the baseline and selected best variant.
- Default tests pass without model downloads or network calls.
- README commands use repository-relative paths and match the final tree.
- Generated artifacts and secrets are excluded from the public Git history.
