"""Unit tests for the llm_to_icu module."""

import json
import logging

import pytest

from app.planning.llm_to_icu import llm_json_to_icu_txt


def test_llm_json_to_icu_txt_valid_json() -> None:
    """Test with a valid JSON response."""
    # GIVEN a valid JSON response from the AI
    workouts = [
        {
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
                {
                    "title": "Cooldown",
                    "repeats": 1,
                    "steps": [{"duration_m": 10, "power_pct": 40}],
                },
            ],
        },
    ]
    ai_response = f"Here is your plan:###JSON_START###{json.dumps(workouts)}"

    expected_output = (
        "Title: Sweetspot\n\n"
        "Description: A tough sweetspot session.\n\n"
        "Warmup\n"
        "- 10m 50% 90rpm\n"
        "- 5m 60%\n\n"
        "Main set 2x\n"
        "- 15m 90% 85rpm\n"
        "- 5m 50%\n\n"
        "Cooldown\n"
        "- 10m 40%\n\n\n\n"
    )

    # WHEN converting to intervals.icu txt format
    # THEN the output is as expected
    assert llm_json_to_icu_txt(ai_response) == expected_output


def test_llm_json_to_icu_txt_no_json_start_tag() -> None:
    """Test response without the JSON_START tag."""
    # GIVEN a response without the JSON_START tag
    ai_response = '{"plan": "some plan"}'
    # WHEN converting to intervals.icu txt format
    # THEN the output is empty since no workouts are found
    assert not llm_json_to_icu_txt(ai_response)


def test_llm_json_to_icu_txt_invalid_json(caplog: pytest.LogCaptureFixture) -> None:
    """Test with invalid JSON."""
    # GIVEN an invalid JSON response from the AI
    ai_response = "Here is your plan:###JSON_START###this is not json"
    # WHEN converting to intervals.icu txt format
    # THEN a warning is logged and the output indicates failure to parse
    with caplog.at_level(logging.WARNING):
        result = llm_json_to_icu_txt(ai_response)
        assert "Failed to parse JSON from AI response." in caplog.text
    assert result == "Failed to parse workout JSON."


def test_llm_json_to_icu_txt_empty_json_array() -> None:
    """Test with an empty JSON array."""
    # GIVEN a response with an empty JSON array
    ai_response = "Here is your plan:###JSON_START###[]"
    # WHEN converting to intervals.icu txt format
    # THEN the output is empty since there are no workouts
    assert not llm_json_to_icu_txt(ai_response)


def test_llm_json_to_icu_txt_workout_with_no_segments() -> None:
    """Test a workout that has an empty segments list."""
    # GIVEN a workout with an empty segments list
    workouts = [
        {
            "workout_name": "No Segments",
            "description": "This workout has no segments.",
            "segments": [],
        },
    ]
    # WHEN converting to intervals.icu txt format
    ai_response = f"Plan:###JSON_START###{json.dumps(workouts)}"
    # THEN the output is as expected
    expected_output = "Title: No Segments\n\nDescription: This workout has no segments.\n\n\n\n"
    assert llm_json_to_icu_txt(ai_response) == expected_output


def test_llm_json_to_icu_txt_segment_with_no_steps() -> None:
    """Test a segment that has an empty steps list."""
    # GIVEN a segment with an empty steps list
    workouts = [
        {
            "workout_name": "No Steps",
            "description": "This workout has a segment with no steps.",
            "segments": [{"title": "Empty Segment", "repeats": 1, "steps": []}],
        },
    ]
    # WHEN converting to intervals.icu txt format
    ai_response = f"Plan:###JSON_START###{json.dumps(workouts)}"
    expected_output = (
        "Title: No Steps\n\nDescription: This workout has a segment with no steps.\n\nEmpty Segment\n\n\n\n"
    )
    # THEN the output is as expected
    assert llm_json_to_icu_txt(ai_response) == expected_output


@pytest.mark.parametrize(
    ("repeats", "expected_header"),
    [
        (1, "Main set\n"),
        (3, "Main set 3x\n"),
        (0, "Main set\n"),  # Assuming 0 or 1 repeats don't show 'x'
    ],
)
def test_llm_json_to_icu_txt_segment_repeats(repeats: int, expected_header: str) -> None:
    """Test segment header formatting based on the 'repeats' value."""
    # GIVEN a segment with varying repeats
    workouts = [
        {
            "workout_name": "Repeats Test",
            "description": "Testing segment repeats.",
            "segments": [
                {
                    "title": "Main set",
                    "repeats": repeats,
                    "steps": [{"duration_m": 5, "power_pct": 80}],
                },
            ],
        },
    ]
    # WHEN converting to intervals.icu txt format
    ai_response = f"Plan:###JSON_START###{json.dumps(workouts)}"
    # THEN the output header matches the expected format
    expected_output = (
        f"Title: Repeats Test\n\nDescription: Testing segment repeats.\n\n{expected_header}- 5m 80%\n\n\n\n"
    )
    assert llm_json_to_icu_txt(ai_response) == expected_output
