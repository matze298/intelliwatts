"""Generates the training plan based on the summary by using an LLM."""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)
from openai import OpenAI

from app.models.user import load_user_secrets
from app.planning.coach_prompt import SYSTEM_PROMPT, user_prompt

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

    from app.config import LanguageModel
    from app.models.user import User


@dataclass(frozen=True)
class LLMMessage:
    """Hashable representation of a chat message."""

    role: str
    content: str


class LLMResponse(NamedTuple):
    """Response from the LLM."""

    plan: str
    prompt: list[dict[str, str]]


def generate_plan(
    language_model: LanguageModel,
    user: User,
    *,
    summary: dict[str, Any] | None = None,
    messages: list[dict[str, str]] | None = None,
) -> LLMResponse:
    """Generates the training plan based on the summary or message history.

    Args:
        language_model: The language model to use.
        user: The current user.
        summary: Optional athlete summary for initial plan generation.
        messages: Optional full conversation history for iterative updates.

    Returns:
        The training plan.

    Raises:
        ValueError: If neither summary nor messages are provided.
    """
    if summary is not None:
        prompt = user_prompt(summary)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    elif messages is None:
        msg = "Either summary or messages must be provided"
        raise ValueError(msg)

    secrets = load_user_secrets(user.id)
    if "gpt" in language_model:
        return call_gpt(messages, api_key=secrets.openai_api_key, model=language_model)

    if "gemini" in language_model:
        return call_gemini(messages, api_key=secrets.gemini_api_key, model=language_model)

    msg = "Unknown model: " + language_model
    raise NotImplementedError(msg)


def call_gpt(messages: list[dict[str, str]], api_key: str | None, model: LanguageModel) -> LLMResponse:
    """Sends a prompt to the GPT model.

    Returns:
        The text response and the prompt.
    """
    messages_tuple = tuple(LLMMessage(m["role"], m["content"]) for m in messages)
    return _call_gpt_cached(messages_tuple, api_key, model)


@lru_cache
def _call_gpt_cached(messages_tuple: tuple[LLMMessage, ...], api_key: str | None, model: LanguageModel) -> LLMResponse:
    """Sends a prompt to the GPT model (cached version).

    Returns:
        The text response and the prompt.

    Raises:
        RuntimeError: if the API key is not set
    """
    if not api_key:
        msg = "OPENAI_API_KEY must be set if using GPT!"
        raise RuntimeError(msg)

    messages = [{"role": m.role, "content": m.content} for m in messages_tuple]
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=cast("list[ChatCompletionMessageParam]", messages),
        temperature=0.2,
    )
    if not response.choices[0].message.content:
        msg = "GPT returned no text output"
        raise RuntimeError(msg)

    return LLMResponse(plan=response.choices[0].message.content, prompt=messages)


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
    messages_tuple = tuple(LLMMessage(m["role"], m["content"]) for m in messages)
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
    client = genai.Client(api_key=api_key)

    # For Gemini API, we can either use contents=[...] or use the chat session.
    # To keep it consistent with our message list format:
    gemini_contents = []
    for msg in messages:
        if msg["role"] == "system":
            # Gemini system instruction is handled in config
            continue
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    response = client.models.generate_content(
        model=model,
        contents=gemini_contents,
        config=GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
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

    if not response.text:
        msg = "Gemini returned no text output"
        raise RuntimeError(msg)

    return LLMResponse(plan=response.text, prompt=messages)
