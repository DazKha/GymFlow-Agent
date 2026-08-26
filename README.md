# Alex, FlexFit Gym policy agent

Alex is a Vietnamese LangGraph agent for gym-plan advice, policy questions, and
trial-session booking. Policy answers use the dense production RAG path and
return citations from the indexed policy documents.

## Architecture

```text
agent graph -> tools/query_gym_policy -> rag.core.pipeline
                                      -> dense E5 retriever -> Chroma

rag.research   optional benchmark variants
rag.evaluation deterministic metrics and opt-in Ragas validation
```

The agent imports only `rag.core`. Query expansion, reciprocal-rank fusion,
cross-encoder reranking, benchmark runs, and Ragas are not part of normal
startup. A clean runtime install therefore does not import Ragas.

## Setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set `DIGITALOCEAN_INFERENCE_KEY` or `GRADIENT_MODEL_ACCESS_KEY` and
`MODEL_NAME` for the agent. Set `LLM_MODEL` for policy answers. Start the
tracked backend from the repository root:

```bash
cd backend
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

The backend creates `backend/gym.db` at runtime; that database is intentionally
not tracked. The agent expects `BACKEND_URL=http://127.0.0.1:8000`.

Start the agent with:

```bash
langgraph dev
```

## Policy Index

Canonical Markdown sources live in `data/policies/`. The following workflow
uses only repository-relative paths and keeps generated output ignored:

```bash
python scripts/normalize_policies.py
python scripts/validate_policies.py
python -m rag.core.chunking --input-dir data/policies \
  --output data/generated/policy_chunks.jsonl \
  --report data/generated/policy_chunk_report.json
python -m rag.core.ingest --input data/generated/policy_chunks.jsonl --dry-run
python -m rag.core.ingest --input data/generated/policy_chunks.jsonl \
  --persist-dir data/generated/chroma --recreate-collection --sync
```

The production index uses multilingual E5 embeddings and dense cosine search
only. Rebuild chunks and the index whenever a policy source changes.

## Research And Evaluation

Install optional dependencies only when needed:

```bash
python -m pip install -r requirements-research.txt
python -m rag.research.benchmark --help
python -m rag.evaluate_policy_rag --dataset rag/evaluation/policy_eval_set_v1.jsonl --config dense --top-k 5
```

The research benchmark exposes `dense`, `reranker`, `multi_query`, and
`combined` configurations. Ragas is intentionally selective: pass only the
result files you want to validate, normally the dense baseline and the chosen
best configuration.

```bash
python -m rag.evaluation.ragas_validation --list
python -m rag.evaluation.ragas_validation \
  --result-path path/to/dense.jsonl \
  --result-path path/to/combined.jsonl
```

Ragas is imported lazily only by the execution path; listing or selecting files
does not require it.

## Checks

```bash
python -m pytest -q
python -m pytest -q rag/core/tests rag/research/tests rag/evaluation/tests -m "not real_model"
python scripts/normalize_policies.py --help
python scripts/validate_policies.py --help
python -m rag.core.chunking --help
python -m rag.core.ingest --help
python -m rag.research.benchmark --help
python -m rag.evaluation.ragas_validation --help
```

The default tests are offline and do not download models or call external
services. See `docs/rag/` for policy preparation notes and `docs/evaluation/`
for benchmark and Ragas details.
