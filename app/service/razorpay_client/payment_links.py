"""Payment link generation — local checkout page URLs.

Razorpay's payment-link API creates a separate order disconnected from
the checkout session, so ``complete_checkout`` never sees it as paid.

Instead we generate a URL to our own ``/pay/{session_id}`` page that
loads Razorpay checkout.js with the session's order ID.  This keeps
the payment tied to the right order.
"""

from __future__ import annotations

import logging

from service.settings import settings

logger = logging.getLogger(__name__)


def create_payment_link(
    *,
    session_id: str,
    amount_paise: int,
    currency: str = "INR",
    item_name: str = "Item",
) -> dict:
    """Generate a local checkout page URL for the given session.

    Returns a URL the user can open to pay via Razorpay checkout.js.
    The page uses the session's existing order ID, so the payment is
    directly linked to the checkout session.

    Parameters
    ----------
    session_id : str
        The checkout session ID (= Razorpay order ID).
    amount_paise : int
        Amount in paise (for display purposes).
    currency : str
        Currency code.
    item_name : str
        Human-readable item name for the page.

    Returns
    -------
    dict
        ``{ checkout_url, session_id, message }`` on success.
    """
    base = settings.service_url.rstrip("/")
    checkout_url = f"{base}/pay/{session_id}"

    logger.info("Local checkout URL generated for session %s: %s", session_id, checkout_url)

    return {
        "checkout_url": checkout_url,
        "session_id": session_id,
        "amount_paise": amount_paise,
        "amount_inr": f"{amount_paise / 100:.2f}",
        "currency": currency,
        "message": (
            f"Payment page ready. Share this URL with the user to complete "
            f"payment: {checkout_url}"
        ),
    }


def fetch_payment_link(payment_link_id: str) -> dict:
    """No-op for compatibility — local checkout links don't have remote IDs."""
    return {"id": payment_link_id, "status": "local", "note": "Local checkout page"}


def cancel_payment_link(payment_link_id: str) -> dict:
    """No-op for compatibility — local checkout links can't be cancelled remotely."""
    return {"id": payment_link_id, "status": "cancelled", "note": "Local checkout page"}
