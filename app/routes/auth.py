"""Authentication routes for the app."""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.db import engine
from app.models.user import User
from app.auth.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth")


@router.post("/register")
def register(email: str, password: str) -> dict[str, bool]:
    """Register a new user.

    Args:
        email: The email of the user.
        password: The password of the user.

    Returns:
        A dictionary with a key "ok" and a value of True.

    Raises:
        HTTPException: If the user already exists.
    """
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            raise HTTPException(400, "User exists")
        user = User(email=email, password_hash=hash_password(password))
        session.add(user)
        session.commit()
        return {"ok": True}


@router.post("/login")
def login(email: str, password: str) -> dict[str, str]:
    """Login a user.

    Args:
        email: The email of the user.
        password: The password of the user.

    Returns:
        A dictionary with the access token and token type.

    Raises:
        HTTPException: If the user does not exist or the password is incorrect.
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer"}
