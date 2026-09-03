"""Telegram delivery for MoneyOS — payment links and approval cards to a phone.

Telegram is used purely as a delivery/channel layer. Every function here is
guarded by config (``telegram_bot_token`` must be set) and fails silently on
error, so the core checkout/approval flow is never blocked by a notification.

This module talks to the Telegram Bot API over HTTP (httpx). It does NOT touch
any money state — buttons simply hand the caller back the same single-use
approval token already used by the web approval page, so the audit trail and
token semantics stay in ``service/api/approval.py`` unchanged.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from service import runtime_settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot"


# ---------------------------------------------------------------------------
# Low-level Bot API helpers
# ---------------------------------------------------------------------------

def _bot_url(method: str) -> str:
    """Absolute URL for a Telegram Bot API method."""
    token = runtime_settings.get_setting("telegram_bot_token")
    return f"{_TELEGRAM_API}{token}/{method}"


def _post(method: str, **payload: Any) -> dict[str, Any]:
    """Call a Telegram Bot API method. Returns the JSON body, or {} on failure."""
    if not runtime_settings.get_setting("telegram_bot_token"):
        return {}
    try:
        resp = httpx.post(_bot_url(method), json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("Telegram %s failed: HTTP %d %s", method, e.response.status_code, e.response.text[:200])
    except httpx.RequestError as e:
        logger.warning("Telegram %s request failed: %s", method, e)
    return {}


def _resolve_chat_id(delivery: str) -> str:
    """Pick the chat ID for a delivery target, defaulting customer -> merchant."""
    if delivery == "approval":
        return runtime_settings.get_setting("telegram_merchant_chat_id")
    # payment / default
    return (
        runtime_settings.get_setting("telegram_customer_chat_id")
        or runtime_settings.get_setting("telegram_merchant_chat_id")
    )


class _InlineButton:
    """Small builder so callers don't hand-write Bot API keyboard dicts."""

    def __init__(self, text: str, callback_data: str):
        self._data = {"text": text, "callback_data": callback_data}

    def build(self) -> dict[str, str]:
        return self._data


# ---------------------------------------------------------------------------
# High-level delivery
# ---------------------------------------------------------------------------

def send_payment_link(
    *,
    session_id: str,
    checkout_url: str,
    amount_paise: int = 0,
    item_name: str | None = None,
) -> bool:
    """Send a payment link to the customer's Telegram chat.

    Returns True if the message was sent, False otherwise (e.g. not configured).
    """
    chat_id = _resolve_chat_id("payment")
    if not _enabled(chat_id):
        return False

    amount = f" — ₹{amount_paise / 100:,.2f}" if amount_paise else ""
    label = f"{item_name}{amount}" if item_name else f"Order {session_id}"
    text = (
        f"🛒 MoneyOS — ready to pay\n\n{label}\n\n"
        f"Tap to complete payment:\n{checkout_url}"
    )
    return bool(_post("sendMessage", chat_id=chat_id, text=text))


def send_approval_card(
    *,
    session_id: str,
    items: list[dict[str, Any]] | None = None,
    total_paise: int = 0,
    approval_url: str = "",
) -> str | None:
    """Send an approve/deny card to the merchant's Telegram chat.

    Telegram limits ``callback_data`` to 64 bytes, so the buttons carry the
    *short* session id (not the 64-char approval token). The callback handler
    resolves the session id back to the single-use token server-side.

    Returns the Telegram message_id (needed later to edit the card with the
    result) or None if not sent.
    """
    chat_id = _resolve_chat_id("approval")
    if not _enabled(chat_id):
        return None

    lines = ["⚡ MoneyOS — purchase awaiting approval\n"]
    if items:
        for it in items:
            qty = it.get("quantity", 1)
            name = it.get("name", it.get("id", "item"))
            lines.append(f"• {qty} × {name}")
    if total_paise:
        lines.append(f"\nTotal: ₹{total_paise / 100:,.2f}")
    if approval_url:
        lines.append(f"\nOpen in browser: {approval_url}")
    lines.append("\nApprove or deny? (link expires in 5 min)")

    keyboard = {
        "inline_keyboard": [
            [
                _InlineButton("✅ Approve", f"approve:{session_id}").build(),
                _InlineButton("❌ Deny", f"deny:{session_id}").build(),
            ]
        ]
    }
    resp = _post(
        "sendMessage",
        chat_id=chat_id,
        text="\n".join(lines),
        reply_markup=keyboard,
    )
    msg_id = resp.get("result", {}).get("message_id")
    if msg_id is not None:
        return str(msg_id)
    return None


def edit_approval_result(
    *,
    message_id: str,
    outcome: str,
    detail: str = "",
) -> bool:
    """Replace a sent approval card with its final result (approved/denied/error)."""
    chat_id = _resolve_chat_id("approval")
    if not _enabled(chat_id):
        return False

    if outcome == "approved":
        text = "✅ Approved & captured.\nPayment captured on Razorpay."
    elif outcome == "denied":
        text = "❌ Denied.\nOrder cancelled, nothing captured."
    elif outcome == "expired":
        text = "⏱️ Expired.\nApproval TTL passed, no payment captured."
    else:
        text = f"⚠️ {detail or 'Could not process the action.'}"

    return bool(_post("editMessageText", chat_id=chat_id, message_id=int(message_id), text=text))


# ---------------------------------------------------------------------------
# Callback handling — shared by polling and webhook
# ---------------------------------------------------------------------------

_CALLBACK_PREFIXES = ("approve:", "deny:")


def handle_callback(callback_query: dict[str, Any]) -> dict[str, Any]:
    """Resolve a Telegram inline-keyboard callback into an approval action.

    ``callback_data`` is expected to be ``approve:<session_id>`` or
    ``deny:<session_id>``. The session id is short (well under Telegram's
    64-byte ``callback_data`` limit); it is resolved back to the single-use
    approval token server-side.
    Returns a dict the transport (polling/webhook) can use to edit the card.
    """
    data = (callback_query.get("data") or "").strip()
    message_id = callback_query.get("message", {}).get("message_id")

    if not data.startswith(_CALLBACK_PREFIXES):
        return {"ok": False, "error": "unknown_callback", "message_id": message_id}

    action, _, ref = data.partition(":")
    if not ref:
        return {"ok": False, "error": "missing_ref", "message_id": message_id}

    # Acknowledge the button press to Telegram (required for callback queries).
    query_id = callback_query.get("id")
    if query_id:
        _post("answerCallbackQuery", callback_query_id=query_id)

    return {
        "ok": True,
        "action": action,  # "approve" | "deny"
        "session_id": ref,
        "message_id": message_id,
    }


def resolve_approval_path(action: str, session_id: str) -> str | None:
    """Map an approval action to the MoneyOS approval endpoint path.

    Uses the by-session endpoint since the callback carries a session id
    rather than the (longer) approval token.
    """
    if action == "approve":
        return f"/api/approval/by-session/{session_id}/approve"
    if action == "deny":
        return f"/api/approval/by-session/{session_id}/deny"
    return None


def _enabled(chat_id: str) -> bool:
    return bool(runtime_settings.get_setting("telegram_bot_token") and chat_id)
