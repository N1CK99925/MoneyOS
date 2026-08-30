"""Tests for Phase 1 — catalog, audit writer, and DB schema."""

import json
import os

from service.db.audit_writer import write_audit_row


class TestCatalog:
    """Issue #2 — GET /api/catalog serves fixture data."""

    def test_catalog_loads_json(self):
        """catalog.json is valid JSON with at least 5 items."""
        catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "catalog.json",
        )
        with open(catalog_path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_catalog_items_have_required_fields(self):
        """Every item has id, name, price_paise, currency, description."""
        catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "catalog.json",
        )
        with open(catalog_path) as f:
            data = json.load(f)
        required = {"id", "name", "price_paise", "currency", "description"}
        for item in data:
            assert required.issubset(
                item.keys()
            ), f"Missing fields in {item.get('id')}: {required - item.keys()}"


class TestAuditWriter:
    """Issue #3 — audit log schema + write helper."""

    def test_write_row_creates_entry(self, db_session):
        """Calling write_audit_row inserts a row with all fields."""
        row = write_audit_row(
            db_session,
            actor="test_actor",
            action="test_action",
            entity_type="test_entity",
            entity_id="ent_123",
            payload={"key": "value"},
            result="success",
        )
        assert row.id is not None
        assert row.actor == "test_actor"
        assert row.action == "test_action"
        assert row.entity_type == "test_entity"
        assert row.entity_id == "ent_123"
        assert row.result == "success"
        assert row.signed_hash is not None
        assert len(row.signed_hash) == 64  # SHA256 hex digest

    def test_signed_hash_is_valid_hex(self, db_session):
        """Signed hash is a valid hex string."""
        row = write_audit_row(
            db_session,
            actor="a",
            action="b",
            payload={"x": 1},
            result="success",
        )
        assert row.signed_hash is not None
        int(row.signed_hash, 16)

    def test_audit_log_schema_matches_prd(self, db_session):
        """Schema has all columns from PRD §6."""
        from sqlalchemy import text

        result = db_session.execute(text("PRAGMA table_info(audit_log)"))
        columns = {row[1] for row in result}
        expected = {
            "id",
            "timestamp",
            "actor",
            "action",
            "entity_type",
            "entity_id",
            "payload",
            "result",
            "error_reason",
            "signed_hash",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_multiple_rows_independent(self, db_session):
        """Multiple audit rows can coexist."""
        r1 = write_audit_row(db_session, actor="a", action="b", result="success")
        r2 = write_audit_row(db_session, actor="c", action="d", result="failure")
        assert r1.id != r2.id
        assert r1.signed_hash != r2.signed_hash
