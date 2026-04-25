from __future__ import annotations

from langchain_core.tools import tool

from tools.client import api_get


@tool
def get_package_detail(package_id: str):
    """Get full package detail by package code."""
    return api_get(f"/packages/{package_id}")
