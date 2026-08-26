from rag.research.query_expansion import CachedQueryExpander


def test_cached_expander_returns_cached_queries_without_calling_source():
    calls = []
    expander = CachedQueryExpander(lambda query: calls.append(query) or [query, "expanded"])

    assert expander.expand("q").queries == ["q", "expanded"]
    assert expander.expand("q").queries == ["q", "expanded"]
    assert calls == ["q"]
