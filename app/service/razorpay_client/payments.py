"""Razorpay Payments API wrapper."""

from __future__ import annotations

from .config import get_razorpay_client


def fetch_payment(payment_id: str) -> dict:
    """Fetch payment details by ID."""
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)


def capture_payment(*, payment_id: str, amount_paise: int) -> dict:
    """Capture a previously authorized payment (only needed for delayed capture)."""
    client = get_razorpay_client()
    return client.payment.capture(payment_id, amount_paise)


def create_refund(*, payment_id: str, amount_paise: int | None = None) -> dict:
    """Create a refund on a captured payment. Partial refund if amount_paise is set."""
    client = get_razorpay_client()
    payload: dict = {}
    if amount_paise is not None:
        payload["amount"] = amount_paise
    return client.payment.refund(payment_id, payload)
