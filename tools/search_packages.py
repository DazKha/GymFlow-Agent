from __future__ import annotations

from langchain_core.tools import tool

from tools.client import api_get


@tool
# def search_packages(query: str = "", tier: str = "", max_price: int = 0):
def search_packages(tier: str = "", max_price: int = 0):
    """Search membership packages by keyword, tier, and max monthly price."""
    params: dict[str, str | int] = {}
    # if query:
    #     params["q"] = query
    if tier:
        params["tier"] = tier
    if max_price > 0:
        params["max_price"] = max_price
    return api_get("/packages/search", params=params or None)
