"""Tests for safely rendering untrusted content in web templates."""

from fastapi import FastAPI
from starlette.requests import Request

from app.config import LanguageModel, get_settings
from app.models.user import User
from app.routes import web
from app.utils.markdown import render_markdown


def test_plan_prompt_is_rendered_as_escaped_text() -> None:
    """Prompt history should be readable without interpreting its content as HTML."""
    # GIVEN a planner page with untrusted HTML in saved prompt content
    app = FastAPI()
    app.state.settings = {"settings": get_settings(), "models": LanguageModel}
    request = Request({"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [], "app": app})

    # WHEN rendering the plan page
    response = web._render_plan_page(
        request,
        user=User(),
        plan_html=render_markdown("# Generated plan"),
        long_term_summary_html=None,
        delivery_status=None,
        delivery_last_error=None,
        summary=None,
        prompt=[{"role": "user", "content": 'Coach text <script>alert("prompt")</script>'}],
    )

    # THEN the prompt remains visible as escaped text, not an executable script
    assert b"<h1>Generated plan</h1>" in response.body
    assert b"Coach text" in response.body
    assert b"&lt;script&gt;" in response.body
    assert b"<script>" not in response.body
