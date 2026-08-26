from rag.evaluation.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k


def test_retrieval_metrics_are_deterministic_at_k():
    retrieved = ["a", "b", "c"]
    relevant = {"b", "c"}

    assert precision_at_k(retrieved, relevant, 2) == 0.5
    assert recall_at_k(retrieved, relevant, 2) == 0.5
    assert mean_reciprocal_rank([retrieved], relevant) == 0.5
