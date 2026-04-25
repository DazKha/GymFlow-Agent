from __future__ import annotations

from langchain_core.tools import tool

from rag.policy_pipeline import run_policy_rag


@tool
def query_gym_policy(query: str) -> str:
    """Tra cứu điều khoản, chính sách, hoàn tiền, đóng băng, nội quy (RAG từ tài liệu nội bộ). Truyền câu hỏi tiếng Việt, đủ rõ nội dung cần biết (vd: 'Chính sách hoàn tiền khi huỷ gói 12 tháng')."""
    return run_policy_rag(query.strip())
