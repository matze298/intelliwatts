"""Routes to store and retrieve secrets."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.deps import get_current_user
from app.db import engine
from app.models.user import User, UserSecrets, load_user_secrets
from app.security.crypto import encrypt

router = APIRouter(prefix="/secrets")

user_dependency = Depends(get_current_user)


@router.post("/store")
def store(
    athlete_id: str,
    intervals_api_key: str,
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
    user=user_dependency,  # noqa:ANN001
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
    """
    with Session(engine) as session:
        item = UserSecrets(
            user_id=user.id,
            intervals_athlete_id=athlete_id,
            intervals_api_key=encrypt(intervals_api_key),
            openai_api_key=encrypt(openai_api_key) if openai_api_key else None,
            gemini_api_key=encrypt(gemini_api_key) if gemini_api_key else None,
        )
        session.add(item)
        session.commit()
        return {"stored": True}


@router.get("/get")
def get_secrets(user: Annotated[User, Depends(get_current_user)]) -> dict[str, str | None]:
    """Retrieve the secrets for the user.

    Args:
        user: The current user. Resolved via dependency injection.

    Returns:
        A dictionary with the secrets.
    """
    secrets = load_user_secrets(user.id)  # Verify secrets exist
    return asdict(secrets)
