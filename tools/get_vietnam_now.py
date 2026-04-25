from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool


@tool
def get_vietnam_now() -> dict:
    """Get current Vietnam date/time in Asia/Ho_Chi_Minh timezone."""
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    return {
        "timezone": "Asia/Ho_Chi_Minh",
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
    }
