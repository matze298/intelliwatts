"""Converts structured weekly workouts into Intervals.icu workout text."""

from typing import Any


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
