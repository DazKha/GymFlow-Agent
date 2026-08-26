"""Command-line retrieval evaluation; generation/provider calls are opt-in."""

from __future__ import annotations

import argparse

from rag.core.retriever import PolicyRetriever
from rag.evaluation.dataset import load_evaluation_dataset
from rag.evaluation.pipeline import evaluate_retrieval
from rag.research.retrieval_config import RetrievalConfig, experiment_configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an explicit RAG retrieval configuration")
    parser.add_argument("--dataset", default="rag/evaluation/policy_eval_set_v1.jsonl",
                        help="Evaluation JSONL dataset")
    parser.add_argument("--config", choices=[config.name for config in experiment_configs()], default="dense")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    base = next(config for config in experiment_configs() if config.name == args.config)
    config = RetrievalConfig(**{**base.__dict__, "final_top_k": args.top_k, "candidate_pool_size": max(base.candidate_pool_size, args.top_k)})
    report = evaluate_retrieval(load_evaluation_dataset(args.dataset), PolicyRetriever(), config)
    print(report)


if __name__ == "__main__":
    main()
