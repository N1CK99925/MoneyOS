"""Tests for the gated-payments additions — approval flow + spend policy.

Covers:
- Spend policy: 403 + audit row + no Razorpay order created.
- Approval flow happy path: complete -> pending_approval -> approve -> completed.
- Deny path: complete -> pending_approval -> deny -> denied.
- Expired approval: TTL lapse rejects with 410.
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


def _start_approval(client, mock_create_order, mock_fetch_order,
                    order_id="order_gate1", items=WITHIN_POLICY):
    """Create a session, drive complete to pending_approval, return (resp, token)."""
    _create(client, mock_create_order, items=items, order_id=order_id)
    mock_fetch_order.return_value = {"status": "paid", "payments": ["pay_gate1"]}
    resp = client.post(f"/api/checkout_sessions/{order_id}/complete")
    assert resp.status_code == 200
    token = resp.json()["approval_url"].rstrip("/").split("/")[-1]
    return resp, token


class TestSpendPolicy:
    @patch("service.api.checkout.create_order")
    def test_over_policy_returns_403_and_no_order(self, mock_create_order, client):
        resp = _create(client, mock_create_order, items=OVER_POLICY)
        assert resp.status_code == 403
        detail = resp.json()["detail"]
        assert detail["error"] == "policy_violation"
        assert detail["total_paise"] == 70000
        assert detail["policy_max_paise"] == 60000
        # No Razorpay order should even be attempted.
        mock_create_order.assert_not_called()

    @patch("service.api.checkout.create_order")
    def test_over_policy_writes_rejection_audit_row(self, mock_create_order, client):
        _create(client, mock_create_order, items=OVER_POLICY)
        audit = client.get("/api/audit?limit=50").json()
        rejected = [r for r in audit if r["action"] == "policy_rejected"]
        # Shared test DB accumulates across tests; assert at least this rejection exists.
        assert len(rejected) >= 1
        row = rejected[0]
        assert row["actor"] == "policy"
        assert row["result"] == "failure"
        assert "max_per_transaction" in row["error_reason"]

    @patch("service.api.checkout.create_order")
    def test_within_policy_proceeds(self, mock_create_order, client):
        resp = _create(client, mock_create_order, items=WITHIN_POLICY)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready_for_payment"
        mock_create_order.assert_called_once()


class TestApprovalFlow:
    @patch("service.api.approval.capture_payment")
    @patch("service.api.approval.fetch_order")
    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_holds_then_approve_completes(
        self, mock_create, mock_co_fetch, mock_ap_fetch, mock_capture, client
    ):
        resp, token = _start_approval(client, mock_create, mock_co_fetch)
        assert resp.json()["status"] == "pending_approval"
        assert "approval_url" in resp.json()

        # Approval page renders the human gate.
        page = client.get(f"/api/approval/{token}")
        assert page.status_code == 200
        assert "Approve" in page.text and "Deny" in page.text

        mock_ap_fetch.return_value = {"status": "paid", "payments": ["pay_gate1"]}
        ok = client.post(f"/api/approval/{token}/approve")
        assert ok.status_code == 200
        assert ok.json()["status"] == "completed"
        mock_capture.assert_called_once_with(payment_id="pay_gate1", amount_paise=35000)

        # Audit: requested -> granted -> completed.
        audit = client.get("/api/audit?limit=50").json()
        actions = [r["action"] for r in audit]
        assert "approval_requested" in actions
        assert "approval_granted" in actions
        assert "checkout_completed" in actions

    @patch("service.api.approval.cancel_order")
    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_holds_then_deny_cancels(
        self, mock_create, mock_co_fetch, mock_cancel, client
    ):
        resp, token = _start_approval(client, mock_create, mock_co_fetch)
        assert resp.json()["status"] == "pending_approval"

        denied = client.post(f"/api/approval/{token}/deny")
        assert denied.status_code == 200
        assert denied.json()["status"] == "denied"
        mock_cancel.assert_called_once_with("order_gate1")

        audit = client.get("/api/audit?limit=50").json()
        assert any(r["action"] == "approval_denied" for r in audit)

    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_approve_second_time_is_rejected(self, mock_create, mock_co_fetch, client):
        _, token = _start_approval(client, mock_create, mock_co_fetch)
        # First deny consumes the token.
        with patch("service.api.approval.cancel_order"):
            client.post(f"/api/approval/{token}/deny")
        # Reusing the token must fail (single-use).
        again = client.post(f"/api/approval/{token}/approve")
        assert again.status_code == 409

    @patch("service.api.approval.capture_payment")
    @patch("service.api.approval.fetch_order")
    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_expired_approval_rejected(
        self, mock_create, mock_co_fetch, mock_ap_fetch, mock_capture, client, monkeypatch
    ):
        resp, token = _start_approval(client, mock_create, mock_co_fetch)
        assert resp.json()["status"] == "pending_approval"

        # Force the token to be expired by shrinking the TTL to a negative window.
        monkeypatch.setattr("service.settings.settings.approval_ttl_seconds", -1)
        expired = client.post(f"/api/approval/{token}/approve")
        assert expired.status_code == 410
        assert "expired" in expired.json()["detail"].lower()
        mock_capture.assert_not_called()

    def test_unknown_token_404(self, client):
        # The approval page (GET) renders a friendly HTML 200 for a human; only the
        # authorize actions (POST) reject an unknown token with 404.
        assert client.post("/api/approval/not_a_real_token/approve").status_code == 404
        assert client.post("/api/approval/not_a_real_token/deny").status_code == 404
