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
    except json.JSONDecodeError as e:
        _LOGGER.exception("Failed to parse JSON from AI response.", exc_info=e)
        return "Failed to parse workout JSON."

    # 2. Generate .txt files from JSON
    file_content = ""
    for workout in workouts:
        file_content += f"Title: {workout['workout_name']}\n\nDescription: {workout['description']}\n\n"

        for segment in workout["segments"]:
            # Format: <section_title> <num_intervals>x
            header = f"{segment['title']}"
            if segment["repeats"] > 1:
                header += f" {segment['repeats']}x"
            file_content += f"{header}\n"

            # Format: - <time>m <power>% <rpm>rpm
            for step in segment["steps"]:
                line = f"- {step['duration_m']}m {step['power_pct']}%"
                if step.get("rpm"):
                    line += f" {step['rpm']}rpm"
                file_content += f"{line}\n"
            file_content += "\n"
        file_content += "\n\n"

    return file_content
