"""Deterministic reciprocal-rank fusion."""


def _key(item):
    return item.chunk_id if hasattr(item, "chunk_id") else item.get("chunk_id", item.get("id"))


def fuse_ranked_results(ranked_lists, candidate_pool_size: int = 20, rrf_k: int = 60):
    if candidate_pool_size < 1 or rrf_k < 1:
        raise ValueError("candidate_pool_size and rrf_k must be > 0")
    by_key = {}
    scores = {}
    first_seen = {}
    for list_index, ranked in enumerate(ranked_lists):
        for rank, item in enumerate(ranked, 1):
            key = _key(item)
            if key is None:
                continue
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            first_seen.setdefault(key, len(first_seen))
            by_key.setdefault(key, item)
    ordered = sorted(by_key, key=lambda key: (-scores[key], first_seen[key]))
    result = []
    for key in ordered[:candidate_pool_size]:
        item = by_key[key]
        if hasattr(item, "fused_score"):
            item.fused_score = scores[key]
        elif isinstance(item, dict):
            item = dict(item)
            item["fused_score"] = scores[key]
        result.append(item)
    return result
