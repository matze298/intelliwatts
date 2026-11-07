"""Profile-backed settings page rendering."""

from copy import copy
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.user import User
from app.profile import get_profile

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def _settings_page_context(request: Request, user: User) -> dict[str, object]:
    """Build the settings page context for the current user.

    Returns:
        A template context dictionary for the unified settings page.
    """
    app_settings = request.app.state.settings
    prompt_settings = copy(app_settings["settings"])
    prompt_settings.SYSTEM_PROMPT = user.system_prompt_override or app_settings["settings"].SYSTEM_PROMPT
    prompt_settings.USER_PROMPT = user.user_prompt_override or app_settings["settings"].USER_PROMPT
    return {
        "user": user,
        "settings": {**app_settings, "settings": prompt_settings},
        "developer_mode_enabled": user.developer_mode_enabled,
    }


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: Annotated[User, Depends(get_profile)]) -> HTMLResponse:
    """Settings page for the app.

    Returns:
        The settings page as HTML.
    """
    return templates.TemplateResponse(request, "settings.html", _settings_page_context(request, user))
