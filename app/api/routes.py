"""Routes for the app API."""

from typing import Any, Annotated

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.models.user import load_user_secrets, User
from app.config import GLOBAL_SETTINGS
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary

router = APIRouter()


@router.post("/generate-plan")
def generate_week(user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
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
    """Run the app without FastAPI."""
    content = generate_week(user=User(id=1, email="test", password_hash="hash"))
    print("Training plan: \n 10*'=' \n", content["plan"])
    print(3 * "\n")
    print("Weekly Summary: \n 10*'=' \n", content["summary"])
