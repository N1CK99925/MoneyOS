"""Phase 4 — LLM-powered buyer agent with tool-calling."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import litellm

from service.settings import settings

from ..tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

# Suppress noisy litellm logs
logging.getLogger("litellm").setLevel(logging.WARNING)

# Set per-provider API keys for litellm — done centrally in service.settings,
# so every agent (core, stretch, CLI) gets distinct keys per provider.

# Global rate-limit cooldown: timestamp after which we can retry
_rate_limit_cooldown_until: float = 0.0
_RATE_LIMIT_BACKOFF = 30  # seconds to wait after hitting rate limit
_RETRY_DELAY = 3  # seconds between model retries

# Token-aware pacing: track tokens used in a rolling window to stay under the
# provider's per-minute budget instead of blowing through it and getting 429s.
# (Groq free tier is ~8000 TPM; keep well under it with headroom.)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_TOKEN_BUDGET = 7000  # tokens allowed per rolling window (headroom under 8000)
_token_history: list[tuple[float, int]] = []  # (timestamp, tokens_used)

_SYSTEM_PROMPT = """\
You are an autonomous buyer agent. Your job is to find and purchase a product \
from the merchant's catalog based on the user's goal.

How to work:
1. First, search the catalog to find relevant products.
2. Pick the best match based on the user's goal (price, name, description).
3. Create a checkout session with the selected item.
4. If the order is over the spend budget, it needs human approval first.
5. Once payable (awaiting_payment), get a payment link or test card so the user can pay.
6. After the user pays, complete the checkout to finalize the purchase.
7. Report what you bought and for how much.

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
- Only buy ONE item unless the user explicitly asks for multiple.
- If nothing matches, say so clearly — do not buy the wrong thing.
- If checkout fails, explain why and suggest next steps.
- Keep your final answer short and clear.
"""

# Type for the streaming callback: (event_type, data)
EventCallback = Callable[[str, dict[str, Any]], None]


def _pace_request(estimated_tokens: int, on_event: EventCallback | None) -> None:
    """Sleep as needed so rolling token usage stays under the per-minute budget.

    Called before each LLM request. Looks at tokens consumed in the last
    ``_RATE_LIMIT_WINDOW`` seconds and, if adding ``estimated_tokens`` would
    exceed ``_RATE_LIMIT_TOKEN_BUDGET``, waits until enough budget frees up.
    """
    now = time.time()

    # Drop entries older than the window
    while _token_history and _token_history[0][0] < now - _RATE_LIMIT_WINDOW:
        _token_history.pop(0)

    used = sum(t for _, t in _token_history)
    if used + estimated_tokens > _RATE_LIMIT_TOKEN_BUDGET:
        wait = _RATE_LIMIT_WINDOW - (now - _token_history[0][0]) if _token_history else 1.0
        wait = max(wait, 1.0)
        logger.info("Token budget hit (%d/%d) — pacing %.1fs", used, _RATE_LIMIT_TOKEN_BUDGET, wait)
        if on_event:
            on_event("rate_limit_wait", {"seconds": int(wait), "reason": "token_pacing"})
        time.sleep(wait)
        # Drop the now-expired window again so we don't double-count
        while _token_history and _token_history[0][0] < time.time() - _RATE_LIMIT_WINDOW:
            _token_history.pop(0)


def _record_tokens(usage) -> None:
    """Record tokens from a litellm response into the rolling window."""
    if usage is None:
        return
    # Count input + output + cache tokens; fall back to total_tokens if present.
    total = getattr(usage, "total_tokens", 0) or 0
    if total == 0:
        total = (getattr(usage, "prompt_tokens", 0) or 0) + (getattr(usage, "completion_tokens", 0) or 0)
    if total > 0:
        _token_history.append((time.time(), total))


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
            _pace_request(estimated_tokens=2000, on_event=on_event)
            # No explicit api_key here: litellm resolves the key per provider
            # from the env vars set above, so each fallback uses its own key.
            response = litellm.completion(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        except Exception as e:
            error_msg = f"LLM call failed on {model}: {e}"
            logger.warning(error_msg)
            raise RuntimeError(error_msg) from e

        _record_tokens(response.usage)

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
