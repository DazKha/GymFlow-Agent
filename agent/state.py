from __future__ import annotations
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

Intent = Literal["consult", "policy", "booking", "off_topic"]

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]

    # Routing 
    intent: Intent | None

    # Booking flow
    booking_info: dict | None
    booking_stage: str | None
    booking_missing_fields: list[str] | None
    booking_confirmed: bool | None
    booking_result: dict | None

    # Policy RAG
    policy_result: str | None

    # Guardrails/escation
    safe: bool | None
    escalate: bool | None
    reason: str | None