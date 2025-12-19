"""Routes for the app API."""

from typing import Any

from fastapi import APIRouter

from app.config import settings
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
        settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, settings.CACHE_INTERVALS_HOURS
    )
    raw = client.activities()
    activities = parse_activities(raw)
    load = compute_load(activities)
    summary = build_weekly_summary(activities, load)
    plan = generate_plan(summary)
    return {"plan": plan, "summary": summary}


def main() -> None:
    """Run the app without FastAPI."""
    content = generate_week()
    print("Training plan: \n 10*'=' \n", content["plan"])
    print(3 * "\n")
    print("Weekly Summary: \n 10*'=' \n", content["summary"])
