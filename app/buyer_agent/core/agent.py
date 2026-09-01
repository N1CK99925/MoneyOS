"""Phase 4 — LLM-powered buyer agent with tool-calling."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import Any

import litellm

from service.settings import settings

from ..tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

# Suppress noisy litellm logs
logging.getLogger("litellm").setLevel(logging.WARNING)

# Set API key for litellm (reads from env var, litellm uses provider-specific env vars)
if settings.llm_api_key:
    # Set the key for all common providers so fallbacks work
    os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
    os.environ.setdefault("OPENROUTER_API_KEY", settings.llm_api_key)
    os.environ.setdefault("GROQ_API_KEY", settings.llm_api_key)
    os.environ.setdefault("GEMINI_API_KEY", settings.llm_api_key)

# Global rate-limit cooldown: timestamp after which we can retry
_rate_limit_cooldown_until: float = 0.0
_RATE_LIMIT_BACKOFF = 30  # seconds to wait after hitting rate limit
_RETRY_DELAY = 3  # seconds between model retries

_SYSTEM_PROMPT = """\
You are an autonomous buyer agent. Your job is to find and purchase a product \
from the merchant's catalog based on the user's goal.

How to work:
1. First, search the catalog to find relevant products.
2. Pick the best match based on the user's goal (price, name, description).
3. Create a checkout session with the selected item.
4. Get a payment link OR test card details so the user can pay.
5. After the user pays, complete the checkout to finalize the purchase.
6. Report what you bought and for how much.

Payment flow (IMPORTANT):
- After creating a checkout session, you MUST get a payment method:
  - Use `get_payment_link` to generate a hosted checkout URL, OR
  - Use `pay_with_test_card` to get test card details for manual entry
- Share the payment link or test card details with the user.
- Only call `complete_checkout` AFTER the user has paid (payment is confirmed).
- If you call `complete_checkout` before payment, it will return a 400 error.

Rules:
- Always search the catalog first — never guess product IDs.
- Only buy ONE item unless the user explicitly asks for multiple.
- If nothing matches, say so clearly — do not buy the wrong thing.
- If checkout fails, explain why and suggest next steps.
- Keep your final answer short and clear.
"""

# Type for the streaming callback: (event_type, data)
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


def _execute_tool(tool_name: str, tool_args: dict[str, Any]) -> str:
    """Execute a tool and return its result as a string."""
    fn = TOOL_FUNCTIONS.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        # Catalog + checkout tools (HTTP-based)
        if tool_name == "search_catalog":
            return fn(query=tool_args["query"])
        if tool_name == "create_checkout_session" and "items" in tool_args:
            items = tool_args["items"]
            buyer_id = tool_args.get("buyer_agent_id", "llm-agent")
            return fn(items=items, buyer_agent_id=buyer_id)
        if tool_name in ("complete_checkout", "cancel_checkout", "get_checkout_session"):
            return fn(session_id=tool_args["session_id"])

        # Payment tools (Razorpay API)
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

        # Generic fallback
        return fn(**tool_args)
    except Exception as e:
        logger.exception("Tool %s failed", tool_name)
        return json.dumps({"error": str(e)})


def run_buyer_agent(
    goal: str,
    *,
    history: list[dict[str, Any]] | None = None,
    verbose: bool = False,
    on_event: EventCallback | None = None,
) -> str:
    """Run the buyer agent loop and return a final summary.

    Parameters
    ----------
    goal : str
        The purchase goal, e.g. "buy chicken biriyani under ₹500".
    history : list of dicts, optional
        Prior conversation turns (role/content pairs) for multi-turn context.
        Injected between the system prompt and the current user message.
    verbose : bool
        If True, print each tool call and result.
    on_event : callback(event_type, data) or None
        Called for each agent event (tool_call, tool_result, model_switch, summary).

    Returns
    -------
    str
        The agent's final summary of what it did.
    """
    global _rate_limit_cooldown_until

    models = _build_models()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": goal})

    last_error: str | None = None

    for i, model in enumerate(models):
        # Respect rate-limit cooldown
        now = time.time()
        if now < _rate_limit_cooldown_until:
            wait = _rate_limit_cooldown_until - now
            logger.info("Rate-limit cooldown: waiting %.0fs", wait)
            if on_event:
                on_event("rate_limit_wait", {"seconds": int(wait)})
            time.sleep(wait)

        # Delay between model retries
        if i > 0:
            time.sleep(_RETRY_DELAY)

        logger.info("Trying model: %s", model)
        if on_event:
            on_event("model_switch", {"model": model})
        try:
            return _run_loop(model, messages, verbose, on_event)
        except Exception as e:
            last_error = str(e)
            logger.warning("Model %s failed: %s", model, last_error)

            # Detect rate limit errors — set cooldown
            err_str = str(e).lower()
            if "rate" in err_str and "limit" in err_str:
                _rate_limit_cooldown_until = time.time() + _RATE_LIMIT_BACKOFF
                logger.warning("Rate limited — cooling down for %ds", _RATE_LIMIT_BACKOFF)
                if on_event:
                    on_event("rate_limit_wait", {"seconds": _RATE_LIMIT_BACKOFF, "model": model})
                continue

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
            response = litellm.completion(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                api_key=settings.llm_api_key or None,
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
