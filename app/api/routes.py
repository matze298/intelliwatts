"""Routes for the app API."""

from typing import Any

from fastapi import APIRouter

from app.config import GLOBAL_SETTINGS
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser.activity import parse_activities
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary

router = APIRouter()


@router.post("/generate-plan")
def generate_week() -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    client = IntervalsClient(
        GLOBAL_SETTINGS.INTERVALS_API_KEY,
        GLOBAL_SETTINGS.INTERVALS_ATHLETE_ID,
        GLOBAL_SETTINGS.CACHE_INTERVALS_HOURS,
    )
    raw = client.activities()
    activities = parse_activities(raw)
    load = compute_load(activities)
    summary = build_weekly_summary(
        activities, load, weekly_hours=GLOBAL_SETTINGS.weekly_hours, weekly_sessions=GLOBAL_SETTINGS.weekly_sessions
    )
    plan = generate_plan(summary)
    return {"plan": plan, "summary": summary}


def main() -> None:
    """Run the app without FastAPI."""
    content = generate_week()
    print("Training plan: \n 10*'=' \n", content["plan"])
    print(3 * "\n")
    print("Weekly Summary: \n 10*'=' \n", content["summary"])
