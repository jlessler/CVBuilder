"""PDF generation service using WeasyPrint + Jinja2."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "cv_templates"


def _combine(base: dict, *others: dict) -> dict:
    """Ansible-style dict combine filter for Jinja2."""
    result = dict(base or {})
    for other in others:
        result.update(other or {})
    return result


def _bold_self(author_name: str, profile_name: str) -> str:
    """Wrap author_name in <strong> if it matches the CV holder's name.

    Matches on last name (whole word) + first initial, and also checks the
    middle initial when the profile has one and the author string provides
    two or more initials — avoiding false positives with common last names.

    Handles typical academic citation formats:
      "Lessler J", "Lessler JK", "J Lessler", "JK Lessler", "Justin Lessler"
    """
    if not profile_name or not author_name:
        return author_name

    parts = profile_name.strip().split()
    if not parts:
        return author_name

    last = parts[-1]
    first_init = parts[0][0].upper()
    mid_init = parts[1][0].upper() if len(parts) >= 3 else ""

    # Last name must appear as a whole word (case-insensitive).
    if not re.search(r"(?i)\b" + re.escape(last) + r"\b", author_name):
        return author_name

    # Strip punctuation, split into words, locate last name.
    clean_words = [w for w in re.sub(r"[,.]", " ", author_name).split() if w]
    last_idx = next(
        (i for i, w in enumerate(clean_words) if w.lower() == last.lower()), None
    )
    if last_idx is None:
        return author_name

    other_words = [w for i, w in enumerate(clean_words) if i != last_idx]
    if not other_words:
        return author_name

    def _to_initials(w: str) -> str:
        # "JK" or "J" (all-caps, 1-3 chars) → keep as-is; "Justin" → "J"
        return w if (re.match(r"^[A-Z]{1,3}$", w)) else w[0].upper()

    initials = "".join(_to_initials(w) for w in other_words).upper()

    # First initial must match.
    if not initials or initials[0] != first_init:
        return author_name

    # Middle initial: only reject if the author name provides a second initial
    # that contradicts the profile's middle initial.
    if mid_init and len(initials) >= 2 and initials[1] != mid_init:
        return author_name

    return f"<strong>{author_name}</strong>"


def _get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    env.filters["combine"] = _combine
    env.filters["bold_self"] = _bold_self
    return env


def render_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 template to HTML string."""
    env = _get_jinja_env()
    tmpl = env.get_template(template_name)
    return tmpl.render(**context)


def render_cv_html(cv_data: dict, theme: str = "academic", sections: list[dict] | None = None) -> str:
    """Render the full CV as HTML."""
    if sections is None:
        sections = []

    # Inline the CSS so the HTML is self-contained (works in browser preview and WeasyPrint).
    theme_css_file = TEMPLATES_DIR / "themes" / f"{theme}.css"
    if theme_css_file.exists():
        theme_css_content = theme_css_file.read_text(encoding="utf-8")
    else:
        theme_css_content = ""

    context = {
        "cv": cv_data,
        "theme": theme,
        "sections": sections,
        "theme_css_content": theme_css_content,
    }
    return render_html("base.html", context)


def html_to_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        raise RuntimeError("weasyprint is not installed. Run: pip install weasyprint")

    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
