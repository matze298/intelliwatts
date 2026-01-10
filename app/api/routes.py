"""Routes for the app API."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.auth.auth import get_current_user_from_token, hash_password
from app.config import GLOBAL_SETTINGS
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.models.user import User, load_user_secrets
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary

router = APIRouter()
_LOGGER = logging.getLogger(__name__)


@router.post("/generate-plan")
def generate_week(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    user_secrets = load_user_secrets(user.id)  # Verify secrets exist
    client = IntervalsClient(
        api_key=user_secrets.intervals_api_key,
        athlete_id=user_secrets.intervals_athlete_id,
        cache_expiration_hours=GLOBAL_SETTINGS.CACHE_INTERVALS_HOURS,
    )

    raw = client.activities()
    activities = parse_activities(raw)
    load = compute_load(activities)
    summary = build_weekly_summary(
        activities,
        load,
        weekly_hours=GLOBAL_SETTINGS.weekly_hours,
        weekly_sessions=GLOBAL_SETTINGS.weekly_sessions,
    )
    plan = generate_plan(summary=summary, user=user, language_model=GLOBAL_SETTINGS.LANGUAGE_MODEL)
    return {"plan": plan, "summary": summary}


def main() -> None:
    """Run the app without FastAPI.

    Raises:
        ValueError: If DEV_USER or DEV_PASSWORD is not set.
    """
    if GLOBAL_SETTINGS.DEV_USER is None or GLOBAL_SETTINGS.DEV_PASSWORD is None:
        msg = "DEV_USER and DEV_PASSWORD must be set to run main()"
        raise ValueError(msg)
    content = generate_week(
        user=User(email=GLOBAL_SETTINGS.DEV_USER, password_hash=hash_password(GLOBAL_SETTINGS.DEV_PASSWORD)),
    )
    _LOGGER.info("Training plan: \n 10*'=' \n)")
    _LOGGER.info(content["plan"])
    _LOGGER.info(3 * "\n")
    _LOGGER.info("Weekly Summary: \n 10*'=' \n")
    _LOGGER.info(content["summary"])
