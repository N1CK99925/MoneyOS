"""GET /pay/{session_id} — local checkout page for agent-initiated payments.

When the buyer agent creates a checkout session, it needs a URL the user
can open to pay.  This endpoint renders a self-contained HTML page that
loads the Razorpay checkout.js SDK and opens it immediately with the
session's order ID.

This avoids using Razorpay's payment-link API (which creates a separate
order disconnected from the checkout session).
"""
# ruff: noqa: E501  # inline HTML templates contain long lines

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.models import CheckoutSession
from ..settings import settings

router = APIRouter(tags=["checkout_page"])


@router.get("/pay/{session_id}")
def checkout_page(session_id: str, db: Session = Depends(get_db)) -> Response:
    """Render a Razorpay checkout page for the given session.

    The page loads checkout.js, pre-fills the order, and opens the modal.
    On success it redirects to a confirmation page; on failure it shows an error.
    """
    row = db.query(CheckoutSession).filter_by(session_id=session_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    import json as _json
    items = _json.loads(row.items) if row.items else []
    item_names = ", ".join(it.get("name", it.get("id", "")) for it in items)
    total_inr = f"{row.total_paise / 100:.2f}"

    # Build the Razorpay options as JS
    rzp_options = {
        "key": settings.razorpay_key_id,
        "amount": row.total_paise,
        "currency": row.currency,
        "name": "MoneyOS",
        "description": f"Order: {item_names}" if item_names else f"Order {session_id}",
        "order_id": row.razorpay_order_id,
        "modal": {"ondismiss": "window.location.href='/'"},
    }

    rzp_json = _json.dumps(rzp_options)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MoneyOS — Checkout</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #f4f4f0;
      color: #111;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }}
    .card {{
      background: #fff;
      border: 2px solid #111;
      padding: 2.5rem;
      max-width: 440px;
      width: 100%;
      box-shadow: 8px 8px 0 #111;
    }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.4rem; }}
    .items {{ font-size: 0.95rem; margin: 1rem 0; line-height: 1.6; }}
    .total {{ font-size: 2rem; font-weight: 700; margin: 1rem 0; }}
    .meta {{ color: #555; font-size: 0.8rem; margin-top: 1rem; }}
    #status {{
      margin-top: 1rem;
      padding: 0.8rem;
      border-radius: 8px;
      font-size: 0.9rem;
      display: none;
    }}
    #status.success {{
      display: block; background: #d4edda;
      border: 1px solid #28a745; color: #155724;
    }}
    #status.error {{
      display: block; background: #f8d7da;
      border: 1px solid #dc3545; color: #721c24;
    }}
    #status.pending {{
      display: block; background: #fff3cd;
      border: 1px solid #ffc107; color: #856404;
    }}
    .test-card {{
      margin-top: 1.2rem;
      padding: 1rem;
      background: #f8f9fa;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      font-size: 0.85rem;
    }}
    .test-card h3 {{ font-size: 0.9rem; margin-bottom: 0.5rem; }}
    .test-card table {{ width: 100%; border-collapse: collapse; }}
    .test-card td {{ padding: 3px 8px; font-family: monospace; font-size: 0.85rem; }}
    .test-card td:first-child {{ color: #555; font-family: system-ui; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>MoneyOS Checkout</h1>
    <div class="items">{item_names or session_id}</div>
    <div class="total">₹{total_inr}</div>
    <div id="status"></div>
    <div class="test-card">
      <h3>Test Card</h3>
      <table>
        <tr><td>Card</td><td>4111 1111 1111 1111</td></tr>
        <tr><td>Expiry</td><td>12/29</td></tr>
        <tr><td>CVV</td><td>123</td></tr>
      </table>
    </div>
    <div class="meta">Session: {session_id}</div>
  </div>

  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <script>
    const options = {rzp_json};

    options.handler = function (resp) {{
      const status = document.getElementById('status');
      status.className = 'pending';
      status.style.display = 'block';
      status.innerHTML = '✅ Payment successful — finalizing order…';

      // Auto-complete the checkout so the approval flow triggers
      fetch('/api/checkout_sessions/{session_id}/complete?poll=true', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
      }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
          if (data.status === 'pending_approval') {{
            status.className = 'pending';
            status.innerHTML = '⏳ Order submitted for approval.<br>'
              + (data.approval_url ? '<a href="' + data.approval_url + '" style="color:#856404">Open approval page</a>' : '');
          }} else if (data.status === 'completed') {{
            status.className = 'success';
            status.innerHTML = '✅ Order confirmed! Payment ID: ' + resp.razorpay_payment_id;
          }} else {{
            status.className = 'success';
            status.innerHTML = '✅ Payment received. Status: ' + data.status;
          }}
        }})
        .catch(function() {{
          status.className = 'success';
          status.innerHTML = '✅ Payment successful — refresh the agent chat to see updates.';
        }});
    }};

    options.modal.ondismiss = function () {{
      const status = document.getElementById('status');
      status.className = 'pending';
      status.style.display = 'block';
      status.innerHTML = 'Payment cancelled. You can close this page.';
    }};

    const rzp = new Razorpay(options);
    rzp.on('payment.failed', function (resp) {{
      const status = document.getElementById('status');
      status.className = 'error';
      status.style.display = 'block';
      status.innerHTML = '❌ Payment failed: ' + (resp.error?.description || 'Unknown error');
    }});
    rzp.open();
  </script>
</body>
</html>"""

    return Response(content=html, media_type="text/html")
