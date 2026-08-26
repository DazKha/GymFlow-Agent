"""Command-line entry point for the four retrieval experiments."""

import argparse

from .retrieval_config import experiment_configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark dense and optional retrieval variants")
    parser.add_argument("--config", choices=[config.name for config in experiment_configs()],
                        help="Run one variant; omit to list all variants")
    parser.add_argument("--query", help="Benchmark query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    configs = experiment_configs()
    selected = [config for config in configs if not args.config or config.name == args.config]
    if args.query:
        from rag.core.retriever import PolicyRetriever
        for config in selected:
            results = PolicyRetriever().search(args.query, top_k=args.top_k)
            print(f"{config.name}: {len(results)} results")
    else:
        for config in selected:
            print(config.name)


if __name__ == "__main__":
    main()
