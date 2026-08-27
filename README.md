# Alex, FlexFit Gym Assistant

Alex is a Vietnamese LangGraph assistant for **FlexFit Gym**, a fictional gym
used as a software demonstration. The assistant helps customers:

- Discover membership plans and compare packages.
- Find clubs, facilities, and opening hours.
- Ask questions about policies, terms, refunds, privacy, and gym rules.
- Book a free trial session through a small FastAPI backend.

The project demonstrates a multi-task agent with a deliberately separated RAG
stack. The production policy path is small and predictable: it uses dense
retrieval with multilingual E5 embeddings and Chroma. More expensive retrieval
strategies are preserved as research experiments and are never loaded by the
normal agent runtime.

## What This Repository Demonstrates

This repository is organized around three concerns:

1. **Application runtime**: LangGraph routing, tools, guardrails, and the
   policy-answering path used by the agent.
2. **RAG core**: policy normalization, section-aware chunking, embedding,
   Chroma ingestion, dense retrieval, and cited answer generation.
3. **Research and evaluation**: controlled comparisons of dense retrieval,
   reranking, multi-query expansion, reciprocal-rank fusion, and optional Ragas
   validation.

The research code is intentionally not part of the production import path. This
makes the default application easier to run, inspect, and reason about while
keeping the experiments reproducible.

## Architecture

### Agent request flow

```text
User message
    |
    v
Input guard -> Intent router -> consult | policy | booking
                              |          |         |
                              v          v         v
                         HTTP tools  policy RAG  booking tools
                                        |
                                        v
                              dense E5 retrieval
                                        |
                                        v
                                  Chroma index
                                        |
                                        v
                                  LLM response
                                        |
                                        v
                                 Output guard
```

The policy tool is exposed through `tools/query_gym_policy.py` and calls
`rag.core.pipeline`. The production path does not import `rag.research` or
Ragas.

### RAG package boundaries

```text
rag/
  core/
    chunking.py       # Parse policy Markdown and create chunks
    models.py         # Chunking and policy result models
    vector_store.py   # Chroma persistence and E5 embeddings
    retriever.py      # Dense retrieval and citation metadata
    pipeline.py       # Production retrieve-and-generate entry point
    ingest.py         # Build/update the Chroma index
  research/
    benchmark.py      # Four retrieval experiment variants
    retrieval_config.py
    query_expansion.py
    retrieval_fusion.py
    reranker.py
  evaluation/
    dataset.py        # Evaluation JSONL loading
    metrics.py        # Deterministic retrieval metrics
    pipeline.py       # Evaluation orchestration
    ragas_validation.py
```

The important dependency direction is:

```text
rag.research  -> rag.core
rag.evaluation -> rag.core and rag.research
agent/tools   -> rag.core
rag.core      -X-> rag.research or rag.evaluation
```

## Production RAG

The production policy path is dense retrieval only:

```text
query_gym_policy(query)
    -> rag.core.pipeline.run_policy_rag(query)
    -> PolicyRetriever.search(query, top_k=5)
    -> cited context construction
    -> Vietnamese LLM answer
```

Production behavior:

- Embedding model: `intfloat/multilingual-e5-base`.
- Vector store: Chroma with cosine distance.
- Default retrieval size: five chunks.
- Output language: Vietnamese.
- Responses cite document title, section, clause, and source URL when those
  fields are available.
- Empty queries and no-result searches use deterministic fallback responses.
- Provider failures are converted into safe tool-facing errors.
- Query expansion, RRF, cross-encoder reranking, and Ragas are not runtime
  features.

This separation is intentional. The production agent should not unexpectedly
pay for extra LLM calls, cross-encoder model loading, or research-only
dependencies because an environment variable was set.

## Project Layout

```text
agent/                       LangGraph state, nodes, prompts, and graph
tools/                       Agent tools and HTTP client
guardrails/                  Input/output safety helpers
backend/                     FastAPI gym catalog and booking mock backend
data/policies/               Canonical policy Markdown sources
rag/core/                    Production RAG and indexing code
rag/research/                Optional retrieval experiments
rag/evaluation/              Dataset, metrics, and Ragas validation
docs/rag/                    Policy preparation notes
docs/evaluation/             Experiment and Ragas documentation
scripts/                     Policy normalization and validation scripts
```

Generated indexes, model caches, Python bytecode, local databases, LangGraph
state, and experiment run outputs are intentionally ignored by Git.

## Requirements

