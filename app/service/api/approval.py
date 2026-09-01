"""GET/POST approval endpoints — the human gate for checkout.

Every money mutation here goes through ``write_audit_row`` (the only audit path).
The approval token is high-entropy (32 random bytes), single-use, and expiring —
acceptable as a demo authorization model, see the GATED_PAYMENTS_PRD §7.
"""
# ruff: noqa: E501  # inline HTML approval pages contain long template lines
from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..db.models import CheckoutSession
from ..razorpay_client.orders import cancel_order, fetch_order
from ..razorpay_client.payments import capture_payment
from ..settings import settings

router = APIRouter(prefix="/api", tags=["approval"])

# Statuses that terminate an approval — no further action allowed.
_TERMINAL = {"approved", "denied", "expired_approval", "completed", "canceled", "failed"}


def mint_approval_token() -> str:
    """Return a fresh high-entropy approval token (32 random bytes, hex)."""
    return secrets.token_hex(32)


def approval_url_for(token: str) -> str:
    """Public URL a human clicks to review/approve a pending checkout."""
    base = settings.service_url.rstrip("/")
    return f"{base}/api/approval/{token}"


def start_approval(db: Session, session: dict[str, Any]) -> dict[str, Any]:
    """Transition a session to pending_approval and return the approval context.

    Idempotent: if an approval is already pending, the existing token/URL is
    returned rather than minting a new one.
    """
    row = db.query(CheckoutSession).filter_by(session_id=session["session_id"]).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if row.status == "pending_approval" and row.approval_token:
        return _approval_context(session, row.approval_token, row.approval_deadline)

    token = mint_approval_token()
    deadline = datetime.now(UTC).isoformat()  # TTL compared against now at decision time
    url = approval_url_for(token)

    row.status = "pending_approval"
    row.approval_token = token
    row.approval_deadline = deadline
    row.approval_url = url
    db.commit()

    session["status"] = "pending_approval"

    write_audit_row(
        db,
        actor="service",
        action="approval_requested",
        entity_type="checkout_session",
        entity_id=session["session_id"],
        payload={
            "razorpay_order_id": session["razorpay_order_id"],
            "total_paise": session["total_paise"],
            "approval_url": url,
            "ttl_seconds": settings.approval_ttl_seconds,
        },
        result="pending",
    )
    return _approval_context(session, token, deadline)


def _approval_context(session: dict[str, Any], token: str, deadline: str | None) -> dict[str, Any]:
    return {
        "session_id": session["session_id"],
        "status": "pending_approval",
        "razorpay_order_id": session["razorpay_order_id"],
        "total_paise": session["total_paise"],
        "currency": session["currency"],
        "items": session["items"],
        "approval_url": approval_url_for(token),
        "approval_deadline": deadline,
    }


def _load_by_token(db: Session, token: str) -> CheckoutSession | None:
    return db.query(CheckoutSession).filter_by(approval_token=token).first()


def _expired(row: CheckoutSession) -> bool:
    raw = row.approval_deadline
    if not raw:
        return False
    try:
        created = datetime.fromisoformat(raw)
    except ValueError:
        return False
    age = (datetime.now(UTC) - created).total_seconds()
    return age > settings.approval_ttl_seconds


def _resolve_token(db: Session, token: str) -> CheckoutSession:
    """Return the session for a token, raising a structured HTTP error otherwise."""
    row = _load_by_token(db, token)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval token not found")
    if row.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Approval already decided ({row.status})")
    if _expired(row):
        row.status = "expired_approval"
        db.commit()
        write_audit_row(
            db,
            actor="service",
            action="approval_expired",
            entity_type="checkout_session",
            entity_id=row.session_id,
            payload={"razorpay_order_id": row.razorpay_order_id, "total_paise": row.total_paise},
            result="failure",
            error_reason="approval deadline passed",
        )
        raise HTTPException(status_code=410, detail="Approval expired")
    return row


@router.get("/approval/{token}")
def approval_page(token: str, json: bool = False, db: Session = Depends(get_db)):
    """Render the human approval page (or JSON with `?json=true`)."""
    row = _load_by_token(db, token)
    if row is None:
        if json:
            return {"error": "approval_not_found", "message": "Approval token not found"}
        return HTML_NOT_FOUND

    import json as _json

    items = _json.loads(row.items) if row.items else []
    context = {
        "session_id": row.session_id,
        "status": row.status,
        "total_paise": row.total_paise,
        "currency": row.currency,
        "items": [
            {"id": it.get("id"), "name": it.get("name"), "quantity": it.get("quantity")}
            for it in items
        ],
        "expired": _expired(row) and row.status == "pending_approval",
    }

    if json:
        return context

    return _render_approval_html(context, token)


# Inline HTML pages — bare minimum per the PRD, not app polish.
HTML_NOT_FOUND = """<!doctype html><html><head><meta charset="utf-8"><title>Approval</title>
<style>body{font-family:system-ui,monospace;background:#f4f4f0;color:#111;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:#fff;border:2px solid #111;padding:2.5rem;max-width:440px;width:100%;box-shadow:8px 8px 0 #111}
h1{font-size:1.4rem;margin:0 0 .4rem}b{font-size:2rem}</style></head>
<body><div class="card"><h1>Approval</h1><p>This approval link is invalid or has already been used.</p></div></body></html>"""


