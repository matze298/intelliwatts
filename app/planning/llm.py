"""Generates the training plan based on the summary by using an LLM."""

from functools import lru_cache
from typing import Any, NamedTuple

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)
from openai import OpenAI

from app.config import LanguageModel
from app.models.user import User, load_user_secrets
from app.planning.coach_prompt import SYSTEM_PROMPT, user_prompt


class LLMResponse(NamedTuple):
    """Response from the LLM."""

    plan: str
    prompt: list[dict[str, str]]


def generate_plan(summary: dict[str, Any], language_model: LanguageModel, user: User) -> LLMResponse:
    """Generates the training plan based on the summary by using ChatGPT.

    Args:
        summary: The athlete summary of the intervals.icu activities.
        language_model: The language model to use.
        user: The current user.

    Returns:
        The training plan.
    """
    secrets = load_user_secrets(user.id)
    if "gpt" in language_model:
        return call_gpt(user_prompt(summary), api_key=secrets.openai_api_key, model=language_model)

    if "gemini" in language_model:
        return call_gemini(user_prompt(summary), api_key=secrets.gemini_api_key, model=language_model)

    msg = "Unknown model: " + language_model
    raise NotImplementedError(msg)


@lru_cache
def call_gpt(prompt: str, api_key: str | None, model: LanguageModel) -> LLMResponse:
    """Sends a prompt to the GPT model.

    Returns:
        The text response and the prompt.

    Raises:
        RuntimeError: if the API key is not set
    """
    if not api_key:
        msg = "OPENAI_API_KEY must be set if using GPT!"
        raise RuntimeError(msg)

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[invalid-argument-type]
        temperature=0.2,
    )
    return LLMResponse(plan=response.choices[0].message.content, prompt=messages)


@lru_cache
def call_gemini(
    prompt: str,
    api_key: str | None,
    model: LanguageModel,
    temperature: float = 0.4,
    max_output_tokens: int = 6144,
) -> LLMResponse:
    """Sends a prompt to the Gemini model.

    Returns:
        The text response and the prompt.

    Raises:
        RuntimeError: if the API key is not set
    """
    if not api_key:
        msg = "GEMINI_API_KEY must be set if using Gemini!"
        raise RuntimeError(msg)

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            # Adding safety settings can sometimes prevent over-active filtering
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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return LLMResponse(plan=response.text, prompt=messages)
