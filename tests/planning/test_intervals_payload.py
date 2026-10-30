"""Unit tests for the intervals_payload module."""

from app.planning.intervals_payload import workout_json_to_icu_txt


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
                    {"duration_m": 10, "power_pct": "50-60", "rpm": "90"},
                    {"duration_m": 5, "power_pct": "60-70"},
                ],
            },
            {
                "title": "Main set",
                "repeats": 2,
                "steps": [
                    {"duration_m": 15, "power_pct": "90", "rpm": "85"},
                    {"duration_m": 5, "power_pct": "50-60"},
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
        "- 10m 50-60% 90rpm\n"
        "- 5m 60-70%\n\n"
        "Main set 2x\n"
        "- 15m 90% 85rpm\n"
        "- 5m 50-60%\n\n\n\n"
    )
