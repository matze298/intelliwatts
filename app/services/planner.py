"""Service for generating the weekly plan."""

from typing import Any

from app.config import GLOBAL_SETTINGS, Settings
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.models.user import User
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary


def generate_weekly_plan(user: User, settings: Settings = GLOBAL_SETTINGS) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, settings.CACHE_INTERVALS_HOURS)
    raw = client.activities()
    activities = parse_activities(raw)
    load = compute_load(activities)
    summary = build_weekly_summary(
        activities,
        load,
        weekly_sessions=settings.weekly_sessions,
        weekly_hours=settings.weekly_hours,
    )
    plan = generate_plan(summary=summary, language_model=settings.LANGUAGE_MODEL, user=user)
    return {"plan": plan, "summary": summary}