- Python 3.9 or newer.
- A compatible OpenAI-style or Gradient inference endpoint for agent answers.
- Enough local disk space for the E5 embedding model and Chroma index.
- Optional: `requirements-research.txt` for Ragas validation.

The default runtime requirements include LangGraph, the LangGraph CLI, Chroma,
Sentence Transformers, PyTorch, `tiktoken`, and PyYAML. Ragas is kept separate
because it is not needed to start the agent or run the offline test suite.

## Configuration

Copy the template and fill in a provider credential:

```bash
cp .env.example .env
```

Important variables:

| Variable | Purpose | Default |
|---|---|---|
| `DIGITALOCEAN_INFERENCE_KEY` | Gradient/DigitalOcean inference credential | empty |
| `GRADIENT_MODEL_ACCESS_KEY` | Alternative Gradient credential | empty |
| `MODEL_NAME` | Agent model name | `deepseek-v4-flash` |
| `LLM_MODEL` | Policy RAG model name | `deepseek-v4-flash` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint | provider-specific |
| `BACKEND_URL` | Gym backend URL | `http://127.0.0.1:8000` |
| `CHROMA_PERSIST_DIR` | Chroma persistence directory | `data/generated/chroma` |
| `CHROMA_POLICY_COLLECTION` | Chroma collection name | `gymflow_policy_e5_v1` |
| `POLICY_EMBEDDING_MODEL` | Sentence Transformers embedding model | `intfloat/multilingual-e5-base` |
| `POLICY_RETRIEVAL_TOP_K` | Production dense retrieval size | `5` |

Research-only settings such as reranker and multi-query configuration belong to
the research commands and are not read by the production pipeline.

## Quick Start

### 1. Create an environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\\Scripts\\activate` instead.

### 2. Configure the agent

```bash
cp .env.example .env
# Edit .env and set an inference credential and endpoint.
```

### 3. Start the mock backend

The backend is a tracked FastAPI application. Run it from the repository root:

```bash
cd backend
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

The backend exposes interactive API documentation at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

The backend creates `backend/gym.db` at runtime. The database is local state and
is intentionally not tracked.

### 4. Build the policy index

In a second terminal, from the repository root, prepare the canonical policy
documents and build the generated Chroma index:

```bash
python scripts/normalize_policies.py
python scripts/validate_policies.py

python -m rag.core.chunking \
  --input-dir data/policies \
  --output data/generated/policy_chunks.jsonl \
  --report data/generated/policy_chunk_report.json

python -m rag.core.ingest \
  --input data/generated/policy_chunks.jsonl \
  --persist-dir data/generated/chroma \
  --recreate-collection \
  --sync
```

The first real ingestion downloads `intfloat/multilingual-e5-base` if it is not
already available locally. To validate the corpus without embedding or writing
an index, use:

```bash
python -m rag.core.ingest \
  --input data/generated/policy_chunks.jsonl \
  --persist-dir data/generated/chroma \
  --dry-run
```

Re-run normalization, validation, chunking, and ingestion whenever a policy
source changes. The corpus is section-aware and preserves document, section,
clause, source, and effective-date metadata for citations.

### Policy Chunking

Policy Markdown files are split by heading and clause boundaries before
embedding. Chunks keep their document and section hierarchy, clause IDs, source
URL, and effective date, so retrieval can return concise context with traceable
citations. The chunker writes JSONL plus a validation report to
`data/generated/`; these generated files are reproducible and ignored by Git.

### 5. Start LangGraph

From the repository root:

```bash
langgraph dev
```

The graph is declared in `langgraph.json` as `agent.graph:graph`.

## Default RAG Benchmark

The default benchmark is the production-style dense RAG path. It evaluates the
same retrieval behavior used by the agent rather than silently enabling a
research strategy. The evaluation dataset is:

```text
rag/evaluation/policy_eval_set_v1.jsonl
```

It contains 32 Vietnamese policy questions across five policy documents,
including answerable, cross-document, and unanswerable cases. The dataset
contains reference document IDs, reference chunk IDs, and reference answers.
See `rag/evaluation/policy_eval_set_v1_README.md` for the schema and cautions.

### Default dense retrieval evaluation

Build the index first, then run the dense configuration:

```bash
python -m rag.evaluate_policy_rag \
  --dataset rag/evaluation/policy_eval_set_v1.jsonl \
  --config dense \
  --top-k 5
