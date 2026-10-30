"""Render Markdown as a sanitized HTML fragment."""

import markdown
import nh3
from markupsafe import Markup

_MARKDOWN_EXTENSIONS = ["tables", "fenced_code"]
_SANITIZER = nh3.Cleaner(
    tags={
        "a",
        "blockquote",
        "br",
        "code",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    },
    clean_content_tags={"embed", "iframe", "object", "script", "style"},
    attributes={"a": {"href", "title"}},
    url_schemes={"http", "https", "mailto"},
    url_relative="deny",
)


def _sanitize_html(html: str) -> str:
    """Remove markup and attributes outside the Markdown allowlist.

    Args:
        html: HTML produced by Python-Markdown.

    Returns:
        The sanitized HTML fragment.
    """
    return _SANITIZER.clean(html)


def render_markdown(source: str) -> Markup:
    """Convert Markdown to a sanitized fragment safe for HTML templates.

    Args:
        source: Untrusted Markdown text.

    Returns:
        Sanitized HTML markup preserving the supported Markdown formatting.
    """
    rendered_html = markdown.markdown(source, extensions=_MARKDOWN_EXTENSIONS)
    return Markup(_sanitize_html(rendered_html))
