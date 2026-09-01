"""Tests for the checkout flow — Phase 1 gate requires this works."""

from unittest.mock import patch


class TestCatalogEndpoint:
    """GET /api/catalog — the first thing you curl in the demo."""

    def test_catalog_returns_200(self, client):
        resp = client.get("/api/catalog")
        assert resp.status_code == 200

    def test_catalog_has_merchant_and_products(self, client):
        resp = client.get("/api/catalog")
        data = resp.json()
        assert data["merchant"] == "nick-store"
        assert data["currency"] == "INR"
        assert isinstance(data["products"], list)
        assert len(data["products"]) >= 5

    def test_catalog_product_schema(self, client):
        resp = client.get("/api/catalog")
        products = resp.json()["products"]
        for p in products:
            assert "id" in p
            assert "name" in p
            assert "price_paise" in p
            assert p["price_paise"] > 0


def _create_session(client, mock_create_order, order_id="order_test123", amount=35000):
    """Helper to create a checkout session."""
    mock_create_order.return_value = {
        "id": order_id,
        "amount": amount,
        "currency": "INR",
        "status": "created",
    }
    return client.post(
        "/api/checkout_sessions",
        json={"items": [{"item_id": "item_001", "quantity": 1}]},
    )


class TestCheckoutSession:
    """POST /api/checkout_sessions — create a session backed by Razorpay order."""

    @patch("service.api.checkout.create_order")
    def test_create_session_returns_200(self, mock_create_order, client):
        resp = _create_session(client, mock_create_order)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "order_test123"
        assert data["total_paise"] == 35000
        assert data["status"] == "ready_for_payment"

    def test_create_session_validates_items(self, client):
        resp = client.post(
            "/api/checkout_sessions",
            json={"items": [{"item_id": "nonexistent_item", "quantity": 1}]},
        )
        assert resp.status_code == 400

    @patch("service.api.checkout.create_order")
    def test_create_session_calculates_total(self, mock_create_order, client):
        mock_create_order.return_value = {
            "id": "order_test456",
            "amount": 53000,
            "currency": "INR",
            "status": "created",
        }
        resp = client.post(
            "/api/checkout_sessions",
            json={
                "items": [
                    {"item_id": "item_001", "quantity": 1},
                    {"item_id": "item_002", "quantity": 1},
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total_paise"] == 60000

    def test_get_session_not_found(self, client):
        resp = client.get("/api/checkout_sessions/nonexistent")
        assert resp.status_code == 404


class TestCompleteCheckout:
    """POST /api/checkout_sessions/{id}/complete — verify payment."""

    @patch("service.api.checkout.fetch_payment")
    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_success(self, mock_create, mock_fetch_order, mock_fetch_payment, client):
        _create_session(client, mock_create)
        mock_fetch_order.return_value = {"status": "paid", "payments": ["pay_abc"]}
        mock_fetch_payment.return_value = {"id": "pay_abc", "status": "captured"}

        resp = client.post("/api/checkout_sessions/order_test123/complete")
        assert resp.status_code == 200
        data = resp.json()
        # Gated payments: complete now enters a human approval hold, not immediate completion.
        assert data["status"] == "pending_approval"
        assert "/api/approval/" in data["approval_url"]

    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_not_yet_paid(self, mock_create, mock_fetch_order, client):
        _create_session(client, mock_create)
        mock_fetch_order.return_value = {"status": "created"}

        resp = client.post("/api/checkout_sessions/order_test123/complete")
        assert resp.status_code == 400
        assert "not yet paid" in resp.json()["detail"]["message"].lower()

    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_payment_failed(self, mock_create, mock_fetch_order, client):
        _create_session(client, mock_create, order_id="order_fail1")
        mock_fetch_order.return_value = {"status": "failed"}

        resp = client.post("/api/checkout_sessions/order_fail1/complete")
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["status"] == "failed"
        assert "failed" in detail["message"].lower()

    @patch("service.api.checkout.fetch_order")
    @patch("service.api.checkout.create_order")
    def test_complete_payment_cancelled(self, mock_create, mock_fetch_order, client):
        _create_session(client, mock_create, order_id="order_cancel1")
        mock_fetch_order.return_value = {"status": "cancelled"}

        resp = client.post("/api/checkout_sessions/order_cancel1/complete")
        assert resp.status_code == 402
        assert resp.json()["detail"]["status"] == "failed"

    def test_complete_session_not_found(self, client):
        resp = client.post("/api/checkout_sessions/nonexistent/complete")
        assert resp.status_code == 404


class TestCancelCheckout:
    """POST /api/checkout_sessions/{id}/cancel — cancel a session."""

    @patch("service.api.checkout.create_order")
    def test_cancel_success(self, mock_create_order, client):
        _create_session(client, mock_create_order, order_id="order_cancel_me")

        resp = client.post("/api/checkout_sessions/order_cancel_me/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "canceled"
        assert "canceled" in data["message"].lower()

    def test_cancel_session_not_found(self, client):
        resp = client.post("/api/checkout_sessions/nonexistent/cancel")
        assert resp.status_code == 404
