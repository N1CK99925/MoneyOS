"""Phase 4B — Tavily Search API integration for web search."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from service.settings import settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def tavily_search(query: str, *, count: int = 5) -> list[dict[str, Any]]:
    """Search the web using Tavily Search API.

    Returns a list of result dicts with keys: title, url, snippet, rating, review_count.
    Only web results are returned (no news, images, etc.).
    """
    api_key = settings.tavily_api_key
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — returning empty results")
        return []

    payload = {
        "query": query,
        "max_results": count,
        "api_key": api_key,
    }

    try:
        resp = httpx.post(
            TAVILY_SEARCH_URL,
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Tavily Search returned %d: %s", e.response.status_code, e.response.text[:200])
        return []
    except httpx.RequestError as e:
        logger.error("Tavily Search request failed: %s", e)
        return []

    web_results = data.get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            "rating": r.get("score"),
            "review_count": None,
        }
        for r in web_results
    ]


def search_food_reviews(item_name: str) -> list[dict[str, Any]]:
    """Search for reviews of a specific food item.

    Constructs a query like "Chicken Biriyani reviews rating" to find
    review data from food delivery sites, blogs, and review aggregators.
    """
    query = f"{item_name} reviews rating"
    return tavily_search(query, count=8)
