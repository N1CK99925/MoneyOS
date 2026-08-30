"""Razorpay Orders API wrapper."""

from __future__ import annotations

from .config import get_razorpay_client


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
