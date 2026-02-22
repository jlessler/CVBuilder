"""PDF generation service using WeasyPrint + Jinja2."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "cv_templates"


def _combine(base: dict, *others: dict) -> dict:
    """Ansible-style dict combine filter for Jinja2."""
    result = dict(base or {})
    for other in others:
        result.update(other or {})
    return result


def _get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    env.filters["combine"] = _combine
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
    context = {
        "cv": cv_data,
        "theme": theme,
        "sections": sections,
        "theme_url": f"themes/{theme}.css",
    }
    return render_html("base.html", context)


def html_to_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        raise RuntimeError("weasyprint is not installed. Run: pip install weasyprint")

    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
