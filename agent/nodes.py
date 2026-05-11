from langchain_gradient import ChatGradient

import json
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage

from agent.state import AgentState
from agent.router import get_last_user_text, normalize_intent

from agent.prompts import (
    ROUTER_PROMPT,
    CONSULT_PROMPT,
    BOOKING_PROMPT,
    POLICY_PROMPT,
    SYSTEM_PROMPT,
)

from tools import (
    search_packages,
    get_package_detail,
    # compare_packages,
    # get_facilities,
    create_booking,
    get_vietnam_now,
)
from tools.query_gym_policy import query_gym_policy

api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
model = os.getenv("MODEL_NAME") or "openai-gpt-4o"
llm = ChatGradient(model=model, api_key=api_key)


def _normalize_messages_for_provider(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Normalize tool message payloads and strip dangling tool-calls from the last AI turn."""
    normalized: list[BaseMessage] = []
    observed_tool_ids: set[str] = set()

    for msg in messages:
        if isinstance(msg, ToolMessage):
            content = msg.content
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            normalized.append(
                ToolMessage(
                    content=content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                    id=msg.id,
                    status=msg.status,
                    artifact=msg.artifact,
                    additional_kwargs=msg.additional_kwargs,
                    response_metadata=msg.response_metadata,
                )
            )
            if isinstance(msg.tool_call_id, str) and msg.tool_call_id:
                observed_tool_ids.add(msg.tool_call_id)
            continue

        normalized.append(msg)

    # If the latest AI message has unresolved tool_calls, strip them to avoid
    # provider validation errors while preserving the text content.
    for i in range(len(normalized) - 1, -1, -1):
        msg = normalized[i]
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                call_ids = [
                    c.get("id")
                    for c in tool_calls
                    if isinstance(c, dict) and isinstance(c.get("id"), str) and c.get("id")
                ]
                unresolved = [cid for cid in call_ids if cid not in observed_tool_ids]
                if unresolved:
                    normalized[i] = AIMessage(
                        content=msg.content,
                        tool_calls=[],
                        id=msg.id,
                        additional_kwargs=msg.additional_kwargs,
                        response_metadata=msg.response_metadata,
                    )
            break

    return normalized


def input_guard_node(state: AgentState) -> dict[str, Any]:
    text = get_last_user_text(state)

    if not text or not text.strip():
        return {
            "safe": False,
            "reason": "empty_input",
            "messages": [AIMessage(content="Mình chưa nhận được nội dung câu hỏi, bạn thử gửi lại nhé.")],
        }

    return {"safe": True, "reason": ""}


def _format_transcript_for_router(messages: list, max_items: int = 14, chunk: int = 200) -> str:
    """Recent history for routing (avoids 'đúng vậy' -> consult with no context)."""
    turn = []
    for m in list(messages or [])[-max_items:]:
        if isinstance(m, HumanMessage):
            t = m.content
            t = t if isinstance(t, str) else str(t)
            t = " ".join(t.split())[: chunk * 2]
            turn.append("user: " + t[:chunk] + ("…" if len(t) > chunk else ""))
        elif isinstance(m, AIMessage):
            t = m.content
            t = t if isinstance(t, str) else (str(t) if t is not None else "")
            t = " ".join(t.split())[: chunk * 2]
            t = t[:chunk] + ("…" if len(t) > chunk else "")
            if not t and getattr(m, "tool_calls", None):
                names = [c.get("name") for c in m.tool_calls if isinstance(c, dict)]
                t = f"[tool: {', '.join(n for n in names if n)}]" if names else "[tool call]"
            turn.append("assistant: " + t)
    return "\n".join(turn) if turn else "(chưa có hội thoại)"


def _create_booking_tool_ok(messages: list) -> bool:
    for m in reversed(messages or []):
        if not isinstance(m, ToolMessage) or m.name != "create_booking":
            continue
        c = m.content
        s = c if isinstance(c, str) else str(c)
        if "[Tool lỗi]" in s or "error" in s.lower()[: 120]:
            return False
        return bool(s.strip())
    return False


def router_node(state: AgentState) -> dict[str, Any]:
    user_text = get_last_user_text(state)
    messages = list(state.get("messages", []))
    transcript = _format_transcript_for_router(messages)
    booking_on = (state.get("booking_stage") or "") == "open"
    state_hint = f"booking_flow_active: {'yes' if booking_on else 'no'}"
    prompt_body = f"{state_hint}\n\n[Recent conversation]\n{transcript}\n\n[Latest user message to classify]\n{user_text}"
    resp = llm.invoke(
        [SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=prompt_body)]
    )
    out_intent = (
        normalize_intent(resp.content) if isinstance(resp.content, str) else "consult"
    )

    booking_stage: str | None
    if out_intent == "booking":
        booking_stage = "open"
    else:
        booking_stage = None

    return {"intent": out_intent, "booking_stage": booking_stage}

def consult_agent_node(state: AgentState) -> dict[str, Any]:
    messages = _normalize_messages_for_provider(list(state.get("messages", [])))
    tools = [search_packages, get_package_detail,] # compare_packages, get_facilities]
    bound = llm.bind_tools(tools)
    resp = bound.invoke([
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{CONSULT_PROMPT}"),
        *messages,
    ])

    return {"messages": [resp], "consult_result": resp.content if isinstance(resp.content, str) else str(resp.content)}


def policy_agent_node(state: AgentState) -> dict[str, Any]:
    messages = _normalize_messages_for_provider(list(state.get("messages", [])))
    bound = llm.bind_tools([query_gym_policy])
    resp = bound.invoke(
        [SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{POLICY_PROMPT}"), *messages]
    )
    return {
        "messages": [resp],
        "policy_result": resp.content if isinstance(resp.content, str) else str(resp.content),
    }


def booking_agent_node(state: AgentState) -> dict[str, Any]:
    user_text = get_last_user_text(state)
    now_vn = get_vietnam_now.invoke({})
    messages = _normalize_messages_for_provider(list(state.get("messages", [])))
    tools = [get_vietnam_now, create_booking]
    bound = llm.bind_tools(tools)
    resp = bound.invoke([
        SystemMessage(
            content=(
                f"{SYSTEM_PROMPT}\n\n{BOOKING_PROMPT}\n\n"
                f"Thời gian Việt Nam hiện tại: {json.dumps(now_vn, ensure_ascii=False)}"
            )
        ),
        *messages,
    ])

    out: dict[str, Any] = {
        "messages": [resp],
        "booking_result": resp.content if isinstance(resp.content, str) else str(resp.content),
    }
    if _create_booking_tool_ok(list(messages)):
        out["booking_stage"] = None
    return out

