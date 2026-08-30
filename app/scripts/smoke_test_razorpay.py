"""Throwaway script — prove test-mode Razorpay order creation works.

Usage:
    cd app && source .venv/bin/activate
    RAZORPAY_KEY_ID=rzp_test_xxx RAZORPAY_KEY_SECRET=xxx python scripts/smoke_test_razorpay.py

If this prints an order ID, Phase 1 Issue #1 is done.
"""

import os
import sys

# Ensure app/ is on the path so we can import service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from service.razorpay_client.orders import create_order  # noqa: E402


def main():
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        print("ERROR: Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in env or .env file")
        print("       Get test keys from https://dashboard.razorpay.com/app/keys")
        sys.exit(1)

    print(f"Using Razorpay key: {key_id[:12]}...")

    try:
        order = create_order(amount_paise=1000, currency="INR", receipt="smoke_test_001")
        print("SUCCESS — Order created!")
        print(f"  Order ID:  {order['id']}")
        print(f"  Amount:    {order['amount']} paise")
        print(f"  Currency:  {order['currency']}")
        print(f"  Status:    {order['status']}")
    except Exception as e:
        print(f"FAILED — {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
