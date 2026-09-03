"""Tests for the gated-payments model — spend policy + human approval of exceptions.

Model (approval reserved for over-budget exceptions, evaluated at create):
- Within budget  -> awaiting_payment (payable immediately, human pays via test card).
- Over budget    -> pending_approval (held; no payment link yet). On approve the
                    buyer is released to awaiting_payment; on deny/expire the
                    underlying order is cancelled and the purchase cannot happen.

Covers:
- Spend policy: over-budget create returns pending_approval, not a 403; within-budget
  returns awaiting_payment with a payment link.
- Approval flow: over-budget -> pending_approval -> approve -> awaiting_payment.
- Deny path:     over-budget -> pending_approval -> deny -> denied (order cancelled).
- Expired approval: TTL lapse releases the order and rejects with 410.
- complete_checkout: paid order -> completed (no post-payment approval).
- Audit rows written at every money-relevant step.
"""

from unittest.mock import patch

# Default spend cap is 60000 paise (₹600). Chicken Biriyani (item_001) is ₹350.
# 1x = ₹350 (within), 2x = ₹700 (over).
WITHIN_POLICY = [{"item_id": "item_001", "quantity": 1}]
OVER_POLICY = [{"item_id": "item_001", "quantity": 2}]

ORDER = {"id": "order_gate1", "amount": 35000, "currency": "INR", "status": "created"}


def _create(client, mock_create_order, items=WITHIN_POLICY, order_id="order_gate1"):
    mock_create_order.return_value = {**ORDER, "id": order_id}
    body = {"items": items, "buyer_agent_id": "test-agent"}
    return client.post("/api/checkout_sessions", json=body)


class TestSpendPolicy:
    @patch("service.api.checkout.create_order")
    def test_over_policy_enters_pending_approval(self, mock_create_order, client):
        resp = _create(client, mock_create_order, items=OVER_POLICY)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_approval"
        assert "approval_url" in data
        # The order is still created so it can be cancelled on deny/expire.
        mock_create_order.assert_called_once()
        # Over-budget session must NOT be payable yet.
        assert data.get("payment_url") is None or data.get("checkout_url") is None

    @patch("service.api.checkout.create_order")
    def test_over_policy_writes_flag_audit_row(self, mock_create_order, client):
        _create(client, mock_create_order, items=OVER_POLICY)
        audit = client.get("/api/audit?limit=50").json()
        flagged = [r for r in audit if r["action"] == "policy_flagged"]
        assert len(flagged) >= 1
        row = flagged[0]
        assert row["actor"] == "policy"
        assert row["result"] == "pending"
        assert "max_per_transaction" in row["error_reason"]

    @patch("service.api.checkout.create_order")
    def test_within_policy_is_awaiting_payment(self, mock_create_order, client):
        resp = _create(client, mock_create_order, items=WITHIN_POLICY)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "awaiting_payment"
        assert data["total_paise"] == 35000
        mock_create_order.assert_called_once()


