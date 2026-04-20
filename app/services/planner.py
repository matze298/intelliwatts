"""Service for generating the weekly plan."""

from typing import TYPE_CHECKING, Any

from app.config import GLOBAL_SETTINGS, Settings
from app.intervals.analysis import compute_athlete_status
from app.intervals.client import IntervalsClient
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.wellness import parse_wellness_list
from app.planning.llm import generate_plan
from app.planning.llm_to_icu import llm_json_to_icu_txt
from app.planning.summary import PlanningConstraints, build_weekly_summary

if TYPE_CHECKING:
    from app.models.user import User


def generate_weekly_plan(
    user: User, settings: Settings = GLOBAL_SETTINGS, *, use_wellness: bool = True
) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, settings.CACHE_INTERVALS_HOURS)

    # Fetch and parse activities
    raw_activities = client.activities(days=settings.ANALYSIS_DAYS)
    activities = parse_activities(raw_activities)

    # Fetch and parse wellness data if requested
    wellness = None
    if use_wellness:
        raw_wellness = client.wellness(days=settings.ANALYSIS_DAYS)
        wellness = parse_wellness_list(raw_wellness)

    # Compute athlete status (load and wellness trends)
    status = compute_athlete_status(activities, wellness_data=wellness)

    constraints = PlanningConstraints(
        weekly_hours=settings.weekly_hours,
        weekly_sessions=settings.weekly_sessions,
        primary_goal="increase_ftp",  # Default for now
    )

    summary = build_weekly_summary(
        activities,
        status.load,
        constraints=constraints,
        wellness_summary=status.wellness,
    )
    llm_response = generate_plan(summary=summary, language_model=settings.LANGUAGE_MODEL, user=user)
    plan_txt = llm_json_to_icu_txt(llm_response.plan)

    plan = llm_response.plan + "\n\n" + "## intervals.icu workout file (txt)\n\n```text\n\n" + plan_txt + "\n```"
    return {"plan": plan, "summary": summary, "prompt": llm_response.prompt}
