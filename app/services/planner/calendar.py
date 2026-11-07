"""Compact, read-only calendar context for cross-sport weekly scheduling."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import requests

from app.intervals.client import IntervalsClient, IntervalsResponseError

RACE_CATEGORIES = {"RACE_A", "RACE_B", "RACE_C"}
DISPLAY_CATEGORIES = RACE_CATEGORIES | {"WORKOUT"}
MAX_EVENTS = 12


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
    except (requests.RequestException, IntervalsResponseError, ValueError):
        return "Upcoming calendar events unavailable; do not assume there are none."

    return format_week_commitments(events, oldest=oldest, newest=newest)


def format_week_commitments(events: list[object], *, oldest: date, newest: date) -> str:
    """Keep only sport/date/duration details relevant to the chosen week.

    Returns:
        A short calendar summary suitable for the coach's prompt.
    """
    output: list[tuple[date, str]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        category = event.get("category")
        if category not in DISPLAY_CATEGORIES:
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
        kind = "Race" if category in RACE_CATEGORIES else "Planned"
        detail = f"{event_date.isoformat()} {kind} {sport}"
        if name and name.casefold() != sport.casefold():
            detail += f" ({name})"
        if duration:
            detail += f", {duration}"
        output.append((event_date, detail))

    output.sort(key=lambda pair: pair[0])
    if not output:
        return "No scheduled sports or races found in the selected week."
    compact = "; ".join(line for _, line in output[:MAX_EVENTS])
    if len(output) > MAX_EVENTS:
        compact += f"; plus {len(output) - MAX_EVENTS} more events"
    return "Scheduled calendar commitments (not completed training): " + compact


def _plain_text(value: Any, default: str) -> str:
    """Sanitize short external labels so calendar text cannot inject instructions."""
    if not isinstance(value, str) or not value.strip():
        return default
    return " ".join(value.split())[:65]


def _duration_label(seconds: Any) -> str:
    """Format optional workout duration without inventing missing values."""
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds <= 0:
        return ""
    return f"{round(seconds / 60)} min"
