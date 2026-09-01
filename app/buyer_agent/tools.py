"""Buyer agent tools — HTTP calls to the merchant agent API.

Modular design:
- Catalog + checkout tools live here (HTTP-based, talk to the merchant API).
- Payment tools (payment link, test card) live in ``payment_tools.py``.
- Both are re-exported via ``TOOL_DEFINITIONS`` and ``TOOL_FUNCTIONS``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from service.settings import settings

from .payment_tools import PAYMENT_TOOL_DEFINITIONS, PAYMENT_TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

_BASE = settings.service_url.rstrip("/")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        resp = httpx.post(f"{_BASE}{path}", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("POST %s returned %d", path, e.response.status_code)
        try:
            return e.response.json()
        except Exception:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except httpx.RequestError as e:
        logger.warning("POST %s failed: %s", path, e)
        return {"error": f"Request failed: {e}"}


def _get(path: str) -> dict[str, Any]:
    try:
        resp = httpx.get(f"{_BASE}{path}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("GET %s returned %d", path, e.response.status_code)
        try:
            return e.response.json()
        except Exception:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except httpx.RequestError as e:
        logger.warning("GET %s failed: %s", path, e)
        return {"error": f"Request failed: {e}"}


# ---------------------------------------------------------------------------
# Tool implementations (called by the agent loop)
# ---------------------------------------------------------------------------

def search_catalog(query: str) -> str:
    """Search the merchant catalog for products matching a query."""
    data = _get("/api/catalog")
    products = data.get("products", [])
    query_lower = query.lower()
    matches = [
        p for p in products
        if query_lower in p["name"].lower() or query_lower in p.get("description", "").lower()
    ]
    if not matches:
        matches = products  # return everything if no match
    return json.dumps({"matches": matches, "total": len(matches)})


def create_checkout_session(items: list[dict[str, Any]], buyer_agent_id: str = "llm-agent") -> str:
    """Create a checkout session with the given items."""
    body = {"items": items, "buyer_agent_id": buyer_agent_id}
    result = _post("/api/checkout_sessions", body)
    return json.dumps(result)


def complete_checkout(session_id: str) -> str:
    """Complete payment for a checkout session.

    Uses polling fallback if webhook is delayed.
    Only succeeds after the Razorpay order has been paid (via payment link or test card).
    """
    result = _post(f"/api/checkout_sessions/{session_id}/complete?poll=true", {})
    return json.dumps(result)


def cancel_checkout(session_id: str) -> str:
    """Cancel a checkout session."""
    result = _post(f"/api/checkout_sessions/{session_id}/cancel", {})
    return json.dumps(result)


def get_checkout_session(session_id: str) -> str:
    """Get the current state of a checkout session."""
    result = _get(f"/api/checkout_sessions/{session_id}")
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Catalog + checkout tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

_CATALOG_CHECKOUT_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": (
                "Search the merchant's product catalog. Returns matching products "
                "with id, name, price, and description. Use this first to find what's available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term, e.g. 'biriyani', 'milk', 'cheapest eggs'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checkout_session",
            "description": (
                "Create a checkout session with selected items. Returns a session ID "
                "and Razorpay order ID. Call this after selecting products."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_id": {
                                    "type": "string",
                                    "description": "Product ID from the catalog",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "How many to buy",
                                    "default": 1,
                                },
                            },
                            "required": ["item_id"],
                        },
                        "description": "List of items to purchase",
                    },
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_checkout",
            "description": (
                "Verify payment and start the human approval flow. The order must "
                "be PAID on Razorpay before calling this (use get_payment_link or "
                "pay_with_test_card first). If the result has status "
                "'pending_approval', STOP and report the approval_url to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The checkout session ID to complete",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_checkout",
            "description": (
                "Cancel a checkout session. "
                "Use if the user changes their mind or payment fails."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The checkout session ID to cancel",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_checkout_session",
            "description": "Get the current state of a checkout session (status, items, total).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The checkout session ID to look up",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Combined exports — all tools from catalog/checkout + payment modules
# ---------------------------------------------------------------------------

# OpenAI function-calling schemas (catalog + checkout + payment)
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    *_CATALOG_CHECKOUT_DEFINITIONS,
    *PAYMENT_TOOL_DEFINITIONS,
]

# Tool name → callable mapping
TOOL_FUNCTIONS: dict[str, Any] = {
    "search_catalog": search_catalog,
    "create_checkout_session": create_checkout_session,
    "complete_checkout": complete_checkout,
    "cancel_checkout": cancel_checkout,
    "get_checkout_session": get_checkout_session,
    **PAYMENT_TOOL_FUNCTIONS,
}
