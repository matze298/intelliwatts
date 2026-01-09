"""Authentication functions."""

from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError
from passlib.context import CryptContext
import os


pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify the password.

    Returns:
        True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash the password.

    Returns:
        The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Create an access token.

    Returns:
        The access token.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
