"""Razorpay config — test-mode keys loaded from env."""

import razorpay

from ..settings import settings


def get_razorpay_client() -> razorpay.Client:
    """Return an initialised Razorpay client using test-mode keys."""
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RuntimeError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in env. "
            "Get test keys from https://dashboard.razorpay.com/app/keys"
        )
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
