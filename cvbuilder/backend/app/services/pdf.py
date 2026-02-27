"""PDF generation service using WeasyPrint + Jinja2."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "cv_templates"


# ---------------------------------------------------------------------------
# Default style properties (academic defaults)
# ---------------------------------------------------------------------------

DEFAULT_STYLE: dict[str, str] = {
    "primary_color": "#1a3a5c",
    "accent_color": "#2e6da4",
    "font_body": '"Times New Roman", Times, serif',
    "font_heading": "Arial, Helvetica, sans-serif",
    "body_font_size": "11pt",
    "heading_font_size": "12pt",
    "name_font_size": "20pt",
    "header_alignment": "center",
    "section_decoration": "bottom-border",
    "heading_transform": "uppercase",
    "text_color": "#222222",
    "muted_color": "#666666",
    "border_color": "#cccccc",
    "page_width": "8.5in",
    "page_padding": "0.75in 0.75in 1in 0.75in",
    "date_column_width": "1.3in",
    "header_border_style": "2px solid",
    "header_bg_color": "",
    "name_font_weight": "bold",
    "name_letter_spacing": "0.05em",
    "section_margin_bottom": "1.2em",
    "heading_letter_spacing": "0.08em",
    "line_height": "1.4",
    "custom_css": "",
}


# ---------------------------------------------------------------------------
# Theme presets extracted from the old CSS files
# ---------------------------------------------------------------------------

THEME_PRESETS: dict[str, dict[str, str]] = {
    "academic": {
        "primary_color": "#1a3a5c", "accent_color": "#2e6da4",
        "font_body": '"Times New Roman", Times, serif',
        "font_heading": "Arial, Helvetica, sans-serif",
        "body_font_size": "11pt", "heading_font_size": "12pt",
        "name_font_size": "20pt", "header_alignment": "center",
        "section_decoration": "bottom-border", "heading_transform": "uppercase",
        "text_color": "#222222", "muted_color": "#666666", "border_color": "#cccccc",
        "page_width": "8.5in", "page_padding": "0.75in 0.75in 1in 0.75in",
        "date_column_width": "1.3in", "header_border_style": "2px solid",
        "name_font_weight": "bold", "name_letter_spacing": "0.05em",
        "section_margin_bottom": "1.2em", "heading_letter_spacing": "0.08em",
        "line_height": "1.4",
    },
    "unc": {
        "primary_color": "#13294B", "accent_color": "#4B9CD3",
        "font_body": "Helvetica, Arial, sans-serif",
        "font_heading": "Helvetica, Arial, sans-serif",
        "body_font_size": "10.5pt", "heading_font_size": "11pt",
        "name_font_size": "18pt", "header_alignment": "left",
        "section_decoration": "bottom-border", "heading_transform": "none",
        "text_color": "#222222", "muted_color": "#666666", "border_color": "#c0d0e0",
        "page_width": "8.5in", "page_padding": "0.75in",
        "date_column_width": "1.1in", "header_border_style": "2px solid",
        "name_font_weight": "bold", "name_letter_spacing": "0.02em",
        "section_margin_bottom": "1.1em", "heading_letter_spacing": "0",
        "line_height": "1.4",
    },
    "hopkins": {
        "primary_color": "#002D72", "accent_color": "#002D72",
        "font_body": '"Times New Roman", Times, serif',
        "font_heading": '"Times New Roman", Times, serif',
        "body_font_size": "12pt", "heading_font_size": "12pt",
        "name_font_size": "14pt", "header_alignment": "center",
        "section_decoration": "bottom-border", "heading_transform": "uppercase",
        "text_color": "#111111", "muted_color": "#555555", "border_color": "#aaaaaa",
        "page_width": "8.5in", "page_padding": "1in",
        "date_column_width": "1.3in", "header_border_style": "none",
        "name_font_weight": "bold", "name_letter_spacing": "0.04em",
        "section_margin_bottom": "1.2em", "heading_letter_spacing": "0.05em",
        "line_height": "1.5",
    },
    "unige": {
        "primary_color": "#C01584", "accent_color": "#a8127a",
        "font_body": '"Latin Modern Sans", "DejaVu Sans", Helvetica, Arial, sans-serif',
        "font_heading": '"Latin Modern Sans", "DejaVu Sans", Helvetica, Arial, sans-serif',
        "body_font_size": "11pt", "heading_font_size": "12pt",
        "name_font_size": "14pt", "header_alignment": "right",
        "section_decoration": "none", "heading_transform": "none",
        "text_color": "#1a1a1a", "muted_color": "#666666", "border_color": "#dddddd",
        "page_width": "8.27in", "page_padding": "1in 0.75in",
        "date_column_width": "1.1in", "header_border_style": "1px solid",
        "name_font_weight": "bold", "name_letter_spacing": "0",
        "section_margin_bottom": "1.2em", "heading_letter_spacing": "0",
        "line_height": "1.45",
    },
    "minimal": {
        "primary_color": "#333333", "accent_color": "#555555",
        "font_body": '"Helvetica Neue", Helvetica, Arial, sans-serif',
        "font_heading": '"Helvetica Neue", Helvetica, Arial, sans-serif',
        "body_font_size": "10.5pt", "heading_font_size": "9pt",
        "name_font_size": "22pt", "header_alignment": "left",
        "section_decoration": "bottom-border", "heading_transform": "uppercase",
        "text_color": "#333333", "muted_color": "#888888", "border_color": "#dddddd",
        "page_width": "8.5in", "page_padding": "0.75in",
        "date_column_width": "1.2in", "header_border_style": "none",
        "name_font_weight": "300", "name_letter_spacing": "0.1em",
        "section_margin_bottom": "1.5em", "heading_letter_spacing": "0.12em",
        "line_height": "1.5",
    },
    "modern": {
        "primary_color": "#7c3aed", "accent_color": "#5b21b6",
        "font_body": '"Georgia", serif',
        "font_heading": '"Arial", sans-serif',
        "body_font_size": "10.5pt", "heading_font_size": "11pt",
        "name_font_size": "24pt", "header_alignment": "left",
        "section_decoration": "left-border", "heading_transform": "uppercase",
        "text_color": "#1f2937", "muted_color": "#6b7280", "border_color": "#e5e7eb",
        "page_width": "8.5in", "page_padding": "0",
        "date_column_width": "1.2in", "header_border_style": "none",
        "header_bg_color": "#7c3aed",
        "name_font_weight": "bold", "name_letter_spacing": "0.02em",
        "section_margin_bottom": "1.2em", "heading_letter_spacing": "0.1em",
        "line_height": "1.45",
    },
}


def _resolve_style(style: dict | None) -> dict[str, str]:
    """Merge a style dict over DEFAULT_STYLE, filling gaps."""
    merged = dict(DEFAULT_STYLE)
    if style:
        for k, v in style.items():
            if v is not None:
                merged[k] = v
    return merged


def generate_css(style: dict | None) -> str:
    """Generate the full CSS string from a style property dict.

    Maps style properties to CSS rules targeting the same classes used by
    the old monolithic theme files (.cv-page, .cv-header, .cv-section-heading, etc.).
    """
    s = _resolve_style(style)

    # Section heading decoration
    heading_border = ""
    if s["section_decoration"] == "bottom-border":
        heading_border = f"border-bottom: 1px solid {s['border_color']}; padding-bottom: 2px;"
    elif s["section_decoration"] == "left-border":
        heading_border = f"border-left: 3px solid {s['primary_color']}; padding-left: 0.4em;"

    heading_transform = f"text-transform: {s['heading_transform']};" if s["heading_transform"] != "none" else ""

    # Header border
    header_border = ""
    if s["header_border_style"] and s["header_border_style"] != "none":
        header_border = f"border-bottom: {s['header_border_style']} {s['primary_color']};"

    # Header background
    header_bg = ""
    header_h1_color = s["primary_color"]
    header_contact_style = f"color: {s['muted_color']};"
    if s.get("header_bg_color"):
        header_bg = f"background: {s['header_bg_color']}; color: white; padding: 0.6in 0.75in 0.5in;"
        header_h1_color = "white"
        header_contact_style = "opacity: 0.85;"

    # Body padding — if page_padding is "0", the modern theme uses a cv-body wrapper
    body_wrapper_padding = ""
    if s["page_padding"] == "0":
        body_wrapper_padding = f".cv-body {{ padding: 0.5in 0.75in 1in; }}"

    css = f"""\
