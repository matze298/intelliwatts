"""Service for generating the weekly plan."""

from typing import Any

from app.config import GLOBAL_SETTINGS, Settings
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.models.user import User
from app.planning.llm import generate_plan
from app.planning.llm_to_icu import llm_json_to_icu_txt
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
    llm_response = generate_plan(summary=summary, language_model=settings.LANGUAGE_MODEL, user=user)
    plan_txt = llm_json_to_icu_txt(llm_response.plan)

    plan = llm_response.plan + "\n\n" + "## intervals.icu workout file (txt)\n\n```text\n\n" + plan_txt + "\n```"
    return {"plan": plan, "summary": summary, "prompt": llm_response.prompt}
