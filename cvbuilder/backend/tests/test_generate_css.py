"""Unit tests for generate_css() and related style functions in services/pdf.py."""
import pytest

from app.services.pdf import (
    DEFAULT_STYLE,
    THEME_PRESETS,
    _resolve_style,
    generate_css,
)


# ---------------------------------------------------------------------------
# _resolve_style
# ---------------------------------------------------------------------------

class TestResolveStyle:

    def test_none_returns_defaults(self):
        result = _resolve_style(None)
        assert result == DEFAULT_STYLE

    def test_empty_dict_returns_defaults(self):
        result = _resolve_style({})
        assert result == DEFAULT_STYLE

    def test_override_single_key(self):
        result = _resolve_style({"primary_color": "#ff0000"})
        assert result["primary_color"] == "#ff0000"
        assert result["accent_color"] == DEFAULT_STYLE["accent_color"]

    def test_override_multiple_keys(self):
        result = _resolve_style({
            "primary_color": "#ff0000",
            "font_body": "Georgia, serif",
            "line_height": "1.8",
        })
        assert result["primary_color"] == "#ff0000"
        assert result["font_body"] == "Georgia, serif"
        assert result["line_height"] == "1.8"

    def test_none_values_ignored(self):
        result = _resolve_style({"primary_color": None})
        assert result["primary_color"] == DEFAULT_STYLE["primary_color"]

    def test_extra_keys_preserved(self):
        result = _resolve_style({"custom_thing": "hello"})
        assert result["custom_thing"] == "hello"

    def test_all_default_keys_present(self):
        result = _resolve_style({"primary_color": "#000"})
        for key in DEFAULT_STYLE:
            assert key in result


# ---------------------------------------------------------------------------
# THEME_PRESETS structure
# ---------------------------------------------------------------------------

class TestThemePresets:

    REQUIRED_KEYS = [
        "primary_color", "accent_color", "font_body", "font_heading",
        "body_font_size", "heading_font_size", "name_font_size",
        "header_alignment", "section_decoration", "heading_transform",
        "text_color", "muted_color", "border_color",
        "page_width", "page_padding", "date_column_width",
        "header_border_style", "name_font_weight", "name_letter_spacing",
        "section_margin_bottom", "heading_letter_spacing", "line_height",
    ]

    EXPECTED_PRESETS = ["academic", "unc", "hopkins", "unige", "minimal", "modern"]

    def test_all_presets_exist(self):
        for name in self.EXPECTED_PRESETS:
            assert name in THEME_PRESETS, f"Missing preset: {name}"

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESETS)
    def test_preset_has_required_keys(self, preset_name):
        preset = THEME_PRESETS[preset_name]
        for key in self.REQUIRED_KEYS:
            assert key in preset, f"{preset_name} missing key: {key}"

    @pytest.mark.parametrize("preset_name", EXPECTED_PRESETS)
    def test_preset_values_are_strings(self, preset_name):
        preset = THEME_PRESETS[preset_name]
        for key, val in preset.items():
            assert isinstance(val, str), f"{preset_name}.{key} is {type(val)}, expected str"

    def test_academic_matches_defaults(self):
        """Academic preset should match DEFAULT_STYLE for all shared keys."""
        academic = THEME_PRESETS["academic"]
        for key in academic:
            if key in DEFAULT_STYLE:
                assert academic[key] == DEFAULT_STYLE[key], (
                    f"academic[{key}]={academic[key]!r} != DEFAULT_STYLE[{key}]={DEFAULT_STYLE[key]!r}"
                )

    def test_each_preset_generates_valid_css(self):
        for name, preset in THEME_PRESETS.items():
            css = generate_css(preset)
            assert isinstance(css, str)
            assert len(css) > 100, f"Preset {name} generated suspiciously short CSS"


# ---------------------------------------------------------------------------
# generate_css — basic output
# ---------------------------------------------------------------------------

class TestGenerateCssBasic:

    def test_returns_string(self):
        assert isinstance(generate_css(None), str)

    def test_contains_core_selectors(self):
        css = generate_css(None)
        for selector in [
            "body {", ".cv-page {", ".cv-header {", ".cv-header h1 {",
            ".cv-section {", ".cv-section-heading {", ".cv-entry {",
            ".cv-entry-date {", ".cv-entry-body {", ".pub-entry {",
            ".cv-subsection-heading {", ".cv-grant-entry {",
            "@media print {",
        ]:
            assert selector in css, f"Missing selector: {selector}"

    def test_default_style_colors_applied(self):
        css = generate_css(None)
        assert DEFAULT_STYLE["primary_color"] in css
        assert DEFAULT_STYLE["accent_color"] in css
        assert DEFAULT_STYLE["text_color"] in css
        assert DEFAULT_STYLE["muted_color"] in css

    def test_default_fonts_applied(self):
        css = generate_css(None)
        assert DEFAULT_STYLE["font_body"] in css
        assert DEFAULT_STYLE["font_heading"] in css

    def test_custom_colors_override(self):
        css = generate_css({"primary_color": "#abcdef", "accent_color": "#fedcba"})
        assert "#abcdef" in css
        assert "#fedcba" in css
        assert DEFAULT_STYLE["primary_color"] not in css


# ---------------------------------------------------------------------------
# generate_css — section decoration
# ---------------------------------------------------------------------------

class TestSectionDecoration:

    def test_bottom_border(self):
        css = generate_css({"section_decoration": "bottom-border"})
        assert "border-bottom:" in css
        assert "padding-bottom: 2px" in css

    def test_left_border(self):
        css = generate_css({
            "section_decoration": "left-border",
            "primary_color": "#123456",
        })
        assert "border-left: 3px solid #123456" in css
        assert "padding-left: 0.4em" in css

    def test_none_decoration(self):
        css = generate_css({"section_decoration": "none"})
        # The .cv-section-heading rule should not have border-bottom or border-left
        # from the decoration logic (there may be other borders elsewhere)
        heading_block = css.split(".cv-section-heading {")[1].split("}")[0]
        assert "border-bottom:" not in heading_block
        assert "border-left:" not in heading_block


