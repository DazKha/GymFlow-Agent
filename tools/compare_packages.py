from __future__ import annotations

from langchain_core.tools import tool

from tools.client import api_get


@tool
def compare_packages(package_ids: list[str]):
    """Compare at least two membership packages by package codes."""
    if len(package_ids) < 2:
        raise ValueError('package_ids must contain at least 2 values')
    return api_get('/packages/compare', params={'ids': ','.join(package_ids)})
