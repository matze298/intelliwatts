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


@pytest.mark.parametrize("response", ["not JSON", "{}", '{"plan_markdown":"","workouts":[]}', ""])
def test_manual_response_rejects_invalid_content(response: str) -> None:
    """Invalid output must not be accepted for persistence."""
    # GIVEN a response without the required valid structured content.
    # WHEN parsing it.
    # THEN validation returns an actionable failure.
    with pytest.raises(ValueError):
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
