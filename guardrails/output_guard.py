from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage

from agent.state import AgentState


_OFF_TOPIC_RESPONSE = "Xin lỗi bạn, mình chỉ hỗ trợ các câu hỏi về dịch vụ gym, gói tập, chính sách và đặt lịch tại FlexFit Gym thôi ạ. Bạn cần mình giúp gì khác không ạ?"

_INJECTION_RESPONSE = "Xin lỗi, mình không thể xử lý yêu cầu này. Nếu bạn có thắc mắc về dịch vụ gym, mình sẵn sàng hỗ trợ ạ."

_EMPTY_INPUT_RESPONSE = "Mình chưa nhận được nội dung câu hỏi, bạn thử gửi lại nhé."


def _get_last_ai_text(state: AgentState) -> str:
    from langchain_core.messages import AIMessage
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage):
            return (msg.content or "").strip() if isinstance(msg.content, str) else ""
    return ""


def _contains_pii(text: str) -> bool:
    patterns = [
        r"\b0[3-9]\d{8}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    ]
    return any(re.search(p, text) for p in patterns)


def output_guard_node(state: AgentState) -> dict[str, Any]:
    intent = state.get("intent")
    safe = state.get("safe", True)
    reason = state.get("reason", "")

    if not safe:
        if reason == "prompt_injection":
            return {"messages": [AIMessage(content=_INJECTION_RESPONSE)]}
        if reason == "empty_input":
            return {"messages": [AIMessage(content=_EMPTY_INPUT_RESPONSE)]}

    if intent == "off_topic":
        return {"messages": [AIMessage(content=_OFF_TOPIC_RESPONSE)]}

    last_ai = _get_last_ai_text(state)
    if not last_ai:
        return {}

    if _contains_pii(last_ai):
        sanitized = re.sub(r"\b0[3-9]\d{8}\b", "***", last_ai)
        sanitized = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "***", sanitized)
        return {"messages": [AIMessage(content=sanitized)]}

    return {}
