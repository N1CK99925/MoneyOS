"""Checkout flow — POST /checkout_sessions create, status, complete, cancel."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..db.models import CheckoutSession as CheckoutSessionRow
from ..razorpay_client.orders import create_order, fetch_order, poll_order_status
from ..razorpay_client.payments import fetch_payment
from ..settings import settings
from .approval import start_approval
from .catalog import _load_catalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["checkout"])


@router.get("/razorpay_key")
def get_razorpay_key():
    """Return the Razorpay publishable key for client-side checkout."""
    return {"key_id": settings.razorpay_key_id}


# ---------------------------------------------------------------------------
# Request / response models — single-item and multi-item both supported
# ---------------------------------------------------------------------------

class CreateCheckoutRequest(BaseModel):
    """Accepts both shapes:
    - Frontend: { item_id: "item_001", quantity: 1 }
    - Agent:    { items: [{ item_id: "item_001", quantity: 1 }], buyer_agent_id: "..." }
    """
    item_id: str | None = None
    quantity: int = Field(default=1, ge=1)
    items: list[dict[str, Any]] | None = None
    buyer_agent_id: str = "anonymous"


class CheckoutSessionResponse(BaseModel):
    session_id: str
    razorpay_order_id: str
    items: list[dict]
    total_paise: int
    currency: str
    status: str
    created_at: str


def _build_catalog_index() -> dict[str, dict]:
    return {p["id"]: p for p in _load_catalog()}


def _load_session(db: Session, session_id: str) -> dict[str, Any] | None:
    row = db.query(CheckoutSessionRow).filter_by(session_id=session_id).first()
    if not row:
        return None
    return {
        "session_id": row.session_id,
        "razorpay_order_id": row.razorpay_order_id,
        "items": json.loads(row.items),
        "total_paise": row.total_paise,
        "currency": row.currency,
        "status": row.status,
        "buyer_agent_id": row.buyer_agent_id,
        "created_at": row.created_at,
    }


def _save_session(db: Session, data: dict[str, Any]) -> None:
    row = db.query(CheckoutSessionRow).filter_by(session_id=data["session_id"]).first()
    if row:
        row.razorpay_order_id = data["razorpay_order_id"]
        row.items = json.dumps(data["items"])
        row.total_paise = data["total_paise"]
        row.currency = data["currency"]
        row.status = data["status"]
        row.buyer_agent_id = data.get("buyer_agent_id", "anonymous")
        row.created_at = data["created_at"]
    else:
        row = CheckoutSessionRow(
            session_id=data["session_id"],
            razorpay_order_id=data["razorpay_order_id"],
            items=json.dumps(data["items"]),
            total_paise=data["total_paise"],
            currency=data["currency"],
            status=data["status"],
            buyer_agent_id=data.get("buyer_agent_id", "anonymous"),
            created_at=data["created_at"],
        )
        db.add(row)
    db.commit()


def _session_response(data: dict[str, Any]) -> CheckoutSessionResponse:
    return CheckoutSessionResponse(
        session_id=data["session_id"],
        razorpay_order_id=data["razorpay_order_id"],
        items=data["items"],
        total_paise=data["total_paise"],
        currency=data["currency"],
        status=data["status"],
        created_at=data["created_at"],
    )


def _fetch_order_payments(order: dict) -> dict:
    payment_ids = order.get("payments", [])
    if not payment_ids:
        return {}
    pid = payment_ids[0] if isinstance(payment_ids[0], str) else payment_ids[0].get("id")
    if pid:
        return fetch_payment(pid)
    return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/checkout_sessions", response_model=CheckoutSessionResponse)
def create_checkout_session(body: CreateCheckoutRequest, db: Session = Depends(get_db)):
    """Create a checkout session. Accepts single item_id or multi-item list."""
    catalog = _build_catalog_index()

    # Normalize to items list
    if body.items:
        raw_items = body.items
    elif body.item_id:
        raw_items = [{"item_id": body.item_id, "quantity": body.quantity}]
    else:
        raise HTTPException(status_code=400, detail="Provide item_id or items list")

    items_out = []
    total = 0
    for ci in raw_items:
        item_id = ci.get("item_id") or ci.get("id")
        qty = ci.get("quantity", 1)
        product = catalog.get(item_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Unknown item: {item_id}")
        line_total = product["price_paise"] * qty
        items_out.append({
            "id": product["id"],
            "name": product["name"],
            "price_paise": product["price_paise"],
            "quantity": qty,
            "line_total_paise": line_total,
        })
        total += line_total

    # --- Spend policy (bounded spend) — enforced BEFORE creating any order. ---
    policy_max = settings.spend_policy_max_per_transaction_paise
    if policy_max > 0 and total > policy_max:
        write_audit_row(
            db,
            actor="policy",
            action="policy_rejected",
            entity_type="checkout_session",
            payload={
                "total_paise": total,
                "policy_max_paise": policy_max,
                "buyer_agent_id": body.buyer_agent_id,
                "item_ids": [i["id"] for i in items_out],
            },
            result="failure",
            error_reason=f"exceeds max_per_transaction {policy_max}",
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_violation",
                "message": (
                    f"Order ₹{total / 100:,.2f} exceeds the spend limit of "
                    f"₹{policy_max / 100:,.2f} for this buyer agent."
                ),
                "total_paise": total,
                "policy_max_paise": policy_max,
            },
        )

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
    _save_session(db, session_data)

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

    return _session_response(session_data)


@router.get("/checkout_sessions/{session_id}", response_model=CheckoutSessionResponse)
def get_checkout_session(session_id: str, db: Session = Depends(get_db)):
    session = _load_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_response(session)


@router.post("/checkout_sessions/{session_id}/complete")
def complete_checkout(
    session_id: str,
    poll: bool = False,
    db: Session = Depends(get_db),
):
    """Complete checkout — verify payment on Razorpay, update session, log result.

    Query param ``poll=true`` activates polling fallback.
    """
    session = _load_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    order_id = session["razorpay_order_id"]

    if poll:
        order = poll_order_status(order_id, max_attempts=5, interval_seconds=2.0)
    else:
        order = fetch_order(order_id)

    order_status = order.get("status", "unknown")

    if order_status in ("failed", "cancelled", "expired"):
        session["status"] = "failed"
        _save_session(db, session)

        write_audit_row(
            db,
            actor="service",
            action="checkout_failed",
            entity_type="checkout_session",
            entity_id=session_id,
            payload={
                "razorpay_order_id": order_id,
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
                "message": f"Payment failed: {order_status}. Try again or use a different payment method.",
            },
        )

    if order_status == "paid":
        # Payment is authorized on Razorpay. Per the gated-payments design,
        # we do NOT capture yet — we enter the human approval hold and return
        # an approval URL. Capture happens only on explicit human approval.
        return start_approval(db, session)

    raise HTTPException(
        status_code=400,
        detail={
            "session_id": session_id,
            "status": order_status,
            "message": "Order not yet paid. Complete payment via Razorpay checkout.",
        },
    )


class CancelCheckoutResponse(BaseModel):
    session_id: str
    status: str
    message: str


class FailCheckoutRequest(BaseModel):
    reason: str = "Payment failed"


@router.post("/checkout_sessions/{session_id}/fail")
def fail_checkout(session_id: str, body: FailCheckoutRequest, db: Session = Depends(get_db)):
    session = _load_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["status"] = "failed"
    _save_session(db, session)

    write_audit_row(
        db,
        actor="service",
        action="checkout_failed",
        entity_type="checkout_session",
        entity_id=session_id,
        payload={"razorpay_order_id": session["razorpay_order_id"], "reason": body.reason},
        result="failure",
        error_reason=body.reason,
    )

    return {"session_id": session_id, "status": "failed", "message": body.reason}


@router.post("/checkout_sessions/{session_id}/cancel")
def cancel_checkout(session_id: str, db: Session = Depends(get_db)):
    session = _load_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["status"] = "canceled"
    _save_session(db, session)

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
