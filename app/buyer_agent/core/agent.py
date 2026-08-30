"""Phase 4 — LLM-powered buyer agent with tool-calling."""

from __future__ import annotations

import json
import logging
import os
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

_SYSTEM_PROMPT = """\
You are an autonomous buyer agent. Your job is to find and purchase a product \
from the merchant's catalog based on the user's goal.

How to work:
1. First, search the catalog to find relevant products.
2. Pick the best match based on the user's goal (price, name, description).
3. Create a checkout session with the selected item.
4. Complete the checkout to finalize the purchase.
5. Report what you bought and for how much.

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
        if tool_name == "create_checkout_session" and "items" in tool_args:
            items = tool_args["items"]
            buyer_id = tool_args.get("buyer_agent_id", "llm-agent")
            return fn(items=items, buyer_agent_id=buyer_id)
        if tool_name == "search_catalog":
            return fn(query=tool_args["query"])
        if tool_name in ("complete_checkout", "cancel_checkout", "get_checkout_session"):
            return fn(session_id=tool_args["session_id"])
        return fn(**tool_args)
    except Exception as e:
        logger.exception("Tool %s failed", tool_name)
        return json.dumps({"error": str(e)})


def run_buyer_agent(
    goal: str,
    *,
    verbose: bool = False,
    on_event: EventCallback | None = None,
) -> str:
    """Run the buyer agent loop and return a final summary.

    Parameters
    ----------
    goal : str
        The purchase goal, e.g. "buy chicken biriyani under ₹500".
    verbose : bool
        If True, print each tool call and result.
    on_event : callback(event_type, data) or None
        Called for each agent event (tool_call, tool_result, model_switch, summary).

    Returns
    -------
    str
        The agent's final summary of what it did.
    """
    models = _build_models()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    last_error: str | None = None

    for model in models:
        logger.info("Trying model: %s", model)
        if on_event:
            on_event("model_switch", {"model": model})
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

        response = litellm.completion(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            api_key=settings.llm_api_key or None,
        )

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
