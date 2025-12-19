"""The coach prompt sent to the LLM."""

from typing import Any

SYSTEM_PROMPT = """
You are an evidence-based cycling coach.

Rules:
- Respect training load and constraints
- Reduce intensity if TSB < -10
- Prefer pyramidal or polarized distribution
- Use FTP/CP targets conservatively
- Return a structured weekly plan
"""


def user_prompt(summary: dict[str, Any]) -> str:
    """Generates the prompt for the LLM.

    Returns:
        The prompt.
    """
    return f"""
Athlete weekly summary (JSON):

{summary}

Generate a 7-day cycling training plan.
Include:
- session goal
- duration
- power targets (%FTP)
- rationale
- nutrition tips
"""
