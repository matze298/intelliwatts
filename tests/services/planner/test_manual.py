"""Regression tests for browser-based manual LLM planning."""

from datetime import date

import pytest

from app.services.planner.manual import format_manual_prompt, parse_manual_response

_MESSAGES = [
    {"role": "system", "content": "Coach system instructions"},
    {"role": "user", "content": "Athlete context and selected week"},
]


def test_manual_prompt_contains_full_messages_and_response_schema() -> None:
    """The copied prompt carries both original messages and the output contract."""
    # GIVEN the full messages that automatic generation would send.
    # WHEN preparing a prompt for an external model.
    prompt = format_manual_prompt(_MESSAGES)
    # THEN the instructions, athlete context and structured schema remain visible.
    assert "Coach system instructions" in prompt
    assert "Athlete context and selected week" in prompt
    assert "plan_markdown" in prompt
    assert "workouts" in prompt
    assert "duration_m" in prompt
    assert "intelliwatts-plan.json" in prompt
    assert "downloadable .json file" in prompt
    assert "single item" in prompt
    assert "straight ASCII double quotes" in prompt


def test_manual_response_parses_json_code_fence() -> None:
    """Pasted JSON may be surrounded by an ordinary JSON code fence."""
    # GIVEN a complete structured model response.
    response = '```json\n{"plan_markdown":"# Easy week","workouts":[]}\n```'
    # WHEN importing it for a selected week.
    result = parse_manual_response(response, messages=_MESSAGES, week_start=date(2026, 11, 9))
    # THEN it preserves the original prompt and structured output.
    assert result.plan == "# Easy week"
    assert result.prompt == _MESSAGES
    assert result.workouts == []


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ("not JSON", "must contain valid JSON"),
        ("{}", "must contain valid JSON"),
        ('{"plan_markdown":"","workouts":[]}', "plan_markdown must not be empty"),
        ("", "Paste the model"),
    ],
)
def test_manual_response_rejects_invalid_content(response: str, message: str) -> None:
    """Invalid output must not be accepted for persistence."""
    # GIVEN a response without the required valid structured content.
    # WHEN parsing it.
    # THEN validation returns an actionable failure.
    with pytest.raises(ValueError, match=message):
        parse_manual_response(response, messages=_MESSAGES, week_start=date(2026, 11, 9))


def test_manual_response_rejects_out_of_week_workout() -> None:
    """A pasted workout cannot be saved into a different calendar week."""
    # GIVEN a valid schema with a workout dated outside the selected week.
    response = (
        '{"plan_markdown":"# Training","workouts":[{"day":"Monday",'
        '"date":"2026-11-16","workout_name":"Endurance","description":"Easy",'
        '"segments":[{"title":"Ride","repeats":1,"steps":[{"duration_m":30,'
        '"power_pct":"65-75"}]}]}]}'
    )
    # WHEN importing it for the preceding Monday.
    # THEN it fails before staging or replacing a saved plan.
    with pytest.raises(ValueError, match="outside the selected week"):
        parse_manual_response(response, messages=_MESSAGES, week_start=date(2026, 11, 9))


def test_manual_response_repairs_mixed_quotes_brackets_and_singleton_steps() -> None:
    """A browser model's formatted response can import without editing training data."""
    # GIVEN the quote styles, Markdown-escaped arrays and lone steps
    # returned by a real external-model response for 9–15 November 2026.
    pasted = (
        '{ “plan_markdown”: “# IntelliWatts Cycling Plan — Base Week 1/4\n'
        '**Week:** 9–15 November 2026\n'
        'He said “easy”, then kept the ride aerobic.”, “workouts”: \['
        '{"day": "Monday", "date": "2026-11-09", "workout_name": "Aerobic Calibration",'
        '"description": "30-minute easy ride", "segments": \['
        '{"title": "Progressive Warm-Up", "repeats": 1, "steps": \['
        '{"duration_m": 8, "power_pct": "Ramp 50-65", "rpm": "85-95"}\]},'
        '{ “title”: “Easy Aerobic Calibration”, “repeats”: 1, “steps”: '
        '{"duration_m": 17, "power_pct": "65-70", "rpm": "85-95"} },'
        '{ “title”: “Cool-Down”, “repeats”: 1, “steps”: '
        '{"duration_m": 5, "power_pct": "Ramp 60-45", "rpm": "80-90"} }\]},'
        '{ “day”: “Tuesday”, “date”: “2026-11-10”, '
        '“workout_name”: “Endurance Base Ride”, “description”: “90-minute Zone 2 ride”, '
        '“segments”: \[{ “title”: “Endurance”, “repeats”: 1, '
        '“steps”: { "duration_m": 90, "power_pct": "65-73" } }\]},'
        '{ “day”: “Thursday”, “date”: “2026-11-12”, '
        '“workout_name”: “FTP Builder”, “description”: “Controlled tempo”, '
        '“segments”: \[{ “title”: “Tempo”, “repeats”: 2, '
        '“steps”: { "duration_m": 12, "power_pct": "85-90" } }\]}'
        '\] }'
    )

    # WHEN the response is imported for the selected week.
    result = parse_manual_response(pasted, messages=_MESSAGES, week_start=date(2026, 11, 9))

    # THEN typography and container syntax are repaired, not training parameters.
    assert "He said “easy”, then kept the ride aerobic." in result.plan
    assert [workout["date"] for workout in result.workouts] == [
        "2026-11-09",
        "2026-11-10",
        "2026-11-12",
    ]
    assert result.workouts[0]["segments"][1]["steps"] == [
        {"duration_m": 17, "power_pct": "65-70", "rpm": "85-95"}
    ]
    assert result.workouts[2]["segments"][0]["repeats"] == 2
    assert result.workouts[2]["segments"][0]["steps"][0]["duration_m"] == 12


def test_manual_response_does_not_coerce_other_invalid_structures() -> None:
    """Only singleton steps may be fixed; other schema errors remain errors."""
    # GIVEN a response with a single workout object instead of the workouts array.
    pasted = '{"plan_markdown":"# Week","workouts":{"day":"Monday"}}'
    # WHEN validating the pasted JSON.
    # THEN the real schema error must still reject the plan.
    with pytest.raises(ValueError, match="workouts"):
        parse_manual_response(pasted, messages=_MESSAGES, week_start=date(2026, 11, 9))


def test_manual_response_keeps_valid_json_and_week_checks() -> None:
    """Valid prose is untouched and repaired formatting cannot bypass date limits."""
    # GIVEN an already valid JSON document containing curly quotes as prose.
    valid = '{"plan_markdown":"The coach said “easy”.","workouts":[]}'
    # WHEN importing it.
    result = parse_manual_response(valid, messages=_MESSAGES, week_start=date(2026, 11, 9))
    # THEN the prose stays exactly the same.
    assert result.plan == "The coach said “easy”."

    # GIVEN formatted JSON with a workout in the next week.
    wrong_week = (
        '{ “plan_markdown”: “# Future ride”, “workouts”: \['
        '{“day”: “Monday”, “date”: “2026-11-16”, “workout_name”: “Endurance”, '
        '“description”: “Easy”, “segments”: \['
        '{“title”: “Ride”, “repeats”: 1, “steps”: '
        '{"duration_m": 30, "power_pct": "65-75"}}'
        '\]}\]}'
    )
    # WHEN parsing it for the selected current week.
    # THEN date validation still rejects it.
    with pytest.raises(ValueError, match="outside the selected week"):
        parse_manual_response(wrong_week, messages=_MESSAGES, week_start=date(2026, 11, 9))
