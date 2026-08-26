from __future__ import annotations
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

Intent = Literal["consult", "policy", "booking", "off_topic"]

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]

    # Routing 
    intent: Optional[Intent]

    # Booking flow
    booking_info: Optional[dict]
    booking_stage: Optional[str]
    booking_missing_fields: Optional[list[str]]
    booking_confirmed: Optional[bool]
    booking_result: Optional[dict]

    # Policy RAG
    policy_result: Optional[str]

    # Guardrails/escation
    safe: Optional[bool]
    escalate: Optional[bool]
    reason: Optional[str]
