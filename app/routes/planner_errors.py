"""Planner-specific error handling."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


class PlannerErrorRoute(APIRoute):
    """APIRoute that renders the planner fallback page on unexpected errors."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the route handler with planner-specific error rendering.

        Returns:
            A route handler that renders the planner fallback page on crashes.
        """
        original_route_handler = super().get_route_handler()

        async def planner_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except HTTPException:
                raise
            except Exception:
                _LOGGER.exception("Unhandled planner error on %s", request.url.path)
                render_planner_error_response = request.app.state.render_planner_error_response
                return render_planner_error_response(request)

        return planner_route_handler
