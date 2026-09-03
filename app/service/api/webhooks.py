"""Razorpay webhook receiver — handles payment.captured, payment.failed, and related events."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..db.models import CheckoutSession as CheckoutSessionRow
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook HMAC-SHA256 signature."""
    if not settings.razorpay_webhook_secret:
        # In dev mode without webhook secret, skip verification
        return True
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _update_session_status(db: Session, order_id: str, status: str) -> None:
    """Update checkout session status by Razorpay order ID.

    Only a session in a *payable* state (``awaiting_payment``) may be moved to
    ``completed`` by the payment provider. This keeps Razorpay as the authority
    over payment-provider state while MoneyOS stays the authority over business
    state: a webhook can confirm money moved, but it can never complete a
    session that was not authorised to accept payment.
    """
    row = db.query(CheckoutSessionRow).filter_by(razorpay_order_id=order_id).first()
    if row is None:
        logger.warning("No checkout session found for order %s", order_id)
        return

    if status == "completed":
        # Only release to completed from a payable state. A `pending_approval`
        # session can NOT be completed by the webhook — MoneyOS is the only
        # authority over approval, so the external event cannot bypass it.
        if row.status not in ("awaiting_payment",):
            logger.info(
                "Ignoring captured event for order %s in status %s (not payable)",
                order_id,
                row.status,
            )
            return

    row.status = status
    db.commit()


@router.post("/webhooks/razorpay")
@router.post("/app/webhooks")
@router.post("/app/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Receive Razorpay webhook events. Log to audit and update session status."""
    body = await request.body()

    if not _verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event", "unknown")
    payload = event.get("payload", {})

    # Extract key IDs from nested payload
    entity_id = None
    entity_type = None
    if "payment" in payload:
        entity_id = payload["payment"].get("id")
        entity_type = "payment"
    elif "order" in payload:
        entity_id = payload["order"].get("id")
        entity_type = "order"
    elif "refund" in payload:
        entity_id = payload["refund"].get("id")
        entity_type = "refund"

    # Determine result and update session on failures
    result = "success"
    error_reason = None

    # Razorpay nests entity data under payload.<entity>.entity
    payment_entity = payload.get("payment", {}).get("entity", {}) or {}
    order_entity = payload.get("order", {}).get("entity", {}) or {}
    order_id = payment_entity.get("order_id") or order_entity.get("id")

    if event_type == "payment.failed":
        result = "failure"
        error_reason = payment_entity.get("error_description") or "Payment failed"
        if order_id:
            _update_session_status(db, order_id, "failed")
    elif event_type == "payment.captured":
        result = "success"
        if order_id:
            _update_session_status(db, order_id, "completed")
    elif event_type == "order.paid":
        result = "success"
        if order_id:
            _update_session_status(db, order_id, "completed")
    elif event_type in ("order.failed", "order.cancelled", "order.expired"):
        result = "failure"
        error_reason = f"Order event: {event_type}"
        if order_id:
            _update_session_status(db, order_id, "failed")

    write_audit_row(
        db,
        actor="razorpay_webhook",
        action=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        result=result,
        error_reason=error_reason,
    )

    return {"status": "ok"}
