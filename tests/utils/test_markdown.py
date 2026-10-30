"""Tests for rendering untrusted Markdown as safe HTML."""

from markupsafe import Markup

from app.utils.markdown import render_markdown


def test_render_markdown_sanitizes_active_content_and_preserves_markdown() -> None:
    """Render useful Markdown while removing active HTML and unsafe attributes."""
    # GIVEN Markdown containing normal formatting and malicious raw HTML
    source = """# Weekly plan

<script>alert('script')</script>
<img src=x onerror="alert('image')">
<a href="javascript:alert('link')" onclick="alert('click')">unsafe link</a>
<a href="https://example.com">safe link</a>
<a href="//evil.example">protocol-relative link</a>
<a href="data:text/html,<script>alert('data')</script>">data link</a>
<svg onload="alert('svg')"><script>alert('svg script')</script></svg>
<iframe src="https://example.com">embedded content</iframe>
<p><strong onclick="alert('nested')">malformed nesting</p>

| Day | Session |
| --- | --- |
| Tue | Intervals |

```text
recover well
```
"""

    # WHEN rendering Markdown for a page
    rendered = render_markdown(source)

    # THEN allowed Markdown formatting remains trusted markup
    assert isinstance(rendered, Markup)
    assert "<h1>Weekly plan</h1>" in rendered
    assert "<table>" in rendered
    assert "<pre><code>recover well" in rendered
    assert '<a href="https://example.com"' in rendered

    # AND active content, unsafe attributes, and unsafe links are removed
    for unsafe_fragment in (
        "<script",
        "alert(",
        "onerror",
        "onclick",
        "javascript:",
        "//evil.example",
        "data:text/html",
        "<img",
        "<svg",
        "<iframe",
    ):
        assert unsafe_fragment not in rendered
