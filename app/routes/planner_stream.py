"""Server-sent progress stream for long-running planner actions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import Settings
from app.models.user import User

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

_LOGGER = logging.getLogger(__name__)


def stream_planner_action(
    request: Request,
    user: User,
    settings: Settings,
    action: Callable[[Request, User, Settings], Awaitable[HTMLResponse]],
) -> StreamingResponse:
    """Stream real backend milestones and return rendered planner HTML when complete.

    Returns:
        A newline-delimited event stream consumed by the in-place Planner UI.
    """
    queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()

    def progress(message: str) -> None:
        queue.put_nowait({"kind": "stage", "message": message})

    async def execute() -> None:
        request.state.planner_progress = progress
        try:
            result = await action(request, user, settings)
            queue.put_nowait({"kind": "complete", "html": bytes(result.body).decode("utf-8")})
        except Exception:
            _LOGGER.exception("Planner generation stream failed")
            queue.put_nowait({
                "kind": "error",
                "message": "Plan generation failed. Your existing plan is still available; please try again.",
            })
        finally:
            queue.put_nowait(None)

    async def events() -> AsyncIterator[str]:
        # Work continues to save or stage the plan even if a browser tab disconnects.
        task = asyncio.create_task(execute())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield "data: " + json.dumps(item, ensure_ascii=False) + chr(10) * 2
        finally:
            if task.done():
                await task

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
