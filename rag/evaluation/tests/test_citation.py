from rag.core.retriever import PolicySearchResult
from rag.evaluation.citation import citation_coverage


def test_citation_coverage_matches_referenced_chunk_ids():
    result = PolicySearchResult(
        chunk_id="payment-1", content="Payment details", document_id="payment",
        document_title="Payment policy", section_path=["Payment"], clause_ids=[],
        source_url="https://example.test/payment",
    )

    assert citation_coverage([result], {"payment-1"}) == 1.0
    assert citation_coverage([result], {"other"}) == 0.0
