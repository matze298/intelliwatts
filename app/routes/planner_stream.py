"""Server-sent progress stream for long-running planner actions."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import traceback
from urllib.parse import quote
from typing import TYPE_CHECKING

from fastapi.responses import HTMLResponse, StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from fastapi import Request

    from app.config import Settings
    from app.models.user import User

_LOGGER = logging.getLogger(__name__)


_SECRET_SETTINGS = (
    "APP_PASSWORD",
    "SESSION_SECRET",
    "DATABASE_URL",
    "INTERVALS_API_KEY",
    "INTERVALS_ATHLETE_ID",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
)
_MAX_TRACEBACK_LENGTH = 16000
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|session[_-]?secret|"
    r"authorization)\s*[:=]\s*['\"]?)[^'\"\s,;&]+"
)
_BEARER_TOKEN = re.compile(r"(?i)(Bearer\s+)\S+")


def safe_planner_traceback(error: Exception, settings: Settings) -> str:
    """Prepare a useful traceback for the authenticated UI without exposing known credentials.

    Returns:
        A size-bounded traceback with configured secrets and credential fields redacted.
    """
    details = "".join(traceback.format_exception(error))
    secrets = {
        value
        for field in _SECRET_SETTINGS
        if isinstance((value := getattr(settings, field, None)), str) and len(value) >= 4
    }
    for secret in sorted(secrets, key=len, reverse=True):
        details = details.replace(secret, "[REDACTED]")
        encoded = quote(secret, safe="")
        if encoded != secret:
            details = details.replace(encoded, "[REDACTED]")
    details = _SENSITIVE_ASSIGNMENT.sub(r"\1[REDACTED]", details)
    details = _BEARER_TOKEN.sub(r"\1[REDACTED]", details)
    if len(details) > _MAX_TRACEBACK_LENGTH:
        details = "[Earlier traceback frames omitted]\n" + details[-_MAX_TRACEBACK_LENGTH:]
    return details


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
        except Exception as exc:
            _LOGGER.exception("Planner generation stream failed")
            queue.put_nowait({
                "kind": "error",
                "message": "Plan generation failed. Your existing plan is still available; please try again.",
                "traceback": safe_planner_traceback(exc, settings),
            })
        finally:
            queue.put_nowait(None)

    async def events() -> AsyncIterator[str]:
        # Work continues to save or stage the plan even if a browser tab disconnects.
        task = asyncio.create_task(execute())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    # Keep reverse proxies and the browser connected during
                    # long provider requests; this is not simulated progress.
                    yield 'data: {"kind":"heartbeat"}' + chr(10) * 2
                    continue
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
