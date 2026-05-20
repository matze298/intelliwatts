"""Routes to store user settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.auth import get_current_user_from_token
from app.config import get_settings
from app.db import engine
from app.models.user import User, UserSecrets

router = APIRouter(prefix="/api/settings", tags=["settings"])


class StoreSettingsRequest(BaseModel):
    """Request model for storing user settings."""

    form_type: str = "preferences"
    developer_mode_enabled: bool = False
    system_prompt: str | None = None
    user_prompt: str | None = None
    athlete_id: str | None = None
    intervals_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


def _normalize_prompt(value: str | None) -> str | None:
    """Normalize a prompt override value.

    Returns:
        The trimmed prompt value, or ``None`` when the input is empty.
    """
    if value is None:
        return None
    prompt = value.strip()
    return prompt or None


@router.post("")
def store(
    request: StoreSettingsRequest,
    user: Annotated[User, Depends(get_current_user_from_token)],
) -> dict[str, bool]:
    """Store the user settings.

    Returns:
        A dictionary with a key ``stored`` set to ``True``.

    Raises:
        HTTPException: If the authenticated user cannot be found.
    """
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        session.add(db_user)

        if request.form_type == "preferences":
            db_user.developer_mode_enabled = request.developer_mode_enabled
        elif request.form_type == "developer_prompt":
            if not db_user.developer_mode_enabled:
                raise HTTPException(status_code=403, detail="Developer mode is required")

            settings = get_settings()
            system_prompt = _normalize_prompt(request.system_prompt)
            user_prompt = _normalize_prompt(request.user_prompt)
            if system_prompt:
                settings.SYSTEM_PROMPT = system_prompt
            if user_prompt:
                settings.USER_PROMPT = user_prompt
        elif request.form_type == "secrets":
            athlete_id = _normalize_prompt(request.athlete_id)
            intervals_api_key = _normalize_prompt(request.intervals_api_key)
            if not athlete_id or not intervals_api_key:
                raise HTTPException(status_code=400, detail="intervals.icu secrets are required")

            existing_secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user.id)).first()
            if existing_secrets:
                session.delete(existing_secrets)

            new_secrets = db_user.create_secrets(
                intervals_athlete_id=athlete_id,
                intervals_api_key=intervals_api_key,
                openai_api_key=_normalize_prompt(request.openai_api_key),
                gemini_api_key=_normalize_prompt(request.gemini_api_key),
            )
            session.add(new_secrets)
        else:
            raise HTTPException(status_code=400, detail="Unknown settings form")

        session.commit()
        return {"stored": True}
