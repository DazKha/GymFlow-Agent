"""Dense-only production policy RAG pipeline."""

from __future__ import annotations

import logging
import os
from typing import Any

from rag.core.retriever import PolicyRetriever, PolicySearchResult

logger = logging.getLogger(__name__)

RETRIEVE_TOP_K = int(os.getenv("POLICY_RETRIEVAL_TOP_K", "5"))
_LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("EDU_AGENT_MODEL", "openai-gpt-4o-mini"))
_llm: Any = None


def _get_llm() -> Any:
    global _llm
    if _llm is not None:
        return _llm

    api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
    if not api_key:
        return None

    from langchain_gradient import ChatGradient

    _llm = ChatGradient(model=_LLM_MODEL, api_key=api_key, temperature=0.0)
    return _llm


def _citation_context(results: list[PolicySearchResult]) -> str:
    return "\n\n".join(
        f"[Context {index}]\n{result.content}\n{result.citation_label()}"
        for index, result in enumerate(results, 1)
    )


def _safe_provider_failure(error: Exception) -> str:
    # Keep provider details in logs while returning no credentials or traceback to callers.
    try:
        raise RuntimeError("policy provider failure") from error
    except RuntimeError as chained_error:
        logger.error(
            "Policy RAG provider failure",
            exc_info=(type(chained_error), chained_error, chained_error.__traceback__),
        )
    return "Không thể tra cứu chính sách lúc này."


def run_policy_rag(query: str) -> str:
    """Retrieve policy passages with dense search and answer from their citations."""
    normalized_query = (query or "").strip()
    if not normalized_query:
        return "Câu hỏi trống, không thể tra cứu."

    try:
        results = PolicyRetriever().search(normalized_query, top_k=RETRIEVE_TOP_K)
        if not results:
            return "Không đủ dữ liệu để trả lời chắc chắn."

        context = _citation_context(results)
        llm = _get_llm()
        if llm is None:
            return "Không thể tra cứu chính sách lúc này."

        prompt = f"""
Bạn là nhân viên chăm sóc khách hàng. Trả lời câu hỏi chỉ dựa trên CONTEXT.
Trả lời ngắn gọn bằng tiếng Việt và trích dẫn (Context X) sau mỗi ý quan trọng.
Nếu CONTEXT không đủ, nói rõ rằng tài liệu không đề cập rõ thông tin này.

USER QUESTION
{normalized_query}

CONTEXT
{context}
"""
        response = llm.invoke(prompt)
        return response.content
    except Exception as error:  # noqa: BLE001
        return _safe_provider_failure(error)
