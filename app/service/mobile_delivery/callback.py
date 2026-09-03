"""Approval callback handling — turns a Telegram button tap into an approval action.

This is the bridge between Telegram (transport-agnostic) and the MoneyOS
approval API. It never mutates state itself: it resolves the button's action +
single-use token, POSTs to the same audited ``/api/approval/{token}/approve``
(or ``/deny``) endpoint the web page uses, and edits the Telegram card with the
result.

Both transports (long-polling and webhook) call :class:`CallbackHandler`; the
handler does not care how the callback_query arrived.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from service.settings import settings

from .telegram import (
    edit_approval_result,
    handle_callback,
    resolve_approval_path,
)

logger = logging.getLogger(__name__)


class CallbackHandler:
    """Process a Telegram callback_query by relaying it to the MoneyOS API."""

    def __init__(self, service_url: str | None = None):
        self.service_url = (service_url or settings.service_url).rstrip("/")

    def process(self, callback_query: dict[str, Any]) -> dict[str, Any]:
        """Handle one callback_query; edit the Telegram card with the outcome."""
        parsed = handle_callback(callback_query)
        if not parsed.get("ok"):
            return parsed

        action = parsed["action"]
        session_id = parsed["session_id"]
        message_id = parsed.get("message_id")
        path = resolve_approval_path(action, session_id)
        if path is None:
            return {"ok": False, "error": "unsupported_action", "action": action}

        status_code, body = self._call_approval(path)

        # Map the HTTP status to a card outcome.
        outcome: str
        approved_statuses = ("awaiting_payment", "approved", "completed")
        if status_code == 200 and body.get("status") in approved_statuses:
            outcome = "approved"
        elif status_code == 200 and body.get("status") == "denied":
            outcome = "denied"
        elif status_code == 410:
            outcome = "expired"
        else:
            outcome = "error"

        detail = body.get("message") or body.get("detail") or f"HTTP {status_code}"
        if message_id:
            edit_approval_result(message_id=message_id, outcome=outcome, detail=str(detail))

        return {
            "ok": True,
            "action": action,
            "status_code": status_code,
            "outcome": outcome,
            "detail": detail,
        }

    def _call_approval(self, path: str) -> tuple[int, dict[str, Any]]:
        """POST to an approval endpoint. Returns (status_code, json_body)."""
        try:
            resp = httpx.post(f"{self.service_url}{path}", timeout=30)
            try:
                body = resp.json()
            except ValueError:
                body = {}
            return resp.status_code, body
        except httpx.RequestError as e:
            logger.warning("Approval relay to %s failed: %s", path, e)
            return 0, {"message": f"could not reach service: {e}"}
