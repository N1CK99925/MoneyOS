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

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..db.models import CheckoutSession
from ..razorpay_client.orders import cancel_order, fetch_order
from ..razorpay_client.payments import capture_payment
from ..settings import settings
from ..mobile_delivery import send_approval_card

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

    # Notify the merchant on Telegram (config-gated, non-blocking).
    # Buttons carry the short session id (not the 64-char token) to stay under
    # Telegram's 64-byte callback_data limit; resolved back to the token by the
    # by-session endpoints below.
    send_approval_card(
        session_id=session["session_id"],
        items=session.get("items"),
        total_paise=session["total_paise"],
        approval_url=url,
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
        return Response(content=HTML_NOT_FOUND, media_type="text/html")

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

    return Response(content=_render_approval_html(context, token), media_type="text/html")


# Inline HTML pages — bare minimum per the PRD, not app polish.
HTML_NOT_FOUND = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<title>Approval — MoneyOS</title>'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    '<style>'
    '*{margin:0;padding:0;box-sizing:border-box}'
    'body{font-family:"Inter",system-ui,sans-serif;background:#F4F4F0;color:#111;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;padding:1rem}'
    '.card{background:#fff;border:2px solid #111;padding:3rem 2.5rem;max-width:440px;width:calc(100% - 2rem);box-shadow:8px 8px 0 #111;text-align:center}'
    '.icon{width:48px;height:48px;border-radius:50%;background:#f8f9fa;border:2px solid #ddd;display:flex;align-items:center;justify-content:center;margin:0 auto 1.2rem;font-size:1.4rem}'
    'h1{font-family:"DM Serif Display",serif;font-size:1.6rem;margin-bottom:0.5rem}'
    'p{color:#666;font-size:0.9rem;line-height:1.6}'
    '</style></head>'
    '<body><div class="card">'
    '<div class="icon">🔗</div>'
    '<h1>Link Not Found</h1>'
    '<p>This approval link is invalid or has already been used.</p>'
    '</div></body></html>'
)


