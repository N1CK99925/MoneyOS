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


_CATEGORY_ORDER = ["Food", "Electronics", "Groceries", "Stationery"]


def _categories(products: list[dict]) -> list[dict]:
    """Group products into themed zones (categories), preserving display order.

    Products without a category fall back to "Other".
    """
    by_cat: dict[str, list[dict]] = {}
    for p in products:
        by_cat.setdefault(p.get("category") or "Other", []).append(p)

    known = [c for c in _CATEGORY_ORDER if c in by_cat]
    rest = [c for c in by_cat if c not in _CATEGORY_ORDER]
    return [
        {"name": cat, "products": by_cat[cat]}
        for cat in list(known) + list(rest)
    ]


@router.get("/catalog")
def get_catalog():
    """Return the full merchant catalog for agent consumption."""
    products = _load_catalog()
    return {
        "merchant": "nick-store",
        "currency": "INR",
        "products": products,
        "categories": _categories(products),
    }
