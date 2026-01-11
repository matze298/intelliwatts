"""Routes to store and retrieve secrets."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.auth import get_current_user_from_token
from app.db import engine
from app.models.user import User, UserSecrets

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
                session.delete(existing_secrets)

            new_secrets = user.create_secrets(
                intervals_athlete_id=athlete_id,
                intervals_api_key=intervals_api_key,
                openai_api_key=openai_api_key,
                gemini_api_key=gemini_api_key,
            )
            session.add(new_secrets)
            session.commit()
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to store secrets: {e}") from e
        else:
            return {"stored": True}
