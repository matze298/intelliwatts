"""Routes to store and retrieve secrets."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.auth import get_current_user_from_token
from app.db import engine
from app.models.user import User, UserSecrets

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class StoreSecretsRequest(BaseModel):
    """Request model for storing secrets."""

    athlete_id: str
    intervals_api_key: str
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


@router.post("")
def store(
    request: StoreSecretsRequest,
    user: Annotated[User, Depends(get_current_user_from_token)],
) -> dict[str, bool]:
    """Store the secrets for the user.

    Args:
        request: The secrets to store.
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
                intervals_athlete_id=request.athlete_id,
                intervals_api_key=request.intervals_api_key,
                openai_api_key=request.openai_api_key,
                gemini_api_key=request.gemini_api_key,
            )
            session.add(new_secrets)
            session.commit()
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to store secrets: {e}") from e
        else:
            return {"stored": True}
