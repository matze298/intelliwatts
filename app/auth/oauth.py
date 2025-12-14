"""Oauth for intervals.icu."""

from typing import Any

import requests

from app.config import settings

AUTH_URL = "https://intervals.icu/oauth/authorize"
TOKEN_URL = "https://intervals.icu/oauth/token"


def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange code for token.

    Returns:
        The token.
    """
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.INTERVALS_CLIENT_ID,
            "client_secret": settings.INTERVALS_CLIENT_SECRET,
            "redirect_uri": settings.INTERVALS_REDIRECT_URI,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()
