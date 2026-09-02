"""Runtime settings — read/write from DB with in-memory cache.

 Falls back to the static Settings defaults when the DB has no value.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .db import SessionLocal, SystemSetting
from .settings import settings as _static_settings

logger = logging.getLogger(__name__)

# In-memory cache: key -> value (str).  Populated on first read.
_cache: dict[str, str] = {}
_cache_loaded = False


def _load_all_from_db() -> None:
    """Bulk-load every setting into the cache."""
    global _cache_loaded
    try:
        db = SessionLocal()
        try:
            rows = db.query(SystemSetting).all()
            for row in rows:
                _cache[row.key] = row.value
        finally:
            db.close()
    except Exception:
        logger.warning("Could not load system_settings from DB — using static defaults")
    _cache_loaded = True


def _ensure_loaded() -> None:
    if not _cache_loaded:
        _load_all_from_db()


def get_setting(key: str) -> str:
    """Return the current value for *key* (DB > cache > static default)."""
    _ensure_loaded()
    if key in _cache:
        return _cache[key]
    # Fall back to the static pydantic-settings default
    default = getattr(_static_settings, key, None)
    return str(default) if default is not None else ""


def get_setting_int(key: str) -> int:
    """Convenience: return *key* as an int."""
    return int(get_setting(key))


def set_setting(db: Session, key: str, value: str, description: str | None = None) -> None:
    """Upsert a setting into the DB and refresh the cache."""
    now = datetime.now(UTC).isoformat()
    row = db.query(SystemSetting).filter_by(key=key).first()
    if row:
        row.value = value
        row.updated_at = now
        if description is not None:
            row.description = description
    else:
        row = SystemSetting(
            key=key,
            value=value,
            description=description or "",
            updated_at=now,
        )
        db.add(row)
    db.commit()
    _cache[key] = value


def get_all_settings(db: Session) -> list[dict]:
    """Return every setting as a list of dicts (for the API response)."""
    _ensure_loaded()
    rows = db.query(SystemSetting).all()
    result = []
    for row in rows:
        default = getattr(_static_settings, row.key, None)
        result.append({
            "key": row.key,
            "value": row.value,
            "default": str(default) if default is not None else "",
            "description": row.description or "",
            "updated_at": row.updated_at,
        })
    return result


def get_spend_policy_max() -> int:
    """Return the current spend policy max in paise."""
    return get_setting_int("spend_policy_max_per_transaction_paise")
