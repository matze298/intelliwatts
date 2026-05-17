"""Converts the plan JSON to text format usable by intervals.icu."""

import json
import logging

_LOGGER = logging.getLogger(__name__)


def extract_workout_json(ai_response: str) -> list[dict]:
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
    return json.loads(json_part)


def workout_json_to_icu_txt(workout: dict) -> str:
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


def llm_json_to_icu_txt(ai_response: str) -> str:
    """Parses the AI JSON response and generates .txt workout files for intervals.icu.

    Args:
        ai_response: The AI response containing the plan and JSON.

    Returns:
        The workout structured as intervals.icu .txt file.
    """
    # 1. Extract JSON
    try:
        workouts = extract_workout_json(ai_response)
    except json.JSONDecodeError:
        _LOGGER.warning("Failed to parse JSON from AI response.", exc_info=True)
        return "Failed to parse workout JSON."

    # 2. Generate .txt files from JSON
    return "\n".join(workout_json_to_icu_txt(workout) for workout in workouts)
