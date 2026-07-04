"""Converts weekly plan JSON into structured Intervals.icu workout payloads."""

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_valid_workout_step(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    if not _is_number(step.get("duration_m")) or not _is_number(step.get("power_pct")):
        return False
    return step.get("rpm") is None or _is_number(step.get("rpm"))


def _is_valid_workout_segment(segment: object) -> bool:
    if not isinstance(segment, dict):
        return False
    steps = segment.get("steps")
    repeats = segment.get("repeats")
    return (
        _is_non_empty_string(segment.get("title"))
        and isinstance(repeats, int)
        and not isinstance(repeats, bool)
        and repeats >= 1
        and isinstance(steps, list)
        and all(_is_valid_workout_step(step) for step in steps)
    )


def _is_valid_workout(workout: object) -> bool:
    if not isinstance(workout, dict):
        return False
    segments = workout.get("segments")
    return (
        _is_non_empty_string(workout.get("workout_name"))
        and isinstance(workout.get("description"), str)
        and isinstance(segments, list)
        and all(_is_valid_workout_segment(segment) for segment in segments)
    )


def extract_workout_json(ai_response: str) -> list[dict[str, Any]]:
    """Parses the AI response and extracts the workout JSON part.

    Args:
        ai_response: The AI response containing the plan and JSON.

    Returns:
        The parsed workout JSON as a list of dictionaries.
    """
    parts = ai_response.split("###JSON_START###")
    if len(parts) <= 1:
        return []

    json_part = parts[1].split("###JSON_END###")[0].strip()
    try:
        payload = json.loads(json_part)
    except json.JSONDecodeError:
        _LOGGER.warning("Ignoring malformed workout JSON payload", exc_info=True)
        return []

    if not isinstance(payload, list) or not all(_is_valid_workout(workout) for workout in payload):
        payload_type = type(payload).__name__
        _LOGGER.warning("Ignoring malformed workout JSON payload: payload_type=%s", payload_type)
        return []

    return payload


def workout_json_to_icu_txt(workout: dict[str, Any]) -> str:
    """Render a single workout object as Intervals.icu workout text.

    Example:
        Title: Tuesday Intervals

        Description: Quality work

        Main Set
        - 10m 85-95%
        - 5m 65-75%

    Returns:
        The workout in intervals.icu text format.
    """
    file_content = f"Title: {workout['workout_name']}\n\nDescription: {workout['description']}\n\n"

    for segment in workout["segments"]:
        header = f"{segment['title']}"
        if segment["repeats"] > 1:
            header += f" {segment['repeats']}x"
        file_content += f"{header}\n"

        for step in segment["steps"]:
            line = f"- {step['duration_m']}m {step['power_pct']}%"
            if step.get("rpm"):
                line += f" {step['rpm']}rpm"
            file_content += f"{line}\n"
        file_content += "\n"

    file_content += "\n\n"
    return file_content
