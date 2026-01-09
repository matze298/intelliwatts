"""Authentication dependencies."""

from fastapi import Request
from sqlmodel import Session

from app.auth.auth import decode_token
from app.db import engine
from app.models.user import User


def get_current_user(request: Request) -> User | None:
    """Get the current user from the access token cookie.

    Args:
        request: The FastAPI request object.

    Returns:
        The user or None if not authenticated.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    # The token is expected to be in the format "Bearer <token>"
    try:
        _, token = token.split()
    except ValueError:
        return None

    user_id = decode_token(token)
    if not user_id:
        return None
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return None
        return user