def _render_approval_html(ctx: dict[str, Any], token: str) -> str:
    total_inr = ctx["total_paise"] / 100
    if ctx["expired"]:
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>Approval expired</title>"
            "<style>body{font-family:system-ui,monospace;background:#f4f4f0;color:#111;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
            ".card{background:#fff;border:2px solid #111;padding:2.5rem;max-width:440px;"
            "width:100%;box-shadow:8px 8px 0 #111}"
            "h1{font-size:1.4rem;margin:0 0 .4rem}</style></head>"
            "<body><div class=\"card\"><h1>Approval expired</h1>"
            "<p>This approval link has expired. No money was moved.</p></div></body></html>"
        )

    items_html = "".join(
        f"<li><b>{it.get('name')}</b> &times;{it.get('quantity', 1)}</li>" for it in ctx["items"]
    )
    session_id = ctx["session_id"]
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>Approve purchase</title>"
        "<style>"
        "body{font-family:system-ui,monospace;background:#f4f4f0;color:#111;"
        "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
        ".card{background:#fff;border:2px solid #111;padding:2.5rem;max-width:440px;"
        "width:100%;box-shadow:8px 8px 0 #111}"
        "h1{font-size:1.4rem;margin:0 0 .4rem}ul{padding-left:1.2rem}b{font-size:2rem}"
        ".row{display:flex;gap:1rem;margin-top:1.6rem}"
        "button{flex:1;padding:.8rem;font-weight:700;font-family:inherit;cursor:pointer;"
        "border:2px solid #111;font-size:1rem}"
        ".approve{background:#EDFF45;color:#111}.deny{background:#fff;color:#111}"
        ".meta{color:#555;font-size:.8rem;margin-top:1rem}"
        "</style></head>"
        "<body><div class=\"card\"><h1>Approve purchase</h1><ul>"
        f"{items_html}</ul><p>Total: <b>₹{total_inr:,.2f}</b> ({ctx['currency']})</p>"
        "<div class=\"row\">"
        '<button class="approve" onclick="post(\'approve\')">Approve</button>'
        '<button class="deny" onclick="post(\'deny\')">Deny</button>'
        "</div>"
        f"<div class=\"meta\">Session {session_id}</div></div>"
        "<script>"
        f"async function post(path){{const r=await fetch('/api/approval/{token}/'+path,"
        "{{method:'POST'}});const t=await r.text();"
        "document.body.innerHTML='<pre style=\"white-space:pre-wrap;padding:2rem\">'"
        "+t.replace(/</g,'&lt;')+'</pre>';}"
        "</script></body></html>"
    )


def _finalize_approved(db: Session, row: CheckoutSession) -> dict[str, Any]:
    """Capture the payment and mark the session completed."""
    payment_ids = fetch_order(row.razorpay_order_id).get("payments", [])
    payment_id = payment_ids[0] if payment_ids else None
    if payment_id:
        capture_payment(payment_id=payment_id, amount_paise=row.total_paise)

    row.status = "approved"
    db.commit()

    write_audit_row(
        db,
        actor="human_approval",
        action="approval_granted",
        entity_type="checkout_session",
        entity_id=row.session_id,
        payload={"razorpay_order_id": row.razorpay_order_id, "total_paise": row.total_paise},
        result="success",
    )

    row.status = "completed"
    db.commit()

    write_audit_row(
        db,
        actor="service",
        action="checkout_completed",
        entity_type="checkout_session",
        entity_id=row.session_id,
        payload={"razorpay_order_id": row.razorpay_order_id, "total_paise": row.total_paise},
        result="success",
    )
    return {
        "session_id": row.session_id,
        "status": "completed",
        "razorpay_order_id": row.razorpay_order_id,
        "message": "Payment approved and captured",
    }


@router.post("/approval/{token}/approve")
def approve(token: str, db: Session = Depends(get_db)):
    """Approve a pending checkout — capture the payment."""
    try:
        row = _resolve_token(db, token)
    except HTTPException:
        raise
    return _finalize_approved(db, row)


@router.post("/approval/{token}/deny")
def deny(token: str, db: Session = Depends(get_db)):
    """Deny a pending checkout — cancel the order, no capture."""
    try:
        row = _resolve_token(db, token)
    except HTTPException:
        raise

    cancel_order(row.razorpay_order_id)

    row.status = "denied"
    db.commit()

    write_audit_row(
        db,
        actor="human_approval",
        action="approval_denied",
        entity_type="checkout_session",
        entity_id=row.session_id,
        payload={"razorpay_order_id": row.razorpay_order_id, "total_paise": row.total_paise},
        result="failure",
        error_reason="denied by user",
    )
    return {
        "session_id": row.session_id,
        "status": "denied",
        "razorpay_order_id": row.razorpay_order_id,
        "message": "Purchase denied",
    }
