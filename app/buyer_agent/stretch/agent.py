"""Phase 4B — search-and-score buyer agent.

Reuses core checkout tools from the core agent. Adds web search + scoring
to pick the best item based on real reviews, not just catalog data.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import litellm

from service.settings import settings

from ..tools import (
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
    search_catalog,
)
from .scoring import score_items
from .search import search_food_reviews

logger = logging.getLogger(__name__)

# Suppress noisy litellm logs
logging.getLogger("litellm").setLevel(logging.WARNING)

_SYSTEM_PROMPT = """\
You are a research-driven buyer agent. Your job is to find the BEST product \
based on real web reviews, then purchase it.

How to work:
1. First, search the catalog to see what's available.
2. Search the web for reviews. NOTE: the current search source (Tavily) does not \
return structured consumer ratings or review counts. When no review data is \
available, score_items returns no winner and you fall back to the cheapest match.
3. Create a checkout session with the best item.
4. If the order is over the spend budget, it needs human approval first.
5. Once payable (awaiting_payment), get a payment link or test card so the user can pay.
6. After the user pays, complete the checkout to finalize the purchase.
7. Report what you bought, why you picked it, and the price.

Payment flow (IMPORTANT):
- When you create a checkout session, the response status tells you what's next:
  - 'awaiting_payment' — within budget, ready for payment. Generate a payment
    page with `get_payment_link` (or `pay_with_test_card`) and share it with the user.
  - 'pending_approval' — over budget, held for human approval. STOP and report
    the approval_url; the buyer cannot pay until a human approves the exception.
- Only call `complete_checkout` AFTER the user has paid (payment is confirmed).
- If you call `complete_checkout` before payment, it will return a 400 error.

