"""Authentication functions."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session

from app.config import GLOBAL_SETTINGS
from app.db import engine
from app.models.user import User

# Password hashing context
PWD_CONTEXT = CryptContext(schemes=["bcrypt"])

# JWT (JSON Web Token) settings
SECRET_KEY = GLOBAL_SETTINGS.JWT_SECRET_KEY
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify the password.

    Returns:
        True if the password is correct, False otherwise.
    """
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash the password.

    Returns:
        The hashed password.
    """
    return PWD_CONTEXT.hash(password)


def create_access_token(data: dict, acess_token_expire_minutes: int = 60) -> str:
    """Create an access token.

    Returns:
        The access token.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=acess_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """Decode the token.

    Returns:
        The decoded token.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    except JWTError:
        return None


def get_current_user_from_token(request: Request) -> User | None:
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
        user = session.get(User, UUID(user_id))
        if not user:
            return None
        return user