```

This command runs deterministic retrieval evaluation using the dense production
retriever. It reports retrieval quality for the selected configuration without
calling an LLM. Use `--top-k 1`, `--top-k 3`, `--top-k 5`, and `--top-k 8` when
you want a comparable retrieval curve.

The main retrieval metrics are:

| Metric | Meaning |
|---|---|
| Document Hit@K | A relevant policy document appears in the top K. |
| Chunk Hit@K | A reference chunk appears in the top K. |
| Precision@K | Fraction of retrieved chunks that are relevant. |
| Recall@K | Fraction of reference chunks recovered in the top K. |
| MRR | Reciprocal rank of the first relevant chunk, averaged per case. |
| First relevant rank | Position of the first relevant result for successful cases. |

The tracked dataset and code are the reproducible benchmark inputs. Generated
per-case result files and Chroma indexes are local outputs under ignored paths.

### Default end-to-end RAG and citation evaluation

The runtime path answers policy questions through `query_gym_policy` and
`rag.core.pipeline`. An end-to-end result record should preserve:

```json
{
  "user_input": "Chinh sach hoan tien khi huy goi la gi?",
  "reference": "Reference answer from the evaluation set",
  "retrieved_contexts": ["Retrieved policy chunk 1", "Retrieved policy chunk 2"],
  "response": "Generated Vietnamese answer",
  "retrieved_chunk_ids": ["chunk-id-1", "chunk-id-2"]
}
```

Use the deterministic citation evaluator alongside generation. It checks that
the answer cites available document/section/chunk evidence rather than only
measuring semantic answer quality. Do not treat a fluent answer without valid
source evidence as a successful policy answer.

### Default Ragas validation

Ragas is a secondary, opt-in validation layer for the default dense RAG path.
It evaluates generated responses and retrieved context, not just vector search.
Typical metrics are:

- Context Precision.
- Context Recall.
- Faithfulness.
- Answer Relevancy.
- Answer Correctness as a secondary metric.

Install the optional dependencies:

```bash
python -m pip install -r requirements-research.txt
```

List the default validation targets without importing or executing Ragas:

```bash
python -m rag.evaluation.ragas_validation --list
```

By default, the validator targets the dense baseline and the selected best
retrieval configuration. To validate concrete generated result files, pass only
the files you want:

```bash
python -m rag.evaluation.ragas_validation \
  --result-path rag/evaluation/runs/dense/results.jsonl \
  --result-path rag/evaluation/runs/combined/results.jsonl
```

The validator does not invent responses or reference answers. It reads selected
JSONL results, converts them to the installed Ragas dataset type, and then calls
the configured Ragas evaluator. Result files are ignored because they can
contain generated answers and provider-specific output. A clean checkout with
no result files fails with a clear message telling you to run evaluation first.

The default dense benchmark therefore has two separate evidence layers:

```text
Dense retrieval metrics
    -> document/chunk hit, precision, recall, MRR, latency

Generated dense RAG responses
    -> citation checks and selected Ragas metrics
```

Ragas is not required for the default test suite or for production startup.

## Retrieval Variant Benchmark

The research benchmark keeps four explicit configurations. These variants are
for retrieval comparison and do **not** require Ragas.

| Variant | Retrieval flow | Extra cost | Ragas by default |
|---|---|---|---|
| `dense` | One dense E5 search | Lowest | No |
| `reranker` | Dense candidate pool followed by BGE cross-encoder reranking | Cross-encoder inference | No |
| `multi_query` | LLM query expansion, dense search per variant, RRF fusion | Extra LLM call and searches | No |
| `combined` | Multi-query expansion, dense searches, RRF fusion, then reranking | Highest | No |

### Run the benchmark CLI

Install the optional research dependencies first when using model-backed
variants:

```bash
python -m pip install -r requirements-research.txt
```

Inspect all configurations without loading an embedding model, LLM, or
cross-encoder:

```bash
python -m rag.research.benchmark --help
```

Run one query through all four variants:

```bash
python -m rag.research.benchmark \
  --query "Chinh sach bao mat thong tin ca nhan la gi?" \
  --top-k 5
```

Run a single variant:

```bash
python -m rag.research.benchmark \
  --config reranker \
  --query "Dieu kien hoan tien khi huy goi tap la gi?" \
  --top-k 5
```

The benchmark composes the following components:

```text
dense
  PolicyRetriever.search

reranker
  PolicyRetriever.search -> CrossEncoderReranker.rerank

multi_query
  LLMQueryExpander -> dense search per query -> fuse_ranked_results

