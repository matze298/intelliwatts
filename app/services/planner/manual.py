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
            "Create or revise a training plan for IntelliWatts. Follow ALL instructions and context below. "
            "Your deliverable is a UTF-8 JSON document named intelliwatts-plan.json. "
            "If your chat supports file attachments, create that downloadable .json file containing ONLY one JSON object. "
            "Otherwise, output ONLY the raw JSON object (an optional json code fence is fine), with no commentary."
        ),
        (
            "STRICT JSON RULES: Use straight ASCII double quotes for every key and string delimiter, never curly quotes. "
            "Represent newlines inside strings as escaped \\n, not literal line breaks. "
            "Do not Markdown-escape array brackets: write [ and ], NEVER \\[ or \\]. "
            "The workouts, segments, and steps fields must ALWAYS be JSON arrays, even for a single item. "
            'For example, a single interval is "steps": [{"duration_m": 20, "power_pct": "65-70"}]. '
            "Before returning the result, check it parses as JSON and matches the schema below."
        ),
    ]
    for message in messages:
        heading = {"system": "SYSTEM INSTRUCTIONS", "user": "USER MESSAGE", "assistant": "ASSISTANT RESPONSE"}.get(
            message["role"], "PRIOR MESSAGE"
        )
        sections.append(f"### {heading}\n{message['content']}")
    sections.append(
        "### REQUIRED JSON RESPONSE SCHEMA\n"
        + json.dumps(WeeklyPlanOutput.model_json_schema(), indent=2, ensure_ascii=False)
        + "\nReturn a JSON object with plan_markdown and workouts. Use [] when no workouts are prescribed."
    )
    return "\n\n".join(sections)


_JSON_QUOTED_STRING = re.compile(r'"(?:\\.|[^"\\])*"', re.DOTALL)
_SMART_STRING_ESCAPES = {"\n": r"\n", "\r": r"\r", "\t": r"\t", '"': r"\""}


def _smart_quote_closes(text: str, index: int) -> bool:
    """Distinguish a closing JSON delimiter from punctuation inside prose.

    Returns:
        Whether this smart right quote can close a JSON string.
    """
    following = text[index + 1 :].lstrip()
    if not following or following[0] in ":}]":
        return True
    if not following.startswith(","):
        return False
    after_comma = following[1:].lstrip()
    return not after_comma or after_comma[0] in '"“{['


def _append_smart_quoted_text(text: str, start: int, result: list[str]) -> int:
    """Convert a curly-quoted string into a JSON-quoted string in the output.

    Returns:
        The index of the next character after that string.
    """
    result.append('"')
    index = start + 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            result.append(char)
            escaped = False
        elif char == "\\":
            result.append(char)
            escaped = True
        elif char == "”" and _smart_quote_closes(text, index):
            result.append('"')
            return index + 1
        else:
            result.append(_SMART_STRING_ESCAPES.get(char, char))
        index += 1
    return index


def _normalize_json_punctuation(text: str) -> str:
    """Repair smart JSON delimiters and escaped brackets outside JSON strings.

    Returns:
        JSON text with common copy/paste artifacts normalized.
    """
    result: list[str] = []
    index = 0
    while index < len(text):
        quoted = _JSON_QUOTED_STRING.match(text, index)
        if quoted is not None:
            # Never modify the contents of already-valid JSON strings.
            result.append(quoted.group())
            index = quoted.end()
        elif text[index] == "“":
            index = _append_smart_quoted_text(text, index, result)
        elif text[index : index + 2] in {r"\[", r"\]"}:
            result.append(text[index + 1])
            index += 2
        else:
            result.append(text[index])
            index += 1
    return "".join(result)


def _wrap_single_steps(data: object) -> object:
    """Repair only one-step objects in structured workouts.

    Returns:
        The parsed object with single-step dictionaries wrapped in arrays.
    """
    if not isinstance(data, dict) or not isinstance(data.get("workouts"), list):
        return data
    for workout in data["workouts"]:
        if not isinstance(workout, dict) or not isinstance(workout.get("segments"), list):
            continue
        for segment in workout["segments"]:
            if isinstance(segment, dict) and isinstance(segment.get("steps"), dict):
                segment["steps"] = [segment["steps"]]
    return data


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
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(_normalize_json_punctuation(text))
        except json.JSONDecodeError as exc:
            msg = (
                "The response must contain valid JSON with plan_markdown and structured workouts. "
                f"Syntax error at line {exc.lineno}, column {exc.colno}: {exc.msg}."
            )
            raise ValueError(msg) from exc

    try:
        output = WeeklyPlanOutput.model_validate(_wrap_single_steps(data))
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