Rules:
- ONLY handle product research and purchasing. If the user asks something unrelated (e.g. coding, math, general knowledge), politely refuse and redirect them to the task at hand.
- Always search the catalog first — never guess product IDs.
- Use web search to find real reviews and ratings for items.
- Only buy ONE item unless the user explicitly asks for multiple.
- If no review data is available, fall back to the cheapest option.
- If nothing matches, say so clearly — do not buy the wrong thing.
- Keep your final answer short and clear.
"""

EventCallback = Callable[[str, dict[str, Any]], None]


def _build_models() -> list[str]:
    """Build ordered list of models with fallbacks."""
    models = [settings.llm_model]
    if settings.llm_fallback_models:
        for m in settings.llm_fallback_models.split(","):
            m = m.strip()
            if m and m not in models:
                models.append(m)
    return models


def _search_and_score(tool_args: dict[str, Any]) -> str:
    """Search catalog + web, then score and return the best item."""
    query = tool_args.get("query", "")

    # Step 1: Get catalog matches
    catalog_result = json.loads(search_catalog(query))
    catalog_items = catalog_result.get("matches", [])

    if not catalog_items:
        return json.dumps({"error": "No catalog items found", "matches": []})

    # Step 2: Search web for reviews of top candidates
    all_search_results = []
    for item in catalog_items[:3]:  # search top 3 to stay within API limits
        results = search_food_reviews(item["name"])
        all_search_results.extend(results)

    # Step 3: Score and pick the best
    best = score_items(catalog_items, all_search_results)

    if best is None:
        # No review data — fall back to cheapest
        cheapest = min(catalog_items, key=lambda x: x["price_paise"])
        cheapest["scoring_note"] = "No review data available — fell back to cheapest"
        return json.dumps({"best_match": cheapest, "scoring_method": "fallback_cheapest"})

    return json.dumps({
        "best_match": best,
        "scoring_method": "highest_rated_with_min_reviews",
        "min_reviews_threshold": 20,
    })


def _execute_tool(tool_name: str, tool_args: dict[str, Any]) -> str:
    """Execute a tool and return its result as a string."""
    if tool_name == "search_and_score":
        return _search_and_score(tool_args)

    fn = TOOL_FUNCTIONS.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        # Catalog + checkout tools
        if tool_name == "create_checkout_session" and "items" in tool_args:
            items = tool_args["items"]
            buyer_id = tool_args.get("buyer_agent_id", "stretch-agent")
            return fn(items=items, buyer_agent_id=buyer_id)
        if tool_name == "search_catalog":
            return fn(query=tool_args["query"])
        if tool_name in ("complete_checkout", "cancel_checkout", "get_checkout_session"):
            return fn(session_id=tool_args["session_id"])

        # Payment tools
        if tool_name == "get_payment_link":
            return fn(
                session_id=tool_args["session_id"],
                amount_paise=tool_args["amount_paise"],
                item_name=tool_args.get("item_name", "Item"),
            )
        if tool_name == "pay_with_test_card":
            return fn(
                session_id=tool_args["session_id"],
                amount_paise=tool_args["amount_paise"],
                card=tool_args.get("card", "visa"),
            )

        return fn(**tool_args)
    except Exception as e:
        logger.exception("Tool %s failed", tool_name)
        return json.dumps({"error": str(e)})


# Extended tool definitions — adds search_and_score on top of all base tools
STRETCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    *TOOL_DEFINITIONS,
    {
        "type": "function",
        "function": {
            "name": "search_and_score",
            "description": (
                "Search the catalog AND the web for reviews. Scores items by "
                "highest rating with ≥20 reviews. Returns the best match with "
                "its rating, review count, and price."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term, e.g. 'biriyani', 'butter chicken'",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def run_stretch_agent(
    goal: str,
    *,
    history: list[dict[str, Any]] | None = None,
    verbose: bool = False,
    on_event: EventCallback | None = None,
) -> str:
    """Run the stretch buyer agent with web search + scoring.

    Parameters
    ----------
    goal : str
        The purchase goal, e.g. "buy the best biriyani under ₹500".
    history : list of dicts, optional
        Prior conversation turns (role/content pairs) for multi-turn context.
    verbose : bool
        If True, print each tool call and result.
    on_event : callback(event_type, data) or None
        Called for each agent event.

    Returns
    -------
    str
        The agent's final summary of what it did.
    """
    models = _build_models()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": goal})

    last_error: str | None = None

    for model in models:
        logger.info("Trying model: %s", model)
        if on_event:
            on_event("model_switch", {"model": model, "agent": "stretch"})
        try:
            return _run_loop(model, messages, verbose, on_event)
        except Exception as e:
            last_error = str(e)
            logger.warning("Model %s failed: %s", model, last_error)
            if on_event:
                on_event("model_error", {"model": model, "error": last_error})
            continue

    error_msg = f"All models failed. Last error: {last_error}"
    if on_event:
        on_event("error", {"message": error_msg})
    return error_msg


def _run_loop(
    model: str,
    messages: list[dict[str, Any]],
    verbose: bool,
    on_event: EventCallback | None,
) -> str:
    """Run the tool-calling loop on a single model."""
    max_iter = settings.llm_max_iterations

    for iteration in range(1, max_iter + 1):
        logger.info("Iteration %d/%d", iteration, max_iter)

        try:
            # No explicit api_key: litellm resolves the key per provider from
            # the env vars set in service.settings, so each fallback uses its own key.
            response = litellm.completion(
                model=model,
                messages=messages,
                tools=STRETCH_TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        except Exception as e:
            error_msg = f"LLM call failed on {model}: {e}"
            logger.warning(error_msg)
            raise RuntimeError(error_msg) from e

        message = response.choices[0].message

        # No tool calls — agent is done
        if not message.tool_calls:
            summary = message.content or "Done (no summary provided)."
            if on_event:
                on_event("summary", {"message": summary})
            return summary

        # Execute each tool call
        messages.append(message)

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            if verbose:
                print(f"  [tool] {fn_name}({fn_args})")

            if on_event:
                on_event("tool_call", {"name": fn_name, "args": fn_args})

            result = _execute_tool(fn_name, fn_args)

            if verbose:
                print(f"  [result] {result[:200]}")

            if on_event:
                on_event("tool_result", {"name": fn_name, "result": result})

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": fn_name,
                "content": result,
            })

    error_msg = f"Reached max iterations ({max_iter}) without completing the goal."
    if on_event:
        on_event("error", {"message": error_msg})
    return error_msg