combined
  LLMQueryExpander -> dense search per query -> RRF fusion
                    -> CrossEncoderReranker.rerank
```

Compare variants using deterministic retrieval metrics from the same evaluation
dataset:

```bash
python -m rag.evaluate_policy_rag \
  --dataset rag/evaluation/policy_eval_set_v1.jsonl \
  --config dense \
  --top-k 5

python -m rag.evaluate_policy_rag \
  --dataset rag/evaluation/policy_eval_set_v1.jsonl \
  --config reranker \
  --top-k 5

python -m rag.evaluate_policy_rag \
  --dataset rag/evaluation/policy_eval_set_v1.jsonl \
  --config multi_query \
  --top-k 5

python -m rag.evaluate_policy_rag \
  --dataset rag/evaluation/policy_eval_set_v1.jsonl \
  --config combined \
  --top-k 5
```

Do not compare one variant at `top-k=3` with another at `top-k=8`. Keep the
dataset, corpus, embedding model, candidate pool, and final top-k aligned when
making quality or latency claims.

### Interpretation guidance

- Use `dense` as the production baseline.
- Use `reranker` to measure ranking quality gained from a cross-encoder over a
  fixed dense candidate pool.
- Use `multi_query` to measure recall gains from alternative Vietnamese query
  formulations and RRF fusion.
- Use `combined` to measure the maximum retrieval quality configuration, not a
  default production recommendation.
- Report both quality and latency. A small Recall@K improvement may not justify
  an extra LLM call or multi-second reranker inference.
- Do not use Ragas results to claim that a retrieval variant is better unless
  that variant was evaluated using generated responses and the same references.

The repository intentionally does not commit a large generated run directory or
model cache. Store compact conclusions, configuration metadata, and selected
tables in `docs/evaluation/` when publishing a benchmark result.

## Backend API

The mock backend provides catalog and booking data for the non-policy tools.
Start it with the commands above, then use:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/packages/search
curl -s http://127.0.0.1:8000/facilities
```

The backend README contains the complete endpoint examples, including package
comparison, club lookup, available slots, and booking creation.

## Testing And Verification

The default suite is offline and uses fake embeddings and injected components.
It does not download model weights or call an external inference provider:

```bash
python -m pytest -q
```

Run only the three RAG areas:

```bash
python -m pytest -q \
  rag/core/tests \
  rag/research/tests \
  rag/evaluation/tests \
  -m "not real_model"
```

Run command and import checks without building a model-backed index:

```bash
python -c "import agent.graph; import tools.query_gym_policy; import rag.core.pipeline"
python -m rag.core.chunking --help
python -m rag.core.ingest --help
python -m rag.research.benchmark --help
python -m rag.evaluate_policy_rag --help
python -m rag.evaluation.ragas_validation --help
python -m rag.evaluation.ragas_validation --list
```

Opt-in real-model checks are intentionally separate:

```bash
python -m pytest -m real_model rag/research/tests/test_reranker.py
```

These checks may download `BAAI/bge-reranker-v2-m3` and require network access.
Ragas execution also requires configured evaluator credentials and selected
result JSONL files.

## Evaluation Dataset And Limitations

The policy evaluation set is a seed dataset, not a legal benchmark reviewed by
legal experts. Its reference answers summarize a particular policy snapshot and
are not legal advice.

When the corpus or chunking algorithm changes:

1. Rebuild the policy chunks.
2. Recompute the corpus version.
3. Validate or remap `reference_chunk_ids`.
4. Re-run the dense baseline before comparing variants.

Avoid tuning and reporting on the same small set as if it were a generalized
benchmark. Use a holdout set or expand the dataset before making production
claims.

## Reproducibility Checklist

Before publishing a benchmark result, record:

- Git commit or release identifier.
- Corpus version and policy source snapshot.
- Evaluation dataset path/version.
- Embedding model and distance metric.
- Candidate pool and final top-k.
- Query variant count and expansion prompt version, when applicable.
- Reranker model, batch size, and device, when applicable.
- Retrieval metrics at the same K values for every variant.
- Warm latency and cold model-load latency separately.
- Whether results came from deterministic retrieval only or from generated
  responses plus Ragas.

## License And Demo Disclaimer

FlexFit Gym and Alex are fictional demo/project branding. The policy documents,
catalog data, and backend are mock data. Replace branding, endpoints, policy
sources, authentication, and operational controls before using this project in a
real customer-facing system.
