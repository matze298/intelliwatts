"""Planner preference normalization tests."""

import pytest

from app.config import LanguageModel
from app.services.planner.preferences import normalize_available_days, preferred_model


def test_available_days_are_saved_in_calendar_order() -> None:
    """The submitted selection is canonicalized without inflating cycling sessions."""
    assert normalize_available_days(["Sunday", "Tuesday", "Tuesday", "Thursday"]) == [
        "Tuesday",
        "Thursday",
        "Sunday",
    ]


@pytest.mark.parametrize("days", [[], ["Restday"], ["Monday", "other"]])
def test_reject_invalid_availability(days: list[str]) -> None:
    """No selection or unknown days are not accepted."""
    with pytest.raises(ValueError, match="Select at least one"):
        normalize_available_days(days)


def test_resolve_previous_model_or_fallback() -> None:
    """A valid model persists while removed models fall back safely."""
    assert (
        preferred_model(LanguageModel.GROQ_GPT_OSS_120B.value, LanguageModel.GEMINI_FLASH)
        == LanguageModel.GROQ_GPT_OSS_120B
    )
    assert preferred_model("removed-model", LanguageModel.GEMINI_FLASH) == LanguageModel.GEMINI_FLASH
