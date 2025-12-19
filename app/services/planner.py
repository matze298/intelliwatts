"""Service for generating the weekly plan."""

from typing import Any

from app.config import settings
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary


def generate_weekly_plan() -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    client = IntervalsClient(
        settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, settings.CACHE_INTERVALS_HOURS
    )
    raw = client.activities()
    activities = parse_activities(raw)
    load = compute_load(activities)
    summary = build_weekly_summary(activities, load)
    plan = generate_plan(summary)
    return {"plan": plan, "summary": summary}
