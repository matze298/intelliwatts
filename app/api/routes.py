"""Routes for the app API."""

from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.intervals.client import IntervalsClient
from app.intervals.load import compute_load
from app.intervals.parser import parse_activity
from app.planning.llm import generate_plan
from app.planning.summary import build_weekly_summary

router = APIRouter()


@router.post("/generate-plan")
def generate_week() -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    client = IntervalsClient(settings.INTERVALS_API_KEY)
    raw = client.activities()

    activities = [parse_activity(a) for a in raw]
    load = compute_load(activities)
    summary = build_weekly_summary(activities, load)

    plan = generate_plan(summary)
    return {"plan": plan, "summary": summary}
