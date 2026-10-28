"""Routes to store user settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.models.user import User
from app.profile import get_profile

router = APIRouter(prefix="/api/settings", tags=["settings"])


class StoreSettingsRequest(BaseModel):
    """Request model for storing user settings."""

    form_type: str = "preferences"
    developer_mode_enabled: bool = False
    system_prompt: str | None = None
    user_prompt: str | None = None


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
    user: Annotated[User, Depends(get_profile)],
) -> dict[str, bool]:
    """Store the user settings.

    Returns:
        A dictionary with a key ``stored`` set to ``True``.

    Raises:
        HTTPException: If the profile cannot be found.
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
        else:
            raise HTTPException(status_code=400, detail="Unknown settings form")

        session.commit()
        return {"stored": True}
