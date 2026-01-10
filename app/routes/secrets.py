"""Routes to store and retrieve secrets."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.auth import get_current_user_from_token
from app.db import engine
from app.models.user import User, UserSecrets
from app.security.crypto import encrypt

router = APIRouter(prefix="/secrets")


@router.post("/store")
def store(
    athlete_id: str,
    intervals_api_key: str,
    user: Annotated[User, Depends(get_current_user_from_token)],
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> dict[str, bool]:
    """Store the secrets for the user.

    Args:
        athlete_id: The intervals.icu athlete id.
        intervals_api_key: The intervals.icu api key.
        openai_api_key: The openai api key.
        gemini_api_key: The gemini api key.
        user: The current user. Resolved via dependency injection.

    Returns:
        A dictionary with a key "stored" and a value of True.

    Raises:
        HTTPException: If storing the secrets fails.
    """
    with Session(engine) as session:
        try:
            existing_secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user.id)).first()

            if existing_secrets:
                existing_secrets.intervals_athlete_id = athlete_id
                existing_secrets.intervals_api_key = encrypt(intervals_api_key)
                if openai_api_key:
                    existing_secrets.openai_api_key = encrypt(openai_api_key)
                if gemini_api_key:
                    existing_secrets.gemini_api_key = encrypt(gemini_api_key)
                session.add(existing_secrets)
            else:
                new_secrets = UserSecrets(
                    user_id=user.id,
                    intervals_athlete_id=athlete_id,
                    intervals_api_key=encrypt(intervals_api_key),
                    openai_api_key=encrypt(openai_api_key) if openai_api_key else None,
                    gemini_api_key=encrypt(gemini_api_key) if gemini_api_key else None,
                )
                session.add(new_secrets)
            session.commit()
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to store secrets: {e}") from e
        else:
            return {"stored": True}
