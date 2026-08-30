"""Phase 4B — Brave Search API integration for web search."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from service.settings import settings

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def brave_search(query: str, *, count: int = 5) -> list[dict[str, Any]]:
    """Search the web using Brave Search API.

    Returns a list of result dicts with keys: title, url, snippet, rating, review_count.
    Only web results are returned (no news, images, etc.).
    """
    api_key = settings.brave_api_key
    if not api_key:
        logger.warning("BRAVE_API_KEY not set — returning empty results")
        return []

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    try:
        resp = httpx.get(
            BRAVE_SEARCH_URL,
            headers=headers,
            params={"q": query, "count": count},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Brave Search returned %d: %s", e.response.status_code, e.response.text[:200])
        return []
    except httpx.RequestError as e:
        logger.error("Brave Search request failed: %s", e)
        return []

    web_results = data.get("web", {}).get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
            "rating": r.get("rating"),
            "review_count": r.get("review_count"),
        }
        for r in web_results
    ]


def search_food_reviews(item_name: str) -> list[dict[str, Any]]:
    """Search for reviews of a specific food item.

    Constructs a query like "Chicken Biriyani reviews rating" to find
    review data from food delivery sites, blogs, and review aggregators.
    """
    query = f"{item_name} reviews rating"
    return brave_search(query, count=8)
