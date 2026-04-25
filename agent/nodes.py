from langchain_gradient import ChatGradient

import json
import os
import re
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

# llm = ChatGradient(
#     model="openai-gpt-4o",
#     temperature=0.0,
#     api_key=(
#         os.getenv("DIGITALOCEAN_INFERENCE_KEY")
#         or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
#     ),
# )

api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY") or os.getenv("GRADIENT_MODEL_ACCESS_KEY")
llm = ChatGradient(model="openai-gpt-4o", api_key=api_key)


def _normalize_messages_for_provider(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Normalize tool message payloads and drop dangling tool-call turns."""
    normalized: list[BaseMessage] = []
    observed_tool_ids: set[str] = set()
    pending_tool_call_ids: list[str] = []

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

        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                call_ids = [
                    c.get("id")
                    for c in tool_calls
                    if isinstance(c, dict) and isinstance(c.get("id"), str) and c.get("id")
                ]
                if call_ids and all(cid in observed_tool_ids for cid in call_ids):
                    normalized.append(msg)
                elif call_ids:
                    # Keep only the most recent pending call IDs. Older unresolved calls
                    # will break provider validation on subsequent turns.
                    pending_tool_call_ids = call_ids
                    normalized.append(msg)
                else:
                    normalized.append(msg)
            else:
                normalized.append(msg)
            continue

        normalized.append(msg)

    # If the latest AI tool call is still unresolved in memory, drop that AI turn.
    # This prevents "tool_calls must be followed by tool messages" errors.
    if pending_tool_call_ids and not all(cid in observed_tool_ids for cid in pending_tool_call_ids):
        normalized = [m for m in normalized if not (isinstance(m, AIMessage) and (getattr(m, "tool_calls", None) or []))]

    return normalized


def input_guard_node(state: AgentState) -> dict[str, Any]:
    text = get_last_user_text(state)

    if not text or not text.strip():
        return {
            "safe": False,
            "reason": "empty_input",
            "messages": [AIMessage(content="Mình chưa nhận được nội dung câu hỏi, bạn thử gửi lại nhé 😊")],
        }

    lowered = text.lower()
    injection_markers = [
        "ignore previous instructions",
        "ignore all instructions",
        "system prompt",
        "jailbreak",
        "developer message",
    ]
    if any(marker in lowered for marker in injection_markers):
        return {
            "safe": False,
            "reason": "prompt_injection",
            "messages": [AIMessage(content="Xin lỗi, mình không thể xử lý yêu cầu này.")],
        }

    # Optional lightweight off-topic check can be refined later.
    # Keep fail-open for now to avoid blocking legitimate gym-related questions.
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


def _explicit_non_booking_pivot(user_text: str) -> bool:
    """User is clearly back to product/policy, not a booking step."""
    t = (user_text or "").strip()
    if len(t) < 5:
        return False
    low = t.lower()
    if any(
        p in low
        for p in (
            "gói tập nào",
            "gói nào",
            "giá bao nhiêu",
            "so sánh gói",
            "có mấy gói",
            "gói rẻ",
            "gói cao cấp",
            "hỏi thêm gói",
            "máy tập nào",
            "có bể bơi",
            "có bơi",
            "chính sách",
            "hoàn tiền",
            "nội quy",
        )
    ) and "đặt lịch" not in low and "lịch tập" not in low and "book" not in low:
        return len(t) > 20 or "?" in t
    if len(t) > 100 and "?" in t and "xác nhận" not in low and re.search(
        r"giá|gói|máy|bơi|tập", low
    ):
        return True
    return False


def _stays_in_booking_flow(user_text: str, state: AgentState) -> bool:
    if (state.get("booking_stage") or "") != "open":
        return False
    t = (user_text or "").strip()
    if not t or _explicit_non_booking_pivot(t):
        return False
    low = t.lower()
    if re.search(r"0[3-9]\d{7,8}\b", t):
        return True
    if len(t) < 55 and re.search(
        r"^(dạ|vâng|ok|oke|chốt|ừm?|vậy)\s*(\s*ạ|em)?\s*[!.?…]*$|"
        r"đúng(\s+(vậy|ạ|rồi))?|chính(\s*xác)?|xác nhận|đồng ý|"
        r"^dạ[\s,]+|^dạ a\b|^dạ e\b|^\s*ok\w*",
        low,
    ):
        return True
    if len(t) < 90 and re.search(
        r"\d{1,2}\s*(h|giờ|g)\b|tối|trưa|sáng|chiều|hôm nay|ngày mai|mai\b|mốt|"
        r"tham quan|tập thử|đặt lịch",
        low,
    ):
        return True
    if len(t) < 30 and t.count(",") >= 1 and re.search(r"\d", t):
        return True
    return False


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
    raw = (
        normalize_intent(resp.content) if isinstance(resp.content, str) else "consult"
    )
    if raw in {"policy", "booking", "consult"} and raw:
        out_intent: str = raw
    else:
        out_intent = "consult"

    if (state.get("booking_stage") or "") == "open" and out_intent == "consult" and _stays_in_booking_flow(
        user_text, state
    ):
        out_intent = "booking"

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

