"""Generates the training plan based on the summary by using an LLM."""

from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    HttpOptions,
    HttpRetryOptions,
    SafetySetting,
)
from openai import OpenAI

from app.config import LanguageModel, get_settings
from app.planning.coach_prompt import SYSTEM_PROMPT
from app.planning.schemas import WeeklyPlanOutput

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

MODEL_REQUEST_TIMEOUT_SECONDS = 120
GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"


class LLMRole(StrEnum):
    """LLM roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    MODEL = "model"


@dataclass(frozen=True)
class LLMMessage:
    """Hashable representation of a chat message."""

    role: LLMRole
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Response from the LLM."""

    plan: str
    prompt: list[dict[str, str]]
    workouts: list[dict[str, object]] = field(default_factory=list)


def generate_plan(
    language_model: LanguageModel,
    messages: list[dict[str, str]],
) -> LLMResponse:
    """Generates the training plan based on the message history.

    Args:
        language_model: The language model to use.
        messages: Full conversation history.

    Returns:
        The training plan.
    """
    secrets = get_settings()
    if language_model == LanguageModel.GROQ_GPT_OSS_120B:
        return call_gpt(
            messages,
            api_key=secrets.GROQ_API_KEY,
            model=language_model,
            base_url=GROQ_API_BASE_URL,
        )

    if "gpt" in language_model:
        return call_gpt(messages, api_key=secrets.OPENAI_API_KEY, model=language_model)

    if "gemini" in language_model:
        return call_gemini(messages, api_key=secrets.GEMINI_API_KEY, model=language_model)

    msg = "Unknown model: " + language_model
    raise NotImplementedError(msg)


def call_gpt(
    messages: list[dict[str, str]],
    api_key: str | None,
    model: LanguageModel,
    base_url: str | None = None,
) -> LLMResponse:
    """Sends a prompt to an OpenAI-compatible chat completions model.

    Returns:
        The text response and the prompt.
    """
    messages_tuple = tuple(LLMMessage(LLMRole(m["role"]), m["content"]) for m in messages)
    return _call_gpt_cached(messages_tuple, api_key, model, base_url)


@lru_cache
def _call_gpt_cached(
    messages_tuple: tuple[LLMMessage, ...],
    api_key: str | None,
    model: LanguageModel,
    base_url: str | None = None,
) -> LLMResponse:
    """Sends a prompt to an OpenAI-compatible model (cached version).

    Returns:
        The text response and the prompt.

    Raises:
        RuntimeError: If the provider API key is not set.
    """
    if not api_key:
        key_name, provider = ("GROQ_API_KEY", "Groq") if base_url == GROQ_API_BASE_URL else ("OPENAI_API_KEY", "OpenAI")
        msg = f"{key_name} must be set if using {provider}!"
        raise RuntimeError(msg)

    messages = [{"role": m.role, "content": m.content} for m in messages_tuple]
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=MODEL_REQUEST_TIMEOUT_SECONDS, max_retries=0)
    if base_url == GROQ_API_BASE_URL:
        request_messages = [message.copy() for message in messages]
        request_messages[0]["content"] += (
            "\n\nReturn one JSON object with keys `plan_markdown` and `workouts`. Each workout has "
            "`day`, `workout_name`, `description`, and `segments`; each segment has `title`, `repeats`, "
            "and `steps`; each step has `duration_m`, `power_pct`, and optional `rpm`. Do not include "
            "markdown fences or text outside the JSON object."
        )
        chunks = client.chat.completions.create(
            model=model,
            messages=cast("list[ChatCompletionMessageParam]", request_messages),
            temperature=0.2,
            response_format={"type": "json_object"},
            stream=True,
        )
        response_text = "".join(chunk.choices[0].delta.content or "" for chunk in chunks if chunk.choices)
        output = WeeklyPlanOutput.model_validate_json(response_text)
    else:
        with client.chat.completions.stream(
            model=model,
            messages=cast("list[ChatCompletionMessageParam]", messages),
            temperature=0.2,
            response_format=WeeklyPlanOutput,
        ) as stream:
            response = stream.get_final_completion()
        output = response.choices[0].message.parsed
    if output is None:
        msg = "Model returned no structured plan output"
        raise RuntimeError(msg)

    return LLMResponse(
        plan=output.plan_markdown,
        prompt=messages,
        workouts=[workout.model_dump(mode="json", exclude_none=True) for workout in output.workouts],
    )


def call_gemini(
    messages: list[dict[str, str]],
    api_key: str | None,
    model: LanguageModel,
    temperature: float = 0.4,
    max_output_tokens: int = 6144,
) -> LLMResponse:
    """Sends a prompt to the Gemini model.

    Returns:
        The text response and the prompt.
    """
    messages_tuple = tuple(LLMMessage(LLMRole(m["role"]), m["content"]) for m in messages)
    return _call_gemini_cached(messages_tuple, api_key, model, temperature, max_output_tokens)


@lru_cache
def _call_gemini_cached(
    messages_tuple: tuple[LLMMessage, ...],
    api_key: str | None,
    model: LanguageModel,
    temperature: float = 0.4,
    max_output_tokens: int = 6144,
) -> LLMResponse:
    """Sends a prompt to the Gemini model (cached version).

    Returns:
        The text response and the prompt.

    Raises:
        RuntimeError: if the API key is not set
    """
    if not api_key:
        msg = "GEMINI_API_KEY must be set if using Gemini!"
        raise RuntimeError(msg)

    messages = [{"role": m.role, "content": m.content} for m in messages_tuple]
    client = genai.Client(
        api_key=api_key,
        http_options=HttpOptions(
            timeout=MODEL_REQUEST_TIMEOUT_SECONDS * 1000,
            retry_options=HttpRetryOptions(attempts=2),
        ),
    )

    # For Gemini API, we can either use contents=[...] or use the chat session.
    # To keep it consistent with our message list format:
    gemini_contents = []
    system_instruction = SYSTEM_PROMPT
    for msg in messages_tuple:
        if msg.role == LLMRole.SYSTEM:
            system_instruction = msg.content
            continue
        role = "user" if msg.role == LLMRole.USER else "model"
        gemini_contents.append({"role": role, "parts": [{"text": msg.content}]})

    response_text = "".join(
        chunk.text or ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=gemini_contents,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                response_schema=WeeklyPlanOutput,
                safety_settings=[
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            ),
        )
    )

    if not response_text:
        msg = "Gemini returned no structured plan output"
        raise RuntimeError(msg)

    output = WeeklyPlanOutput.model_validate_json(response_text)
    return LLMResponse(
        plan=output.plan_markdown,
        prompt=messages,
        workouts=[workout.model_dump(mode="json", exclude_none=True) for workout in output.workouts],
    )