# ---------------------------------------------------------------------------
# generate_css — heading transform
# ---------------------------------------------------------------------------

class TestHeadingTransform:

    def test_uppercase(self):
        css = generate_css({"heading_transform": "uppercase"})
        assert "text-transform: uppercase;" in css

    def test_none_transform(self):
        css = generate_css({"heading_transform": "none"})
        heading_block = css.split(".cv-section-heading {")[1].split("}")[0]
        assert "text-transform:" not in heading_block


# ---------------------------------------------------------------------------
# generate_css — header border
# ---------------------------------------------------------------------------

class TestHeaderBorder:

    def test_solid_border(self):
        css = generate_css({
            "header_border_style": "2px solid",
            "primary_color": "#aabbcc",
        })
        assert "border-bottom: 2px solid #aabbcc" in css

    def test_none_border(self):
        css = generate_css({"header_border_style": "none"})
        header_block = css.split(".cv-header {")[1].split("}")[0]
        assert "border-bottom:" not in header_block

    def test_empty_border(self):
        css = generate_css({"header_border_style": ""})
        header_block = css.split(".cv-header {")[1].split("}")[0]
        assert "border-bottom:" not in header_block


# ---------------------------------------------------------------------------
# generate_css — header background (modern theme)
# ---------------------------------------------------------------------------

class TestHeaderBackground:

    def test_no_bg_by_default(self):
        css = generate_css(None)
        assert "background:" not in css.split(".cv-header {")[1].split("}")[0] or \
               DEFAULT_STYLE["header_bg_color"] != ""

    def test_bg_color_applied(self):
        css = generate_css({"header_bg_color": "#7c3aed"})
        header_block = css.split(".cv-header {")[1].split("}")[0]
        assert "background: #7c3aed" in header_block

    def test_bg_color_forces_white_h1(self):
        css = generate_css({"header_bg_color": "#7c3aed"})
        h1_block = css.split(".cv-header h1 {")[1].split("}")[0]
        assert "color: white" in h1_block

    def test_bg_color_forces_contact_opacity(self):
        css = generate_css({"header_bg_color": "#7c3aed"})
        contact_block = css.split(".cv-header .contact-line {")[1].split("}")[0]
        assert "opacity: 0.85" in contact_block

    def test_no_bg_uses_muted_contact(self):
        css = generate_css({"header_bg_color": ""})
        contact_block = css.split(".cv-header .contact-line {")[1].split("}")[0]
        assert "color:" in contact_block
        assert "opacity" not in contact_block


# ---------------------------------------------------------------------------
# generate_css — page padding / body wrapper
# ---------------------------------------------------------------------------

class TestPagePadding:

    def test_zero_padding_adds_body_wrapper(self):
        css = generate_css({"page_padding": "0"})
        assert ".cv-body {" in css
        assert "padding: 0.5in 0.75in 1in" in css

    def test_normal_padding_no_body_wrapper(self):
        css = generate_css({"page_padding": "0.75in"})
        assert ".cv-body {" not in css


# ---------------------------------------------------------------------------
# generate_css — custom CSS
# ---------------------------------------------------------------------------

class TestCustomCss:

    def test_custom_css_appended(self):
        css = generate_css({"custom_css": ".my-class { color: red; }"})
        assert "/* Custom CSS */" in css
        assert ".my-class { color: red; }" in css

    def test_empty_custom_css_not_appended(self):
        css = generate_css({"custom_css": ""})
        assert "/* Custom CSS */" not in css

    def test_whitespace_custom_css_not_appended(self):
        css = generate_css({"custom_css": "   \n  "})
        assert "/* Custom CSS */" not in css

    def test_custom_css_at_end(self):
        css = generate_css({"custom_css": ".footer { display: none; }"})
        # Custom CSS should be after the @media print block
        custom_pos = css.index("/* Custom CSS */")
        print_pos = css.index("@media print")
        assert custom_pos > print_pos


# ---------------------------------------------------------------------------
# generate_css — full preset rendering
# ---------------------------------------------------------------------------

class TestPresetRendering:

    def test_unc_preset(self):
        css = generate_css(THEME_PRESETS["unc"])
        assert "#13294B" in css  # primary
        assert "#4B9CD3" in css  # accent
        assert "text-align: left" in css  # header alignment
        assert "Helvetica" in css

    def test_modern_preset_has_bg(self):
        css = generate_css(THEME_PRESETS["modern"])
        assert "background: #7c3aed" in css
        assert ".cv-body {" in css  # zero padding → body wrapper
        assert "border-left: 3px solid" in css  # left-border decoration

    def test_unige_preset_no_decoration(self):
        css = generate_css(THEME_PRESETS["unige"])
        heading_block = css.split(".cv-section-heading {")[1].split("}")[0]
        assert "border-bottom:" not in heading_block
        assert "border-left:" not in heading_block
        assert "text-transform:" not in css.split(".cv-section-heading {")[1].split("}")[0]

    def test_hopkins_no_header_border(self):
        css = generate_css(THEME_PRESETS["hopkins"])
        header_block = css.split(".cv-header {")[1].split("}")[0]
        assert "border-bottom:" not in header_block

    def test_minimal_light_font_weight(self):
        css = generate_css(THEME_PRESETS["minimal"])
        h1_block = css.split(".cv-header h1 {")[1].split("}")[0]
        assert "font-weight: 300" in h1_block
