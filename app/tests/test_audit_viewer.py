"""Tests for the audit viewer endpoint."""


class TestAuditViewer:
    """GET /api/audit — show recent audit log rows."""

    def test_audit_returns_200(self, client):
        resp = client.get("/api/audit")
        assert resp.status_code == 200

    def test_audit_returns_list(self, client):
        resp = client.get("/api/audit")
        assert isinstance(resp.json(), list)

    def test_audit_limit_works(self, client):
        resp = client.get("/api/audit?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1
