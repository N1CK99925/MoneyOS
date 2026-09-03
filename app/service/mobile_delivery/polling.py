"""Long-polling Telegram transport — consumes inbound button taps via getUpdates.

Unlike a webhook, long-polling needs no public URL: the bot pulls updates from
Telegram over an outbound connection. This is ideal for local/demo runs where
MoneyOS and the bot run on the same machine.

It runs a daemon thread started from the FastAPI lifespan. Config-gated: if
``telegram_bot_token`` is unset (or webhook mode is configured), it no-ops.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from service import runtime_settings
from service.settings import settings

from .callback import CallbackHandler

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot"
_POLL_TIMEOUT_SECONDS = 20  # long-poll: Telegram holds the connection up to 50s
_POLL_INTERVAL_SECONDS = 0.5


class PollingConsumer:
    """Background getUpdates consumer that relays callbacks to the MoneyOS API."""

    def __init__(self, *, service_url: str | None = None):
        self._service_url = (service_url or settings.service_url).rstrip("/")
        self._handler = CallbackHandler(service_url=self._service_url)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset: int | None = None

    # -- public lifecycle ---------------------------------------------------

    @property
    def enabled(self) -> bool:
        """Polling only runs when a bot token is set."""
        return bool(runtime_settings.get_setting("telegram_bot_token"))

    def start(self) -> None:
        """Start the background polling thread if not already running."""
        if not self.enabled:
            logger.info("Telegram polling disabled (no bot token) — skipping")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="telegram-polling",
            daemon=True,
        )
        self._thread.start()
        logger.info("Telegram long-polling started")

    def stop(self) -> None:
        """Signal the polling thread to stop (non-blocking)."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Telegram long-polling stopped")

    # -- internals ----------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:  # noqa: BLE001 — keep the loop alive on any error
                logger.exception("Telegram polling tick failed")
            time.sleep(_POLL_INTERVAL_SECONDS)

    def _tick(self) -> None:
        updates = self._fetch_updates()
        for update in updates:
            self._offset = int(update["update_id"]) + 1
            callback = update.get("callback_query")
            if callback:
                self._handler.process(callback)

    def _fetch_updates(self) -> list[dict[str, Any]]:
        token = runtime_settings.get_setting("telegram_bot_token")
        url = f"{_TELEGRAM_API}{token}/getUpdates"
        params: dict[str, Any] = {"timeout": _POLL_TIMEOUT_SECONDS}
        if self._offset is not None:
            params["offset"] = self._offset
        try:
            resp = httpx.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("result", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # 409 = another getUpdates consumer is active (e.g. a webhook).
                # If we were started in error, stop quietly rather than spin.
                logger.warning("Telegram 409 — webhook likely active; halting polling")
                self._stop_event.set()
            else:
                logger.warning("getUpdates HTTP %d: %s", e.response.status_code, e.response.text[:200])
        except httpx.RequestError as e:
            logger.warning("getUpdates request failed: %s", e)
        return []
