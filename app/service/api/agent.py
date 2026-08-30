"""POST /api/agent/run — SSE endpoint for the buyer agent."""

from __future__ import annotations

import json
import queue
import threading
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from buyer_agent.core.agent import run_buyer_agent

router = APIRouter(prefix="/api", tags=["agent"])


class AgentRunRequest(BaseModel):
    goal: str = Field(..., description="Purchase goal, e.g. 'buy chicken biriyani under ₹500'")


def _sse_stream(goal: str) -> Any:
    """Generator that yields SSE events from the buyer agent."""
    q: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue()

    def on_event(event_type: str, data: dict[str, Any]) -> None:
        q.put((event_type, data))

    def run() -> None:
        try:
            result = run_buyer_agent(goal, on_event=on_event)
            q.put(("done", {"result": result}))
        except Exception as e:
            q.put(("error", {"message": str(e)}))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    while True:
        try:
            event_type, data = q.get(timeout=300)
        except queue.Empty:
            yield {"event": "error", "data": json.dumps({"message": "Timeout"})}
            break

        yield {"event": event_type, "data": json.dumps(data)}

        if event_type in ("done", "error"):
            break


@router.post("/agent/run")
async def run_agent(body: AgentRunRequest):
    """Stream buyer agent progress via Server-Sent Events."""
    if not body.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    return EventSourceResponse(_sse_stream(body.goal))