body {{
  font-family: {s['font_body']};
  font-size: {s['body_font_size']};
  color: {s['text_color']};
  background: #ffffff;
  margin: 0;
  padding: 0;
}}

.cv-page {{
  max-width: {s['page_width']};
  margin: 0 auto;
  padding: {s['page_padding']};
}}

.cv-header {{
  text-align: {s['header_alignment']};
  margin-bottom: 1em;
  {header_border}
  padding-bottom: 0.5em;
  {header_bg}
}}

.cv-header h1 {{
  font-family: {s['font_heading']};
  font-size: {s['name_font_size']};
  font-weight: {s['name_font_weight']};
  color: {header_h1_color};
  margin: 0 0 0.2em 0;
  letter-spacing: {s['name_letter_spacing']};
}}

.cv-header .contact-line {{
  font-size: 10pt;
  {header_contact_style}
}}

{body_wrapper_padding}

.cv-section {{
  margin-bottom: {s['section_margin_bottom']};
}}

.cv-section-heading {{
  font-family: {s['font_heading']};
  font-size: {s['heading_font_size']};
  font-weight: bold;
  color: {s['primary_color']};
  {heading_transform}
  letter-spacing: {s['heading_letter_spacing']};
  {heading_border}
  margin-bottom: 0.5em;
}}

