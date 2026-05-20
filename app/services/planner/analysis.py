"""Analysis loading helpers for weekly planning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.intervals.analysis import compute_analysis
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.wellness import parse_wellness_list

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient
    from app.intervals.models import AnalysisResult


def get_analysis(
    client: IntervalsClient,
    analysis_days: int,
    minimum_lookback_days: int = 42,
) -> AnalysisResult:
    """Perform the full sports science analysis for the athlete.

    Args:
        client: The Intervals client used to fetch raw athlete data.
        analysis_days: The requested analysis lookback window.
        minimum_lookback_days: The minimum data window to enforce for wellness analysis.

    Returns:
        The computed analysis bundle for the athlete.
    """
    # Use max required days (e.g. 120d for PMC, 30d for FTP trajectory, 42d for wellness)
    lookback_days = max(analysis_days, minimum_lookback_days)
    raw_activities = client.activities(days=lookback_days)
    raw_wellness = client.wellness(days=lookback_days)

    return compute_analysis(
        parse_activities(raw_activities),
        wellness_data=parse_wellness_list(raw_wellness),
        client=client,
    )
