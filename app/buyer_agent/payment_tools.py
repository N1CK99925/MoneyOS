"""Payment tools — modular tool definitions and implementations for buyer agent.

Provides two payment strategies:
1. ``get_payment_link``  — generates a local checkout page URL (/pay/{session_id})
2. ``pay_with_test_card`` — returns test card details + checkout URL for manual entry

Both tools produce a URL the user can open to pay via the Razorpay checkout.js
SDK.  The local checkout page keeps the payment linked to the session's order.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from service.razorpay_client.payment_links import create_payment_link
from service.razorpay_client.test_pay import prepare_test_payment
from service.settings import settings

logger = logging.getLogger(__name__)

_BASE = settings.service_url.rstrip("/")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_payment_link(
    *,
    session_id: str,
    amount_paise: int,
    item_name: str = "Item",
) -> str:
    """Generate a local checkout page URL for an existing session.

    The URL opens a page with Razorpay checkout.js pre-loaded, showing the
    order details and test card information.  The user enters card details
    on that page to authorize payment.

    Parameters
    ----------
    session_id : str
        The checkout session ID (= Razorpay order ID).
    amount_paise : int
        Total amount in paise (e.g. 35000 for ₹350).
    item_name : str
        Human-readable item name for the checkout page.

    Returns
    -------
    str
        JSON string with ``{ checkout_url, session_id }``.
    """
    try:
        result = create_payment_link(
            session_id=session_id,
            amount_paise=amount_paise,
            item_name=item_name,
        )
        logger.info("Checkout URL generated for session %s", session_id)
        return json.dumps({
            "checkout_url": result["checkout_url"],
            "session_id": session_id,
            "message": (
                f"Payment page ready: {result['checkout_url']}. "
                f"Share this URL with the user to complete payment."
            ),
        })
    except Exception as e:
        logger.exception("Failed to generate checkout URL for session %s", session_id)
        return json.dumps({
            "error": str(e),
            "message": "Failed to generate payment page.",
        })


def pay_with_test_card(
    *,
    session_id: str,
    amount_paise: int,
    card: str = "visa",
) -> str:
    """Return test card details and a checkout URL for completing payment.

    Provides the test card details and a URL the user can open to enter
    them in the Razorpay checkout modal.

    Parameters
    ----------
    session_id : str
        The checkout session ID.
    amount_paise : int
        Total amount in paise.
    card : str
        Test card type: ``visa``, ``mastercard``, or ``amex``.

    Returns
    -------
    str
        JSON string with test card details, checkout URL, and instructions.
    """
    result = prepare_test_payment(
        order_id=session_id,
        amount_paise=amount_paise,
        card=card,
    )
    if "error" in result:
        return json.dumps(result)

    checkout_url = f"{_BASE}/pay/{session_id}"

    result["checkout_url"] = checkout_url
    result["message"] = (
        f"Test card ready: {result['card']['display']} "
        f"({result['card']['network']}). "
        f"Open {checkout_url} and enter these details to authorize payment."
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema for litellm)
# ---------------------------------------------------------------------------

PAYMENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_payment_link",
            "description": (
                "Generate a payment page URL for an existing checkout session. "
                "The URL opens a Razorpay checkout page where the user enters "
                "card details to pay. Use this AFTER creating a checkout session "
                "and BEFORE calling complete_checkout."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The checkout session ID to generate a payment page for",
                    },
                    "amount_paise": {
                        "type": "integer",
                        "description": "Total amount in paise (e.g. 35000 for ₹350)",
                    },
                    "item_name": {
                        "type": "string",
                        "description": "Item name shown on the checkout page",
                        "default": "Item",
                    },
                },
                "required": ["session_id", "amount_paise"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pay_with_test_card",
            "description": (
                "Get test card details AND a checkout page URL for completing a "
                "Razorpay payment in test mode. Returns card number, expiry, CVV, "
                "and a URL to open for payment. Use when the user wants to pay "
                "with a test card."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The checkout session ID",
                    },
                    "amount_paise": {
                        "type": "integer",
                        "description": "Total amount in paise (e.g. 35000 for ₹350)",
                    },
                    "card": {
                        "type": "string",
                        "description": "Test card type",
                        "enum": ["visa", "mastercard", "amex"],
                        "default": "visa",
                    },
                },
                "required": ["session_id", "amount_paise"],
            },
        },
    },
]

# Map tool names to callables
PAYMENT_TOOL_FUNCTIONS: dict[str, Any] = {
    "get_payment_link": get_payment_link,
    "pay_with_test_card": pay_with_test_card,
}
