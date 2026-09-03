"""Telegram webhook endpoint — receives button taps when deployed (Vercel).

When MoneyOS runs on a serverless/public host, Telegram pushes callback updates
to this endpoint instead of us long-polling. Register it once with:

    curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<PUBLIC>/api/telegram/callback"

The endpoint calls the same :class:`CallbackHandler` as long-polling, so the
approval logic is identical in both modes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from service.mobile_delivery.callback import CallbackHandler

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_handler = CallbackHandler()


@router.post("/callback")
async def telegram_callback(request: Request):
    """Receive a Telegram update (typically a callback_query) and relay it."""
    try:
        update = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid_json"}

    callback_query = (update or {}).get("callback_query")
    if not callback_query:
        # Non-callback updates (messages, edits) are ignored.
        return {"ok": True}

    result = _handler.process(callback_query)

    # Telegram does not require a specific body, but a 200 signals receipt.
    return result
