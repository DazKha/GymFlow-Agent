# Retrieval Experiments

The corpus version is `policy-eval-set-v1`. The reproducible configurations are
`dense`, `reranker`, `multi_query`, and `combined`; evaluation injects a retriever
and an explicit `RetrievalConfig`, so production environment flags do not select a
research strategy. Reports should record precision/recall at `k`, MRR, and mean
retrieval latency in milliseconds.

Run a selected experiment with `python -m rag.evaluate_policy_rag --dataset PATH
--config dense --top-k 5`. Generated result files belong under the ignored
`rag/evaluation/runs/` directory and are not committed.
