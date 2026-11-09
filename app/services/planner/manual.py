"""Manual external-LLM prompt formatting and response validation."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError

from app.models.plan import TrainingPlan
from app.planning.llm import LLMResponse
from app.planning.schemas import WeeklyPlanOutput
from app.services.workout_delivery import build_workout_delivery_payloads

if TYPE_CHECKING:
    from datetime import date

MAX_MANUAL_RESPONSE_LENGTH = 250_000
_JSON_FENCE = re.compile(r"\A```(?:json)?\s*\n(.*?)\n```\s*\Z", re.IGNORECASE | re.DOTALL)


def format_manual_prompt(messages: list[dict[str, str]]) -> str:
    """Format the full model messages and required output contract for browser use.

    Returns:
        A single prompt that can be pasted into any browser-based LLM.
    """
    sections = [
        (
            "Generate a training plan for IntelliWatts. Follow ALL instructions and context below. "
            "Return only a single JSON object matching the schema at the end; no explanation or markdown code fences."
        )
    ]
    for message in messages:
        heading = "SYSTEM INSTRUCTIONS" if message["role"] == "system" else "USER MESSAGE"
        sections.append(f"### {heading}\n{message['content']}")
    sections.append(
        "### REQUIRED JSON RESPONSE SCHEMA\n"
        + json.dumps(WeeklyPlanOutput.model_json_schema(), indent=2, ensure_ascii=False)
        + "\nReturn a JSON object with plan_markdown and workouts. Use [] when no workouts are prescribed."
    )
    return "\n\n".join(sections)


def parse_manual_response(response_text: str, *, messages: list[dict[str, str]], week_start: date) -> LLMResponse:
    """Validate pasted JSON with the same schema used by automatic generation.

    Returns:
        A parsed model response ready for the existing persistence and staging flow.

    Raises:
        ValueError: If the response or workout dates cannot be used.
    """
    text = response_text.strip()
    if not text:
        msg = "Paste the model's complete JSON response."
        raise ValueError(msg)
    if len(text) > MAX_MANUAL_RESPONSE_LENGTH:
        msg = "The pasted model response is too large."
        raise ValueError(msg)
    if text.startswith("```"):
        match = _JSON_FENCE.fullmatch(text)
        if match is None:
            msg = "Paste only a JSON object, optionally inside one JSON code fence."
            raise ValueError(msg)
        text = match.group(1)

    try:
        output = WeeklyPlanOutput.model_validate_json(text)
    except ValidationError as exc:
        msg = "The response must contain valid JSON with plan_markdown and structured workouts. " + str(exc)[:900]
        raise ValueError(msg) from exc
    if not output.plan_markdown.strip():
        msg = "The response's plan_markdown must not be empty."
        raise ValueError(msg)

    workouts = [workout.model_dump(mode="json", exclude_none=True) for workout in output.workouts]
    # The automatic staging path records invalid workout dates as failed deliveries.
    # Reject them here before replacing an existing manual or API-generated plan.
    preview = TrainingPlan(
        phase_id=uuid4(),
        week_start=week_start,
        raw_content=output.plan_markdown,
        workout_data=workouts,
    )
    build_workout_delivery_payloads(preview)

    return LLMResponse(plan=output.plan_markdown, prompt=messages, workouts=workouts)
