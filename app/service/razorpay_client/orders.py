"""Razorpay Orders API wrapper."""

from __future__ import annotations

import logging
import time

from .config import get_razorpay_client

logger = logging.getLogger(__name__)


def create_order(*, amount_paise: int, currency: str = "INR", receipt: str) -> dict:
    """Create a Razorpay order in test mode.

    Returns the full order dict from the Razorpay API.
    """
    client = get_razorpay_client()
    return client.order.create(
        {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,  # auto-capture
        }
    )


def fetch_order(order_id: str) -> dict:
    """Fetch order details by ID."""
    client = get_razorpay_client()
    return client.order.fetch(order_id)


def poll_order_status(
    order_id: str,
    *,
    max_attempts: int = 5,
    interval_seconds: float = 2.0,
) -> dict:
    """Poll Razorpay order status until it reaches a terminal state.

    Used as a fallback when webhooks are delayed or unavailable.
    Returns the final order dict.
    """
    for attempt in range(1, max_attempts + 1):
        order = fetch_order(order_id)
        status = order.get("status", "unknown")

        logger.info(
            "Poll attempt %d/%d — order %s status: %s",
            attempt,
            max_attempts,
            order_id,
            status,
        )

        if status in ("paid", "failed", "cancelled", "expired"):
            return order

        if attempt < max_attempts:
            time.sleep(interval_seconds)

    # Return whatever we have after max attempts
    return order
