from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = (
    os.getenv("BACKEND_URL")
    or os.getenv("BASE_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))


class BackendAPIError(RuntimeError):
    """Raised when backend API returns non-2xx."""


def _build_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{BASE_URL}{path}"


def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    resp = requests.get(_build_url(path), params=params, timeout=TIMEOUT)
    if not resp.ok:
        raise BackendAPIError(f"GET {resp.url} failed: {resp.status_code} {resp.text}")
    return resp.json()


def api_post(path: str, payload: dict[str, Any]) -> Any:
    resp = requests.post(_build_url(path), json=payload, timeout=TIMEOUT)
    if not resp.ok:
        raise BackendAPIError(f"POST {resp.url} failed: {resp.status_code} {resp.text}")
    return resp.json()
