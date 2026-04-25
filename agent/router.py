from __future__ import annotations

from langchain_core.messages import HumanMessage
from agent.state import AgentState

ROUTER_PROMPT = """
Bạn là router cho chatbot gym.
Phân loại tin nhắn user vào đúng 1 intent:
- consult: hỏi gói tập, tiện ích, so sánh
- policy: hỏi điều khoản/chính sách
- booking: muốn đặt lịch tư vấn/tập thử
Chỉ trả về 1 từ: consult | policy | booking
""".strip()

def get_last_user_text(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return (msg.content or "").strip() if isinstance(msg.content, str) else ""
    return ""

def normalize_intent(raw: str) -> str:
    token = (raw or "").strip().lower().split()[0].strip(".,;:!?") if raw else ""
    if token == "off_topic":
        return "consult"
    return token if token in {"consult", "policy", "booking"} else "consult"