"""Optional query expansion implementations."""

from dataclasses import dataclass
import json
import time
from typing import Any, Callable


@dataclass(frozen=True)
class ExpansionResult:
    queries: list[str]
    latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    source_llm_latency_ms: float = 0.0
    cache_hit: bool = False
    llm_calls: int = 0


def _clean_queries(query: str, raw: Any, count: int) -> list[str]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = raw.splitlines()
    if not isinstance(raw, (list, tuple)):
        raw = []
    queries = [str(item).strip() for item in raw if str(item).strip()]
    return list(dict.fromkeys([query.strip(), *queries]))[:count]


class LLMQueryExpander:
    def __init__(self, query_variant_count: int = 3, llm: Any = None) -> None:
        if query_variant_count < 1:
            raise ValueError("query_variant_count must be > 0")
        self.query_variant_count = query_variant_count
        self.llm = llm

    def expand(self, query: str) -> ExpansionResult:
        if not query.strip():
            raise ValueError("Query must be non-empty")
        started = time.perf_counter()
        if self.llm is None:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI()
        response = self.llm.invoke(query)
        raw = getattr(response, "content", response)
        queries = _clean_queries(query, raw, self.query_variant_count)
        latency = (time.perf_counter() - started) * 1000
        return ExpansionResult(queries, latency, latency, latency, False, 1)


class CachedQueryExpander:
    def __init__(self, source: Any, max_entries: int = 1024) -> None:
        self.source = source
        self.max_entries = max_entries
        self._cache: dict[str, ExpansionResult] = {}

    def expand(self, query: str) -> ExpansionResult:
        if query in self._cache:
            result = self._cache[query]
            return ExpansionResult(result.queries, result.latency_ms, result.llm_latency_ms,
                                   result.source_llm_latency_ms, True, 0)
        started = time.perf_counter()
        result = self.source.expand(query) if hasattr(self.source, "expand") else self.source(query)
        if isinstance(result, ExpansionResult):
            normalized = result
        else:
            normalized = ExpansionResult(_clean_queries(query, result, max(1, len(result))))
        normalized = ExpansionResult(normalized.queries,
                                     (time.perf_counter() - started) * 1000,
                                     normalized.llm_latency_ms, normalized.source_llm_latency_ms,
                                     False, normalized.llm_calls)
        if len(self._cache) >= self.max_entries:
            self._cache.pop(next(iter(self._cache)))
        self._cache[query] = normalized
        return normalized
