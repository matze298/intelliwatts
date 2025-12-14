"""Generates the training plan based on the summary by using an LLM."""

from typing import Any

from openai import OpenAI

from app.config import settings
from planning.coach_prompt import SYSTEM_PROMPT, user_prompt

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_plan(summary: dict[str, Any]) -> dict[str, Any]:
    """Generates the training plan based on the summary by using ChatGPT.

    Returns:
        The training plan.
    """
    response = client.chat.completions.create(
        model="gpt-5-thinking-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(summary)},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
