"""Checkout flow — POST /checkout_sessions create, status, complete, cancel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..razorpay_client.orders import create_order, fetch_order
from ..razorpay_client.payments import fetch_payment
from ..settings import settings
from .catalog import _load_catalog

router = APIRouter(prefix="/api", tags=["checkout"])


@router.get("/razorpay_key")
def get_razorpay_key():
    """Return the Razorpay publishable key for client-side checkout."""
    return {"key_id": settings.razorpay_key_id}


class CartItem(BaseModel):
    item_id: str
    quantity: int = Field(default=1, ge=1)


class CreateCheckoutRequest(BaseModel):
    items: list[CartItem]
    buyer_agent_id: str = "anonymous"


class CheckoutSession(BaseModel):
    session_id: str
    razorpay_order_id: str
    items: list[dict]
    total_paise: int
    currency: str
    status: str  # not_ready_for_payment | ready_for_payment | completed | canceled
    created_at: str


# change to postgres in prod.
_sessions: dict[str, dict[str, Any]] = {}


def _build_catalog_index() -> dict[str, dict]:
    """Index catalog items by id for fast lookup."""
    return {p["id"]: p for p in _load_catalog()}


def _session_to_response(session_data: dict) -> CheckoutSession:
    """Extract only the fields CheckoutSession expects."""
    fields = CheckoutSession.model_fields
    return CheckoutSession(**{k: v for k, v in session_data.items() if k in fields})


@router.post("/checkout_sessions", response_model=CheckoutSession)
def create_checkout_session(body: CreateCheckoutRequest, db: Session = Depends(get_db)):
    """Create a checkout session. Validates items against catalog, creates a
    Razorpay order, and logs the event."""
    catalog = _build_catalog_index()
    items_out = []
    total = 0

    for cart_item in body.items:
        product = catalog.get(cart_item.item_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Unknown item: {cart_item.item_id}")
        line_total = product["price_paise"] * cart_item.quantity
        items_out.append(
            {
                "id": product["id"],
                "name": product["name"],
                "price_paise": product["price_paise"],
                "quantity": cart_item.quantity,
                "line_total_paise": line_total,
            }
        )
        total += line_total

    receipt = f"checkout_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    razorpay_order = create_order(amount_paise=total, receipt=receipt)
    session_id = razorpay_order["id"]

    session_data = {
        "session_id": session_id,
        "razorpay_order_id": razorpay_order["id"],
        "items": items_out,
        "total_paise": total,
        "currency": "INR",
        "status": "ready_for_payment",
        "created_at": datetime.now(UTC).isoformat(),
        "buyer_agent_id": body.buyer_agent_id,
    }
    _sessions[session_id] = session_data

    write_audit_row(
        db,
        actor="service",
        action="checkout_session_created",
        entity_type="checkout_session",
        entity_id=session_id,
        payload={
            "items": [i["id"] for i in items_out],
            "total_paise": total,
            "razorpay_order_id": razorpay_order["id"],
        },
        result="success",
    )

    return _session_to_response(session_data)


@router.get("/checkout_sessions/{session_id}", response_model=CheckoutSession)
def get_checkout_session(session_id: str):
    """Get current checkout session state."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.post("/checkout_sessions/{session_id}/complete")
def complete_checkout(session_id: str, db: Session = Depends(get_db)):
    """Complete checkout — verify payment on Razorpay, update session, log result."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    razorpay_order = fetch_order(session["razorpay_order_id"])
    order_status = razorpay_order.get("status", "unknown")

    # Payment failed — declined, expired, or cancelled
    if order_status in ("failed", "cancelled", "expired"):
        session["status"] = "failed"

        write_audit_row(
            db,
            actor="service",
            action="checkout_failed",
            entity_type="checkout_session",
            entity_id=session_id,
            payload={
                "razorpay_order_id": session["razorpay_order_id"],
                "razorpay_status": order_status,
                "amount_paise": session["total_paise"],
            },
            result="failure",
            error_reason=f"Razorpay order status: {order_status}",
        )
        raise HTTPException(
            status_code=402,
            detail={
                "session_id": session_id,
                "status": "failed",
                "razorpay_status": order_status,
                "message": (
                    f"Payment failed: {order_status}. "
                    "Try again or use a different payment method."
                ),
            },
        )

    # Check if order is paid
    if order_status == "paid":
        payment_ids = razorpay_order.get("payments", [])
        payment_info = {}
        if payment_ids:
            pid = payment_ids[0] if isinstance(payment_ids[0], str) else payment_ids[0].get("id")
            if pid:
                payment_info = fetch_payment(pid)

        session["status"] = "completed"

        write_audit_row(
            db,
            actor="service",
            action="checkout_completed",
            entity_type="checkout_session",
            entity_id=session_id,
            payload={
                "razorpay_order_id": session["razorpay_order_id"],
                "payment_id": payment_info.get("id"),
                "payment_status": payment_info.get("status"),
                "amount_paise": session["total_paise"],
            },
            result="success",
        )
        return {
            "session_id": session_id,
            "status": "completed",
            "razorpay_order_id": session["razorpay_order_id"],
            "message": "Payment confirmed",
        }

    # Not yet paid — return ready state
    raise HTTPException(
        status_code=400,
        detail={
            "session_id": session_id,
            "status": order_status,
            "message": "Order not yet paid. Complete payment via Razorpay checkout.",
        },
    )


@router.post("/checkout_sessions/{session_id}/cancel")
def cancel_checkout(session_id: str, db: Session = Depends(get_db)):
    """Cancel a checkout session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["status"] = "canceled"

    write_audit_row(
        db,
        actor="service",
        action="checkout_canceled",
        entity_type="checkout_session",
        entity_id=session_id,
        payload={"razorpay_order_id": session["razorpay_order_id"]},
        result="success",
    )

    return {"session_id": session_id, "status": "canceled", "message": "Checkout canceled"}
