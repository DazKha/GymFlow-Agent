from __future__ import annotations

from langchain_core.messages import HumanMessage
from agent.state import AgentState


def get_last_user_text(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return (msg.content or "").strip() if isinstance(msg.content, str) else ""
    return ""


def normalize_intent(raw: str) -> str:
    token = (raw or "").strip().lower().split()[0].strip(".,;:!?") if raw else ""
    return token if token in {"consult", "policy", "booking", "off_topic"} else "consult"