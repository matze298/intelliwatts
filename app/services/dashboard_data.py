"""On-demand Intervals.icu Dashboard analytics loading and API caching."""

from datetime import timedelta

import requests
from requests_cache import CachedSession

from app.config import Settings
from app.intervals.analysis import compute_analysis
from app.intervals.client import IntervalsClient
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.wellness import parse_wellness_list
from app.intervals.models import AnalysisResult


def load_dashboard_analysis(settings: Settings, *, display_days: int) -> AnalysisResult:
    """Fetch only the history required by the selected Dashboard range.

    Returns:
        Parsed and calculated Dashboard metrics, reusing cached API responses.
    """
    lookback_days = max(settings.ANALYSIS_DAYS, display_days)
    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )
    elif settings.DASHBOARD_CACHE_MINUTES > 0:
        # Different date-range queries have different oldest-date URL parameters.
        session = CachedSession(
            "dashboard_intervals_cache",
            backend="sqlite",
            expire_after=timedelta(minutes=settings.DASHBOARD_CACHE_MINUTES),
        )

    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session)
    activities = parse_activities(client.activities(days=lookback_days))
    wellness = parse_wellness_list(client.wellness(days=lookback_days))
    return compute_analysis(activities, display_days=display_days, wellness_data=wellness, client=client)
