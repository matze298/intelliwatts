"""Unit tests for the intervals_payload module."""

import json
import logging
from typing import TYPE_CHECKING

from app.planning.intervals_payload import extract_workout_json, workout_json_to_icu_txt

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_extract_workout_json_valid_payload() -> None:
    """Extract workout JSON from a valid AI response payload."""
    # GIVEN an AI response that contains a JSON payload
    workouts = [
        {
            "workout_name": "Sweetspot",
            "description": "A tough sweetspot session.",
            "segments": [],
        },
    ]
    ai_response = f"Plan text before JSON###JSON_START###{json.dumps(workouts)}###JSON_END###"

    # WHEN the workout JSON is extracted
    result = extract_workout_json(ai_response)

    # THEN the parsed workout data should be returned
    assert result == workouts


def test_extract_workout_json_without_marker_returns_empty_list() -> None:
    """Return an empty workout list when the response has no JSON marker."""
    # GIVEN an AI response without a JSON payload marker
    ai_response = "Plan text only"

    # WHEN the workout JSON is extracted
    result = extract_workout_json(ai_response)

    # THEN no workouts should be returned
    assert result == []


def test_extract_workout_json_rejects_non_list_payload(caplog: LogCaptureFixture) -> None:
    """Return an empty workout list when the JSON payload is not a list."""
    # GIVEN an AI response whose JSON payload is an object instead of a workout list.
    ai_response = 'Plan text###JSON_START###{"workout_name": "Sweetspot"}###JSON_END###'

    # WHEN the workout JSON is extracted.
    with caplog.at_level(logging.WARNING):
        result = extract_workout_json(ai_response)

    # THEN no structured workouts should be returned and the invalid payload should be logged.
    assert result == []
    assert "Ignoring malformed workout JSON payload" in caplog.text


def test_extract_workout_json_rejects_non_object_workouts(caplog: LogCaptureFixture) -> None:
    """Return an empty workout list when the JSON list contains invalid items."""
    # GIVEN an AI response whose JSON payload contains a non-object workout.
    ai_response = 'Plan text###JSON_START###["bad-workout"]###JSON_END###'

    # WHEN the workout JSON is extracted.
    with caplog.at_level(logging.WARNING):
        result = extract_workout_json(ai_response)

    # THEN no structured workouts should be returned and the invalid payload should be logged.
    assert result == []
    assert "Ignoring malformed workout JSON payload" in caplog.text


def test_workout_json_to_icu_txt_formats_workout_text() -> None:
    """Render a workout as Intervals.icu text."""
    # GIVEN a structured workout payload
    workout = {
        "workout_name": "Sweetspot",
        "description": "A tough sweetspot session.",
        "segments": [
            {
                "title": "Warmup",
                "repeats": 1,
                "steps": [
                    {"duration_m": 10, "power_pct": 50, "rpm": 90},
                    {"duration_m": 5, "power_pct": 60},
                ],
            },
            {
                "title": "Main set",
                "repeats": 2,
                "steps": [
                    {"duration_m": 15, "power_pct": 90, "rpm": 85},
                    {"duration_m": 5, "power_pct": 50},
                ],
            },
        ],
    }

    # WHEN the workout is rendered as Intervals.icu text
    result = workout_json_to_icu_txt(workout)

    # THEN the formatted workout text should match the expected structure
    assert result == (
        "Title: Sweetspot\n\n"
        "Description: A tough sweetspot session.\n\n"
        "Warmup\n"
        "- 10m 50% 90rpm\n"
        "- 5m 60%\n\n"
        "Main set 2x\n"
        "- 15m 90% 85rpm\n"
        "- 5m 50%\n\n\n\n"
    )
