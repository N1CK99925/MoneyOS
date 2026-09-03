"""Phase 4B — review-scoring metric, defined explicitly.

Scoring Rule (documented intent):
    Pick the item with the highest average rating, provided it has
    ≥ 20 reviews. If no item meets the review threshold, fall back
    to the item with the most reviews. If no review data exists at
    all, return None (caller should use catalog-only fallback).

Honesty note: the live web-search source (Tavily) does not return
structured consumer-review data (rating / review count). Its ``score``
is a relevance score, not a rating, so we deliberately do not pass it
off as one. Because of that, `score_items` will typically return None
and the caller falls back to the cheapest match — which is the honest,
explainable behavior for this fixture catalog. If a review-capable
source is wired up later, it must populate real `rating`/`review_count`.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MIN_REVIEWS = 20


def score_items(
    catalog_items: list[dict[str, Any]],
    search_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Score catalog items based on web search review data.

    Parameters
    ----------
    catalog_items : list[dict]
        Items from the catalog (must have 'id', 'name', 'price_paise').
    search_results : list[dict]
        Brave Search results with optional 'rating' and 'review_count' fields.

    Returns
    -------
    dict or None
        The best-scoring item with added 'rating' and 'review_count' fields,
        or None if no review data is available.
    """
    if not search_results:
        logger.info("No search results — cannot score")
        return None

    # Build a score map from search results
    # Match search results to catalog items by name similarity
    scored: dict[str, dict[str, Any]] = {}

    for item in catalog_items:
        item_name_lower = item["name"].lower()
        best_rating = None
        best_review_count = None

        for result in search_results:
            title_lower = result.get("title", "").lower()
            snippet_lower = result.get("snippet", "").lower()

            # Check if this result is relevant to the item
            if any(
                word in title_lower or word in snippet_lower
                for word in item_name_lower.split()
                if len(word) > 2
            ):
                rating = result.get("rating")
                review_count = result.get("review_count")

                if rating is not None and review_count is not None:
                    if best_rating is None or review_count > (best_review_count or 0):
                        best_rating = rating
                        best_review_count = review_count

        if best_rating is not None:
            scored[item["id"]] = {
                **item,
                "rating": best_rating,
                "review_count": best_review_count,
            }

    if not scored:
        logger.info("No scored items — no review data matched catalog")
        return None

    # Apply scoring rule: highest rating with ≥ MIN_REVIEWS
    qualified = [
        item for item in scored.values()
        if (item.get("review_count") or 0) >= MIN_REVIEWS
    ]

    if qualified:
        # Best among qualified: highest rating, break ties by review count
        best = max(qualified, key=lambda x: (x["rating"], x["review_count"] or 0))
        logger.info(
            "Scored (qualified): %s — rating=%s, reviews=%s",
            best["name"],
            best["rating"],
            best["review_count"],
        )
        return best

    # Fallback: most reviews (even if below threshold)
    fallback = max(scored.values(), key=lambda x: x.get("review_count") or 0)
    logger.info(
        "Scored (fallback, below %d reviews): %s — rating=%s, reviews=%s",
        MIN_REVIEWS,
        fallback["name"],
        fallback.get("rating"),
        fallback.get("review_count"),
    )
    return fallback
