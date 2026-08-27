from rag.research.retrieval_fusion import fuse_ranked_results


def test_fusion_orders_unique_results_by_rrf_score_and_original_order():
    first = [{"id": "a"}, {"id": "b"}]
    second = [{"id": "b"}, {"id": "c"}]

    fused = fuse_ranked_results([first, second], candidate_pool_size=3, rrf_k=60)

    assert [item["id"] for item in fused] == ["b", "a", "c"]