def _render_approval_html(ctx: dict[str, Any], token: str) -> str:
    total_inr = ctx["total_paise"] / 100
    if ctx["expired"]:
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Approval Expired — MoneyOS</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'body{font-family:"Inter",system-ui,sans-serif;background:#F4F4F0;color:#111;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}'
            '.card{background:#fff;border:2px solid #111;padding:3rem 2.5rem;max-width:440px;width:calc(100% - 2rem);box-shadow:8px 8px 0 #111;text-align:center}'
            '.icon{width:48px;height:48px;border-radius:50%;background:#f8d7da;border:2px solid #dc3545;display:flex;align-items:center;justify-content:center;margin:0 auto 1.2rem;font-size:1.4rem}'
            'h1{font-family:"DM Serif Display",serif;font-size:1.6rem;margin-bottom:0.5rem}'
            'p{color:#666;font-size:0.9rem;line-height:1.6}'
            '</style></head>'
            '<body><div class="card">'
            '<div class="icon">⏱</div>'
            '<h1>Approval Expired</h1>'
            '<p>This approval link has expired. No payment was captured.</p>'
            '</div></body></html>'
        )

    items_html = "".join(
        f"<tr><td class='item-name'>{it.get('name')}</td><td class='item-qty'>×{it.get('quantity', 1)}</td><td class='item-price'>₹{it.get('price_paise', 0) / 100:,.0f}</td></tr>"
        for it in ctx["items"]
    )
    session_id = ctx["session_id"]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Approve Purchase — MoneyOS</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        '<style>'
        '*{margin:0;padding:0;box-sizing:border-box}'
        'body{font-family:"Inter",system-ui,sans-serif;background:#F4F4F0;color:#111;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;padding:1rem}'
        '.card{background:#fff;border:2px solid #111;padding:2.5rem;max-width:460px;width:100%;box-shadow:8px 8px 0 #111}'
        '.badge{display:inline-flex;align-items:center;gap:6px;background:#EDFF45;color:#111;border:1px solid #111;border-radius:999px;padding:4px 14px;font-size:0.7rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:1.5rem}'
        'h1{font-family:"DM Serif Display",serif;font-size:1.7rem;margin-bottom:1.5rem;line-height:1.2}'
        'table{width:100%;border-collapse:collapse;margin-bottom:1.5rem}'
        'tr{border-bottom:1px solid #eee}'
        'td{padding:0.7rem 0;font-size:0.9rem}'
        '.item-name{font-weight:600}'
        '.item-qty{color:#999;text-align:center;width:40px}'
        '.item-price{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}'
        '.total-row{border-bottom:none;border-top:2px solid #111}'
        '.total-row td{padding-top:0.9rem;font-weight:700;font-size:1.1rem}'
        '.total-label{color:#666;font-weight:500}'
        '.total-val{font-variant-numeric:tabular-nums}'
        '.row{display:flex;gap:0.75rem;margin-top:1.8rem}'
        'button{flex:1;padding:0.9rem;font-weight:700;font-family:inherit;cursor:pointer;border:2px solid #111;font-size:0.95rem;border-radius:0;transition:transform 0.1s,box-shadow 0.1s}'
        'button:active{transform:translate(2px,2px);box-shadow:none}'
        '.approve{background:#EDFF45;color:#111}'
        '.approve:hover{background:#e5f53e}'
        '.deny{background:#fff;color:#111}'
        '.deny:hover{background:#f4f4f0}'
        '.meta{color:#999;font-size:0.72rem;margin-top:1.2rem;font-family:monospace;letter-spacing:0.02em}'
        '.shield{display:flex;align-items:center;justify-content:center;gap:6px;color:#999;font-size:0.75rem;margin-top:1rem}'
        '</style></head>'
        '<body><div class="card">'
        '<div class="badge">⚡ Awaiting Approval</div>'
        '<h1>Approve this purchase?</h1>'
        '<table>'
        f'{items_html}'
        '<tr class="total-row">'
        f"<td class='total-label'>Total</td><td></td><td class='total-val'>₹{total_inr:,.2f}</td>"
        '</tr>'
        '</table>'
        '<div class="row">'
        '<button class="approve" onclick="post(\'approve\')">✓ Approve</button>'
        '<button class="deny" onclick="post(\'deny\')">✗ Deny</button>'
        '</div>'
        '<div class="shield">🔒 Single-use link · expires in 5 minutes</div>'
        f"<div class='meta'>{session_id}</div>"
        '</div>'
        '<script>'
        f"async function post(path){{const r=await fetch('/api/approval/{token}/'+path,{{method:'POST'}});const j=await r.json();"
        'document.body.innerHTML='
        "'<div style=\"max-width:460px;margin:0 auto;padding:3rem 2.5rem;text-align:center;font-family:Inter,system-ui,sans-serif\">'"
        "+('<div style=\"width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 1rem;font-size:1.4rem;background:'+(j.status==='completed'?'#d4edda;border:2px solid #28a745':'#f8d7da;border:2px solid #dc3545')+'\">'+(j.status==='completed'?'✅':'❌')+'</div>')"
        "+'<h1 style=\"font-family:DM Serif Display,serif;font-size:1.6rem;margin-bottom:0.5rem\">'+(j.status==='completed'?'Purchase Approved':'Purchase Denied')+'</h1>'"
        "+'<p style=\"color:#666;font-size:0.9rem\">'+(j.message||'')+'</p>'"
        "+'</div>'}"
        '</script>'
        '</body></html>'
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
    return _deny_row(db, row)


def _deny_row(db: Session, row: CheckoutSession) -> dict[str, Any]:
    """Shared deny logic given a resolved session row."""
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


def _load_by_session(db: Session, session_id: str) -> CheckoutSession | None:
    """Return the session row for a session id, or None."""
    return db.query(CheckoutSession).filter_by(session_id=session_id).first()


@router.post("/approval/by-session/{session_id}/approve")
def approve_by_session(session_id: str, db: Session = Depends(get_db)):
    """Approve a pending checkout addressed by session id (Telegram buttons).

    Resolves the session's single-use approval token and approves it.
    """
    row = _load_by_session(db, session_id)
    if row is None or not row.approval_token:
        raise HTTPException(status_code=404, detail="Approval session not found")
    try:
        resolved = _resolve_token(db, row.approval_token)
    except HTTPException:
        raise
    return _finalize_approved(db, resolved)


@router.post("/approval/by-session/{session_id}/deny")
def deny_by_session(session_id: str, db: Session = Depends(get_db)):
    """Deny a pending checkout addressed by session id (Telegram buttons)."""
    row = _load_by_session(db, session_id)
    if row is None or not row.approval_token:
        raise HTTPException(status_code=404, detail="Approval session not found")
    try:
        resolved = _resolve_token(db, row.approval_token)
    except HTTPException:
        raise
    return _deny_row(db, resolved)