class TestApprovalFlow:
    @patch("service.api.checkout.create_order")
    def test_run_approval(self, mock_create_order, client):
        """Over-budget: create -> pending_approval -> approve -> awaiting_payment."""
        resp = _create(client, mock_create_order, items=OVER_POLICY, order_id="order_ap1")
        assert resp.json()["status"] == "pending_approval"
        token = resp.json()["approval_url"].rstrip("/").split("/")[-1]

        # Approval page renders the human gate.
        page = client.get(f"/api/approval/{token}")
        assert page.status_code == 200
        assert "Approve" in page.text and "Deny" in page.text

        ok = client.post(f"/api/approval/{token}/approve")
        assert ok.status_code == 200
        assert ok.json()["status"] == "awaiting_payment"
        # Approval releases the hold; it does not itself pay.
        session = client.get("/api/checkout_sessions/order_ap1").json()
        assert session["status"] == "awaiting_payment"

        # Audit: requested -> granted -> payment_link_ready.
        audit = client.get("/api/audit?limit=50").json()
        actions = [r["action"] for r in audit]
        assert "policy_flagged" in actions
        assert "approval_requested" in actions
        assert "approval_granted" in actions
        assert "payment_link_ready" in actions

    @patch("service.api.approval.cancel_order")
    @patch("service.api.checkout.create_order")
    def test_approve_then_deny_not_reusable(self, mock_create, mock_cancel, client):
        resp = _create(client, mock_create, items=OVER_POLICY, order_id="order_ap2")
        token = resp.json()["approval_url"].rstrip("/").split("/")[-1]

        denied = client.post(f"/api/approval/{token}/deny")
        assert denied.status_code == 200
        assert denied.json()["status"] == "denied"
        mock_cancel.assert_called_once_with("order_ap2")

        audit = client.get("/api/audit?limit=50").json()
        assert any(r["action"] == "approval_denied" for r in audit)

        # Reusing the token must fail (single-use).
        again = client.post(f"/api/approval/{token}/approve")
        assert again.status_code == 409

    @patch("service.api.approval.cancel_order")
    @patch("service.api.checkout.create_order")
    def test_expired_approval_cancels_order_and_rejects(
        self, mock_create, mock_cancel, client, monkeypatch
    ):
        resp = _create(client, mock_create, items=OVER_POLICY, order_id="order_ap3")
        token = resp.json()["approval_url"].rstrip("/").split("/")[-1]

        # Force the token to be expired by shrinking the TTL to a negative window.
        monkeypatch.setattr("service.settings.settings.approval_ttl_seconds", -1)
        expired = client.post(f"/api/approval/{token}/approve")
        assert expired.status_code == 410
        assert "expired" in expired.json()["detail"].lower()
        # Expiry releases the underlying order so the hold doesn't linger.
        mock_cancel.assert_called_once_with("order_ap3")

        audit = client.get("/api/audit?limit=50").json()
        assert any(r["action"] == "approval_expired" for r in audit)

    def test_unknown_token_404(self, client):
        # The approval page (GET) renders a friendly HTML 200 for a human; only the
        # authorize actions (POST) reject an unknown token with 404.
        assert client.post("/api/approval/not_a_real_token/approve").status_code == 404
        assert client.post("/api/approval/not_a_real_token/deny").status_code == 404


class TestCompleteWithoutApproval:
    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_within_budget_paid_completes(self, mock_create, mock_fetch, client):
        """Within-budget: pay -> complete -> completed (no post-payment approval)."""
        resp = _create(client, mock_create, items=WITHIN_POLICY, order_id="order_paid1")
        assert resp.json()["status"] == "awaiting_payment"

        mock_fetch.return_value = {"status": "paid", "payments": ["pay_gate1"]}
        done = client.post("/api/checkout_sessions/order_paid1/complete")
        assert done.status_code == 200
        assert done.json()["status"] == "completed"

        session = client.get("/api/checkout_sessions/order_paid1").json()
        assert session["status"] == "completed"


class TestWebhookStateMachine:
    """A payment webhook must NOT bypass MoneyOS's approval state machine."""

    def _payment_captured_event(self, order_id: str, payment_id: str = "pay_x") -> dict:
        return {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "id": payment_id,
                    "entity": {"id": payment_id, "order_id": order_id},
                }
            },
        }

    @patch("service.api.approval.cancel_order")
    @patch("service.api.checkout.create_order")
    def test_webhook_cannot_complete_pending_approval(
        self, mock_create, mock_cancel, client, monkeypatch
    ):
        """Over-budget -> pending_approval; the webhook cannot force it to completed."""
        # Dev mode: skip signature verification so we can exercise the state guard.
        monkeypatch.setattr("service.settings.settings.razorpay_webhook_secret", "")
        resp = _create(client, mock_create, items=OVER_POLICY, order_id="order_wb1")
        assert resp.json()["status"] == "pending_approval"

        # A payment.captured event arrives for the still-pending order.
        event = self._payment_captured_event("order_wb1")
        r = client.post("/webhooks/razorpay", json=event)
        assert r.status_code == 200

        # MoneyOS remains in control: still pending_approval, not completed.
        session = client.get("/api/checkout_sessions/order_wb1").json()
        assert session["status"] == "pending_approval"

    @patch("service.api.checkout.create_order")
    def test_webhook_completes_awaiting_payment(self, mock_create, client, monkeypatch):
        """Within-budget -> awaiting_payment; webhook payment confirms completion."""
        monkeypatch.setattr("service.settings.settings.razorpay_webhook_secret", "")
        _create(client, mock_create, items=WITHIN_POLICY, order_id="order_wb2")
        assert client.get("/api/checkout_sessions/order_wb2").json()["status"] == "awaiting_payment"

        event = self._payment_captured_event("order_wb2")
        r = client.post("/webhooks/razorpay", json=event)
        assert r.status_code == 200

        session = client.get("/api/checkout_sessions/order_wb2").json()
        assert session["status"] == "completed"
