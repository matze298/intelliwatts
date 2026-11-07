"""Compact, read-only calendar context for cross-sport weekly scheduling."""

from __future__ import annotations

from datetime import date, timedelta
from operator import itemgetter

import requests

from app.intervals.client import IntervalsClient, IntervalsResponseError


def load_week_commitments(client: IntervalsClient, *, week_start: date, today: date) -> str:
    """Fetch existing upcoming calendar commitments without blocking planning on API errors.

    Returns:
        A compact read-only list of upcoming scheduled sports.
    """
    oldest = max(today, week_start)
    newest = week_start + timedelta(days=6)
    if oldest > newest:
        return "No upcoming calendar dates in the selected week."

    try:
        events = client.calendar_events(oldest=oldest, newest=newest)
    except requests.RequestException, IntervalsResponseError, ValueError:
        return "Upcoming calendar events unavailable; do not assume there are none."

    return format_week_commitments(events, oldest=oldest, newest=newest)


def format_week_commitments(events: list[object], *, oldest: date, newest: date) -> str:
    """Keep only planned WORKOUT details relevant to the chosen week.

    Returns:
        A short calendar summary suitable for the coach's prompt.
    """
    output: list[tuple[date, str]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("category") != "WORKOUT":
            continue
        raw_date = event.get("start_date_local")
        if not isinstance(raw_date, str):
            continue
        try:
            event_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            continue
        if not oldest <= event_date <= newest:
            continue
        sport = _plain_text(event.get("type"), "Unspecified sport")
        name = _plain_text(event.get("name"), "")
        duration = _duration_label(event.get("moving_time"))
        detail = f"{event_date.isoformat()} Planned {sport}"
        if name and name.casefold() != sport.casefold():
            detail += f" ({name})"
        if duration:
            detail += f", {duration}"
        output.append((event_date, detail))

    output.sort(key=itemgetter(0))
    if not output:
        return "No scheduled workouts found in the selected week."
    return (
        "Scheduled workouts (not completed training; non-cycling entries do not use cycling hours/sessions): "
        + "; ".join(line for _, line in output)
    )


def _plain_text(value: object, default: str) -> str:
    """Sanitize external labels to short, single-line text.

    Returns:
        The sanitized label or its fallback.
    """
    if not isinstance(value, str) or not value.strip():
        return default
    return " ".join(value.replace("\\n", " ").replace("\\r", " ").split())[:65]


def _duration_label(seconds: object) -> str:
    """Format optional workout duration without inventing missing values.

    Returns:
        A readable duration, or empty when absent.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds <= 0:
        return ""
    return f"{round(seconds / 60)} min"
