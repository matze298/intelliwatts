"""Planner-specific error handling."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from google.genai.errors import APIError as GeminiAPIError
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import ValidationError
from requests import ConnectionError as RequestsConnectionError
from requests import HTTPError
from requests import Timeout as RequestsTimeout

_LOGGER = logging.getLogger(__name__)


def planner_failure_reason(error: Exception) -> str:
    """Return a concise, safe reason for a failed planner request."""
    resolvers = (
        _httpx_failure_reason,
        _intervals_failure_reason,
        _openai_failure_reason,
        _gemini_failure_reason,
        _configuration_failure_reason,
        _model_output_failure_reason,
    )
    return next(
        (reason for resolver in resolvers if (reason := resolver(error)) is not None),
        "An unexpected server error prevented this planner action. Please try again.",
    )


def _httpx_failure_reason(error: Exception) -> str | None:
    module = type(error).__module__
    name = type(error).__name__
    if not module.startswith("httpx"):
        return None
    if "Timeout" in name:
        return "Gemini took too long to generate a response. Please try again."
    if "Connect" in name:
        return "The app could not connect to Gemini. Check your connection and try again."
    return None


def _intervals_failure_reason(error: Exception) -> str | None:
    if isinstance(error, RequestsTimeout):
        return "Intervals.icu timed out while loading your training data. Please try again."
    if isinstance(error, RequestsConnectionError):
        return "The app could not connect to Intervals.icu. Check your connection and try again."
    if isinstance(error, HTTPError):
        status_code = error.response.status_code if error.response is not None else None
        if status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
            return "Intervals.icu rejected the configured API key. Check the INTERVALS_API_KEY setting."
        return _model_status_reason("Intervals.icu", status_code)
    return None


def _openai_failure_reason(error: Exception) -> str | None:
    if isinstance(error, APITimeoutError):
        return "OpenAI took too long to generate a response. Please try again."
    if isinstance(error, APIConnectionError):
        return "The app could not connect to OpenAI. Check your connection and try again."
    if isinstance(error, RateLimitError):
        return "The OpenAI service is rate limited right now. Wait a little and try again."
    if isinstance(error, AuthenticationError):
        return "OpenAI rejected its API key. Check the OPENAI_API_KEY setting."
    if isinstance(error, APIStatusError):
        return _model_status_reason("OpenAI", error.status_code)
    return None


def _gemini_failure_reason(error: Exception) -> str | None:
    if not isinstance(error, GeminiAPIError):
        return None
    status_code = error.code if isinstance(error.code, int) else None
    if status_code == HTTPStatus.REQUEST_TIMEOUT:
        return "Gemini took too long to generate a response. Please try again."
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return "The Gemini service is rate limited right now. Wait a little and try again."
    if status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
        return "Gemini rejected its API key. Check the GEMINI_API_KEY setting."
    return _model_status_reason("Gemini", status_code)


def _configuration_failure_reason(error: Exception) -> str | None:
    if not isinstance(error, RuntimeError) or "API_KEY must be set" not in str(error):
        return None
    variable = "OPENAI_API_KEY" if "OPENAI_API_KEY" in str(error) else "GEMINI_API_KEY"
    return f"The selected AI provider is missing its {variable} setting."


def _model_output_failure_reason(error: Exception) -> str | None:
    if isinstance(error, ValidationError):
        return "The AI service returned a plan in an unexpected format. Please try again."
    if isinstance(error, NotImplementedError):
        return "The selected AI model is not supported. Choose another model in Settings."
    return None


def _model_status_reason(provider: str, status_code: int | None) -> str:
    if not isinstance(status_code, int):
        return f"{provider} could not complete the request. Please try again."
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return f"{provider} is rate limited right now. Wait a little and try again."
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return f"{provider} is temporarily unavailable. Please try again shortly."
    return f"{provider} returned an error (HTTP {status_code}). Check its configuration and try again."


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
            except Exception as exc:
                _LOGGER.exception("Unhandled planner error on %s", request.url.path)
                request.state.planner_error_reason = planner_failure_reason(exc)
                render_planner_error_response = request.app.state.render_planner_error_response
                return render_planner_error_response(request)

        return planner_route_handler
