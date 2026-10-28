"""Tests for language model configuration."""

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from app.config import LanguageModel
from app.planning import llm

if TYPE_CHECKING:
    import pytest


def test_model_uses_configured_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model calls use the installation's configured key without a user secret row."""
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(OPENAI_API_KEY="configured-key"))
    call_gpt = MagicMock(return_value=llm.LLMResponse(plan="plan", prompt=[]))
    monkeypatch.setattr(llm, "call_gpt", call_gpt)
    result = llm.generate_plan(LanguageModel.GPT_5_MINI, [{"role": "user", "content": "plan"}])
    assert result.plan == "plan"
    assert call_gpt.call_args.kwargs["api_key"] == "configured-key"
