from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

from agent.state import AgentState

from agent.nodes import(
    input_guard_node,
    router_node,
    consult_agent_node,
    policy_agent_node,
    booking_agent_node,
)
from guardrails.output_guard import output_guard_node
from tools import (
    search_packages,
    get_package_detail,
    compare_packages,
    get_facilities,
    get_vietnam_now,
    create_booking,
)
from tools.query_gym_policy import query_gym_policy

def route_after_guard(state: AgentState) -> str:
    return "safe" if state.get("safe") else "unsafe"

def route_intent(state: AgentState) -> str:
    stage = (state.get("booking_stage") or "").lower()
    if stage in {"collecting", "confirming"}:
        return "booking"

    intent = state.get("intent", "consult")
    if intent == "off_topic":
        return "off_topic"
    return intent


def route_after_tools(state: AgentState) -> str:
    intent = state.get("intent", "consult")
    if intent == "booking":
        return "booking"
    if intent == "policy":
        return "policy"
    return "consult"

builder = StateGraph(AgentState)

builder.add_node("input_guard", input_guard_node)
builder.add_node("router", router_node)
builder.add_node("consult_agent", consult_agent_node)
builder.add_node("policy_agent", policy_agent_node)
builder.add_node("booking_agent", booking_agent_node)
builder.add_node("output_guard", output_guard_node)
builder.add_node(
    "tools",
    ToolNode(
        [
            search_packages,
            get_package_detail,
            compare_packages,
            get_facilities,
            get_vietnam_now,
            create_booking,
            query_gym_policy,
        ],
        handle_tool_errors=lambda e: f"[Tool lỗi] {type(e).__name__}: {e}",
    ),
)

builder.set_entry_point("input_guard")

builder.add_conditional_edges("input_guard", route_after_guard, {
    "safe": "router",
    "unsafe": "output_guard",
})

builder.add_conditional_edges("router", route_intent, {
    "consult": "consult_agent",
    "policy": "policy_agent",
    "booking": "booking_agent",
    "off_topic": "output_guard",
})

builder.add_conditional_edges("consult_agent", tools_condition, {
    "tools": "tools",
    "__end__": "output_guard",
})
builder.add_conditional_edges("policy_agent", tools_condition, {
    "tools": "tools",
    "__end__": "output_guard",
})
builder.add_conditional_edges("booking_agent", tools_condition, {
    "tools": "tools",
    "__end__": "output_guard",
})
builder.add_conditional_edges("tools", route_after_tools, {
    "consult": "consult_agent",
    "policy": "policy_agent",
    "booking": "booking_agent",
})

builder.add_edge("output_guard", END)

graph = builder.compile()
