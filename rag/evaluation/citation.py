"""Citation coverage metrics for retrieved policy chunks."""

from collections.abc import Iterable


def citation_coverage(results: Iterable[object], referenced_chunk_ids: Iterable[str]) -> float:
    expected = set(referenced_chunk_ids)
    if not expected:
        return 0.0
    found = {getattr(result, "chunk_id", "") for result in results}
    return len(found & expected) / len(expected)
