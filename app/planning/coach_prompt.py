"""The coach prompt sent to the LLM."""

from typing import Any

SYSTEM_PROMPT = """
You are an evidence-based cycling coach.

Rules:
- Respect training load and constraints
- Reduce intensity if TSB < -30 (high risk zone)
- Ideal TSB is between -30 and -10 (optimal zone)
- Prefer pyramidal or polarized distribution
- Use FTP/CP targets conservatively
- Return a structured weekly plan
"""

USER_PROMPT = """
Generate a 7-day cycling training plan.
Include:
- session goal
- duration
- power targets (%FTP)
- rationale
- nutrition tips
"""


def user_prompt(summary: dict[str, Any]) -> str:
    """Generates the prompt for the LLM.

    Returns:
        The prompt.
    """
    return f"""
Athlete weekly summary (JSON):

{summary}

{USER_PROMPT}
"""
