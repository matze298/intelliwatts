"""Converts the plan JSON to text format usable by intervals.icu."""

import json
import logging

_LOGGER = logging.getLogger(__name__)


def llm_json_to_icu_txt(ai_response: str) -> str:
    """Parses the AI JSON response and generates .txt workout files for intervals.icu.

    Args:
        ai_response: The AI response containing the plan and JSON.

    Returns:
        The workout structured as intervals.icu .txt file.
    """
    # 1. Split the response
    parts = ai_response.split("###JSON_START###")
    json_part = parts[1].strip() if len(parts) > 1 else "[]"

    # 2. Parse JSON
    try:
        workouts = json.loads(json_part)
    except json.JSONDecodeError as e:
        _LOGGER.exception("Failed to parse JSON from AI response.", exc_info=e)
        return "Failed to parse workout JSON."

    # 3. Generate .txt files from JSON
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
