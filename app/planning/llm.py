"""Generates the training plan based on the summary by using an LLM."""

from typing import Any

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)
from openai import OpenAI
from functools import lru_cache

from app.models.user import User, load_user_secrets
from app.config import LanguageModel
from app.planning.coach_prompt import SYSTEM_PROMPT, user_prompt


def generate_plan(summary: dict[str, Any], language_model: LanguageModel, user: User) -> str:
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
def call_gpt(prompt: str, api_key: str | None, model: LanguageModel) -> str:
    """Sends a prompt to the GPT model.

    Returns:
        The text response.

    Raises:
        RuntimeError: if the API key is not set
    """
    if not api_key:
        msg = "OPENAI_API_KEY must be set if using GPT!"
        raise RuntimeError(msg)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


@lru_cache
def call_gemini(
    prompt: str,
    api_key: str | None,
    model: LanguageModel,
    temperature: float = 0.4,
    max_output_tokens: int = 4096,
) -> str:
    """Sends a prompt to the Gemini model.

    Returns:
        The text response.

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

    return response.text
