"""Single-password access gate for the whole application."""

import hashlib
import hmac
import secrets
import time
from collections import deque
from threading import Lock

import fastapi
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings

Request = fastapi.Request
templates = Jinja2Templates(directory="app/templates")
COOKIE_NAME = "intelliwatts_session"
SESSION_SECONDS = 12 * 60 * 60
MAX_LOGIN_ATTEMPTS = 5
_FAILURES: deque[float] = deque()
_LOCK = Lock()


def _signature(timestamp: str) -> str:
    settings = get_settings()
    key = hmac.digest(settings.SESSION_SECRET.encode(), settings.APP_PASSWORD.encode(), "sha256")
    return hmac.new(key, timestamp.encode(), hashlib.sha256).hexdigest()


def _valid_session(value: str) -> bool:
    try:
        timestamp, signature = value.split(".", 1)
        age = time.time() - int(timestamp)
        return 0 <= age <= SESSION_SECONDS and hmac.compare_digest(signature, _signature(timestamp))
    except ValueError, OverflowError:
        return False


class AccessMiddleware(BaseHTTPMiddleware):
    """Require a valid session for all routes except health, login and static assets."""

    @staticmethod
    def is_public(path: str) -> bool:
        """Return whether the path is accessible without a session."""
        return path in {"/health", "/login"} or path.startswith("/static/")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Enforce the session and request origin for each request.

        Returns:
            The requested response or an access error.
        """
        settings = get_settings()
        path = request.url.path
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin", "")
            if not secrets.compare_digest(origin.encode(), settings.APP_ORIGIN.encode()):
                return JSONResponse({"detail": "Invalid request origin"}, status_code=403)
        public = self.is_public(path)
        if not public and not _valid_session(request.cookies.get(COOKIE_NAME, "")):
            if path.startswith("/api/") or request.method not in {"GET", "HEAD"}:
                return JSONResponse({"detail": "Authentication required"}, status_code=401)
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)


def _login_response(request: Request, *, error: str | None = None, status_code: int = 200) -> Response:
    """Render the Tailwind sign-in page.

    Returns:
        The rendered sign-in page.
    """
    return templates.TemplateResponse(
        request,
        "login.html",
        {"user": None, "error": error},
        status_code=status_code,
    )


def login_page(request: Request) -> Response:
    """Render a password-only sign-in form.

    Returns:
        The sign-in page.
    """
    return _login_response(request)


async def login(request: Request) -> Response:
    """Verify the password and issue a time-limited signed cookie.

    Returns:
        A redirect with a session cookie or an error.
    """
    form = await request.form()
    password = form.get("password", "")
    settings = get_settings()
    with _LOCK:
        now = time.monotonic()
        while _FAILURES and _FAILURES[0] <= now - 60:
            _FAILURES.popleft()
        if len(_FAILURES) >= MAX_LOGIN_ATTEMPTS:
            return _login_response(request, error="Too many attempts. Try again in a minute.", status_code=429)
        valid = isinstance(password, str) and secrets.compare_digest(password.encode(), settings.APP_PASSWORD.encode())
        if not valid:
            _FAILURES.append(now)
    if not valid:
        return _login_response(request, error="Invalid password", status_code=401)
    timestamp = str(int(time.time()))
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        f"{timestamp}.{_signature(timestamp)}",
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    return response


def logout() -> Response:
    """Clear the session cookie.

    Returns:
        A redirect to the login page.
    """
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, secure=get_settings().SESSION_COOKIE_SECURE, httponly=True, samesite="lax")
    return response
