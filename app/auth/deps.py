"""Authentication dependencies."""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.auth.auth import decode_token
from app.db import engine
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current user.

    Args:
        token: The access token.

    Returns:
        The user.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(401, "User not found")
        return user
