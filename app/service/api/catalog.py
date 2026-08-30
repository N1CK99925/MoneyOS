"""GET /api/catalog — returns the merchant's product list."""

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["catalog"])

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "catalog.json"


def _load_catalog() -> list[dict]:
    """Load catalog from fixture JSON file."""
    with open(_CATALOG_PATH) as f:
        return json.load(f)


@router.get("/catalog")
def get_catalog():
    """Return the full merchant catalog for agent consumption."""
    return {
        "merchant": "nick-store",
        "currency": "INR",
        "products": _load_catalog(),
    }
