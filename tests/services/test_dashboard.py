"""Tests for dashboard presentation helpers."""

from datetime import date

from app.services.dashboard import get_next_workout


def test_get_next_workout_selects_today_and_calculates_duration() -> None:
    """Select today's session and sum its repeated interval duration."""
    # GIVEN a plan with yesterday's session and today's structured intervals
    workouts = [
        {"day": "Monday", "workout_name": "Past", "segments": []},
        {
            "day": "Tuesday",
            "workout_name": "Tempo",
            "description": "Steady work",
            "segments": [{"repeats": 2, "steps": [{"duration_m": 8}, {"duration_m": 3}]}],
        },
    ]

    # WHEN today's session is requested
    result = get_next_workout(workouts, date(2026, 4, 21))

    # THEN it previews the existing workout and its interval duration
    assert result is not None
    assert result.day == "Tuesday"
    assert result.name == "Tempo"
    assert result.description == "Steady work"
    assert result.duration_minutes == 22


def test_get_next_workout_returns_none_when_week_is_over() -> None:
    """Return no preview when all sessions are before the current weekday."""
    # GIVEN a plan whose only workout has already passed
    workouts = [{"day": "Monday", "workout_name": "Endurance", "segments": []}]

    # WHEN checking on Sunday
    result = get_next_workout(workouts, date(2026, 4, 26))

    # THEN there is no next workout preview
    assert result is None