.cv-entry {{
  display: flex;
  margin-bottom: 0.4em;
  line-height: {s['line_height']};
}}

.cv-entry-date {{
  flex: 0 0 {s['date_column_width']};
  color: {s['muted_color']};
  font-size: 10pt;
  padding-top: 0.05em;
}}

.cv-entry-body {{
  flex: 1;
}}

.cv-entry-title {{
  font-weight: bold;
}}

.cv-entry-org {{
  font-style: italic;
}}

.cv-entry-detail {{
  font-size: 10pt;
  color: {s['muted_color']};
}}

.pub-entry {{
  margin-bottom: 0.5em;
  padding-left: 2.5em;
  text-indent: -2.5em;
  line-height: 1.45;
}}

.pub-count {{ font-weight: normal; font-size: 0.85em; color: {s['muted_color']}; text-transform: none; letter-spacing: normal; }}
.pub-number {{ display: inline-block; min-width: 2em; text-align: right; margin-right: 0.4em; }}
.pub-title {{ font-style: italic; }}
.pub-corr {{ color: {s['accent_color']}; font-weight: bold; }}
.pub-select-flag {{ color: {s['accent_color']}; }}

.cv-subsection-heading {{
  font-family: {s['font_heading']};
  font-size: 10.5pt;
  font-weight: bold;
  color: {s['accent_color']};
  margin: 0.6em 0 0.3em 0;
  border-bottom: 1px dotted {s['border_color']};
  padding-bottom: 1px;
}}

.cv-grant-entry {{
  margin-bottom: 1em;
  padding-left: 0.1in;
}}

.cv-grant-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-weight: bold;
}}

.cv-grant-dates {{
  font-weight: normal;
  font-size: 10pt;
  color: {s['muted_color']};
  white-space: nowrap;
  margin-left: 1em;
}}

.cv-grant-pi {{
  display: flex;
  justify-content: space-between;
  font-size: 10pt;
}}

.cv-grant-amount {{
  color: {s['muted_color']};
}}

.cv-grant-title {{
  font-style: italic;
  margin: 0.15em 0;
}}

.cv-grant-description {{
  font-size: 10pt;
  color: {s['muted_color']};
  margin: 0.15em 0;
  line-height: 1.4;
}}

.cv-grant-role {{
  font-size: 10pt;
  margin-top: 0.1em;
}}

ul.cv-list {{
  margin: 0 0 0.3em 1em;
  padding: 0;
  list-style-type: disc;
}}

ul.cv-list li {{
  margin-bottom: 0.2em;
}}

@media print {{
  .cv-page {{ padding: 0; }}
  body {{ font-size: 10.5pt; }}
  .cv-header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
"""

    # Append custom CSS if any
    custom = s.get("custom_css", "").strip()
    if custom:
        css += "\n/* Custom CSS */\n" + custom + "\n"

    return css


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


def render_cv_html(cv_data: dict, style: dict | None = None, sections: list[dict] | None = None) -> str:
    """Render the full CV as HTML.

    Args:
        cv_data: Assembled CV data dict.
        style: Style properties dict (merged over DEFAULT_STYLE).
        sections: Ordered list of enabled section dicts.
    """
    if sections is None:
        sections = []

    theme_css_content = generate_css(style)

    context = {
        "cv": cv_data,
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
