"""Defines the User and UserSecrets models."""

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Field, Session, SQLModel, select

from app.db import engine
from app.security.crypto import decrypt


class User(SQLModel, table=True):
    """Defines a user."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str
    password_hash: str


class UserSecrets(SQLModel, table=True):
    """Defines the secrets for a user."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    intervals_athlete_id: str
    intervals_api_key: bytes
    openai_api_key: bytes | None = None
    gemini_api_key: bytes | None = None


@dataclass
class DecryptedUserSecrets:
    """Decrypted user secrets."""

    intervals_athlete_id: str
    intervals_api_key: str
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


def load_user_secrets(user_id: uuid.UUID) -> DecryptedUserSecrets:
    """Load and decrypt secrets for a user.

    Args:
        user_id: The ID of the user.

    Returns:
        The decrypted user secrets.

    Raises:
        HTTPException: If no secrets are found for the user.
    """
    with Session(engine) as session:
        secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user_id)).first()
        if not secrets:
            raise HTTPException(
                status_code=404,
                detail="No API secrets configured for this user",
            )

        return DecryptedUserSecrets(
            intervals_athlete_id=secrets.intervals_athlete_id,
            intervals_api_key=decrypt(secrets.intervals_api_key),
            openai_api_key=decrypt(secrets.openai_api_key) if secrets.openai_api_key else None,
            gemini_api_key=decrypt(secrets.gemini_api_key) if secrets.gemini_api_key else None,
        )
