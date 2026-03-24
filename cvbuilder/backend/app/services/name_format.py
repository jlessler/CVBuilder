"""Format author names and citations in standard bibliography styles."""
from __future__ import annotations

from typing import Any, Optional


# ---------------------------------------------------------------------------
# Author name formatting
# ---------------------------------------------------------------------------

def _initials_dotted(name: Optional[str]) -> str:
    """Convert a name or initial to dotted initials: 'Justin' -> 'J.', 'JK' -> 'J. K.'"""
    if not name:
        return ""
    # Already has dots: "J." or "J. K."
    cleaned = name.replace(".", "").replace(" ", "")
    if not cleaned:
        return ""
    # If all uppercase and short, treat as initials
    if cleaned.isupper() and len(cleaned) <= 3:
        return ". ".join(cleaned) + "."
    # Full name — take first letter
    return cleaned[0].upper() + "."


def _initials_bare(name: Optional[str]) -> str:
    """Convert a name or initial to bare initials: 'Justin' -> 'J', 'J. K.' -> 'JK'"""
    if not name:
        return ""
    cleaned = name.replace(".", "").replace(" ", "")
    if not cleaned:
        return ""
    if cleaned.isupper() and len(cleaned) <= 3:
        return cleaned
    return cleaned[0].upper()


def format_author_name(author: Any, style: str = "display") -> str:
    """Format a single author's name according to the given style.

    Args:
        author: Object with author_name, given_name, family_name, middle_name, suffix attributes
               (or dict with those keys).
        style: One of 'display', 'apa', 'vancouver', 'chicago', 'full'.

    Returns:
        Formatted name string.
    """
    def _get(key: str, default: str = "") -> str:
        if isinstance(author, dict):
            return author.get(key, default) or default
        return getattr(author, key, default) or default

    author_name = _get("author_name")
    family = _get("family_name")
    given = _get("given_name")
    middle = _get("middle_name")
    suffix = _get("suffix")

    # Fallback: no structured fields
    if not family:
        return author_name

    if style == "display":
        # Default CVBuilder format: "Family GI" (e.g., "Lessler JK")
        from app.services.name_parser import compose_author_name
        return compose_author_name(given, family, middle, suffix)

    if style == "apa":
        # APA: "Lessler, J. K."
        parts = [family + ","]
        gi = _initials_dotted(given)
        mi = _initials_dotted(middle)
        inits = " ".join(filter(None, [gi, mi]))
        if inits:
            parts.append(inits)
        if suffix:
            parts.append(suffix)
        return " ".join(parts)

    if style == "vancouver":
        # Vancouver/NLM: "Lessler JK"
        gi = _initials_bare(given)
        mi = _initials_bare(middle)
        inits = gi + mi
        result = family
        if inits:
            result += " " + inits
        if suffix:
            result += " " + suffix
        return result

    if style == "chicago":
        # Chicago: "Lessler, Justin K."
        parts = [family + ","]
        if given:
            parts.append(given)
        if middle:
            mi = _initials_dotted(middle)
            parts.append(mi)
        if suffix:
            parts.append(suffix)
        return " ".join(parts)

    if style == "full":
        # Full natural order: "Justin K. Lessler"
        parts = []
        if given:
            parts.append(given)
        if middle:
            mi = _initials_dotted(middle)
            parts.append(mi)
        parts.append(family)
        if suffix:
            parts.append(suffix)
        return " ".join(parts)

    # Unknown style — fallback
    return author_name


# ---------------------------------------------------------------------------
# Author list formatting
# ---------------------------------------------------------------------------

# Per-style list formatting rules
_LIST_RULES = {
    "display": {"sep": ", ", "last_sep": ", ", "et_al": False},
    "apa": {"sep": ", ", "last_sep": ", & ", "et_al_threshold": 21, "et_al_show": 19},
    "vancouver": {"sep": ", ", "last_sep": ", ", "et_al_threshold": 7, "et_al_show": 6},
    "chicago": {"sep": ", ", "last_sep": ", and ", "et_al_threshold": 11, "et_al_show": 7},
    "full": {"sep": ", ", "last_sep": ", and ", "et_al": False},
}


def format_author_list(
    authors: list[Any],
    style: str = "display",
    max_authors: int = 0,
    profile_name: str = "",
) -> str:
    """Format a list of authors as an author string.

    Args:
        authors: List of author objects/dicts.
        style: Citation style.
        max_authors: Override max authors before et al. (0 = use style default).
        profile_name: CV holder's name for bold-self highlighting.

    Returns:
        Formatted author string with role superscripts and bold-self markup.
    """
    if not authors:
        return ""

    rules = _LIST_RULES.get(style, _LIST_RULES["display"])

    # Determine et al. truncation
    threshold = max_authors if max_authors > 0 else rules.get("et_al_threshold", 0)
    show_count = max_authors - 1 if max_authors > 0 else rules.get("et_al_show", 0)
    use_et_al = threshold > 0 and len(authors) > threshold

    # Format individual names
    formatted: list[str] = []
    items = authors[:show_count] if use_et_al else authors

    for a in items:
        name = format_author_name(a, style)

        # Bold self
        if profile_name:
            from app.services.pdf import _bold_self
            aname = _get_attr(a, "author_name") or name
            if "<strong>" in _bold_self(aname, profile_name):
                name = f"<strong>{name}</strong>"

        # Role superscripts
        if _get_attr(a, "student"):
            name += "<sup>&dagger;</sup>"
        if _get_attr(a, "cofirst"):
            name += "<sup>&#8225;</sup>"
        if _get_attr(a, "cosenior"):
            name += "<sup>&sect;</sup>"

        formatted.append(name)

    # Join
    if use_et_al:
        result = rules["sep"].join(formatted) + ", et al."
    elif len(formatted) == 1:
        result = formatted[0]
    elif len(formatted) == 2:
        result = rules.get("last_sep", ", ").join(formatted)
    else:
        result = rules["sep"].join(formatted[:-1]) + rules.get("last_sep", ", ") + formatted[-1]

    # Corresponding author marker (appended to end if any author is corresponding)
    if any(_get_attr(a, "corresponding") for a in authors):
        result += "<sup>*</sup>"

    return result


def _get_attr(obj: Any, key: str, default: Any = False) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ---------------------------------------------------------------------------
# Full citation formatting
# ---------------------------------------------------------------------------

def format_citation(
    work: Any,
    style: str = "display",
    max_authors: int = 0,
    profile_name: str = "",
) -> str:
    """Format a complete citation for a work in the given style.

    Args:
        work: Work object with title, year, data, authors attributes.
        style: Citation style.
        max_authors: Override max authors before et al.
        profile_name: CV holder's name for bold-self.

    Returns:
        Formatted citation HTML string.
    """
    def _get(key: str, default: str = "") -> str:
        if isinstance(work, dict):
            return work.get(key, default) or default
        return getattr(work, key, default) or default

    def _data_get(key: str, default: str = "") -> str:
        if isinstance(work, dict):
            data = work.get("data", {}) or {}
        else:
            data = getattr(work, "data", {}) or {}
        return data.get(key, default) or default

    authors_list = []
    if isinstance(work, dict):
        authors_list = work.get("authors", [])
    else:
        authors_list = getattr(work, "authors", [])

    authors_str = format_author_list(authors_list, style, max_authors, profile_name)
    title = _get("title")
    year = _get("year")
    journal = _data_get("journal")
    volume = _data_get("volume")
    issue = _data_get("issue")
    pages = _data_get("pages")
    doi = _get("doi")

    if style == "display":
        # Keep existing format — return empty to signal the template should render itself
        return ""

    if style == "apa":
        return _format_apa(authors_str, title, year, journal, volume, issue, pages, doi)
    if style == "vancouver":
        return _format_vancouver(authors_str, title, year, journal, volume, issue, pages, doi)
    if style == "chicago":
        return _format_chicago(authors_str, title, year, journal, volume, issue, pages, doi)
    if style == "full":
        # Full uses the same layout as display but with full names
        return ""

    return ""


def _format_apa(authors: str, title: str, year: str, journal: str,
                volume: str, issue: str, pages: str, doi: str) -> str:
    """APA format: Authors (Year). Title. *Journal*, *Volume*(Issue), Pages. doi"""
    parts = []
    if authors:
        parts.append(authors)
    year_str = f" ({year})" if year else ""
    if parts:
        parts[-1] += year_str + "."
    else:
        parts.append(year_str.strip() + ".")

    if title:
        parts.append(title + ".")

    journal_part = ""
    if journal:
        journal_part = f"<em>{journal}</em>"
        if volume:
            journal_part += f", <em>{volume}</em>"
            if issue:
                journal_part += f"({issue})"
        if pages:
            journal_part += f", {pages}"
        journal_part += "."
    if journal_part:
        parts.append(journal_part)

    if doi:
        parts.append(f'<a href="https://doi.org/{doi}">https://doi.org/{doi}</a>')

    return " ".join(parts)


def _format_vancouver(authors: str, title: str, year: str, journal: str,
                      volume: str, issue: str, pages: str, doi: str) -> str:
    """Vancouver format: Authors. Title. Journal. Year;Volume(Issue):Pages. doi"""
    parts = []
    if authors:
        parts.append(authors + ".")
    if title:
        parts.append(title + ".")

    journal_part = ""
    if journal:
        journal_part = journal + "."
        if year:
            journal_part += f" {year}"
        if volume:
            journal_part += f";{volume}"
            if issue:
                journal_part += f"({issue})"
        if pages:
            journal_part += f":{pages}"
        journal_part += "."
    elif year:
        parts.append(f"{year}.")
    if journal_part:
        parts.append(journal_part)

    if doi:
        parts.append(f'doi: <a href="https://doi.org/{doi}">{doi}</a>')

    return " ".join(parts)


def _format_chicago(authors: str, title: str, year: str, journal: str,
                    volume: str, issue: str, pages: str, doi: str) -> str:
    """Chicago format: Authors. "Title." *Journal* Volume, no. Issue (Year): Pages. doi"""
    parts = []
    if authors:
        parts.append(authors + ".")
    if title:
        parts.append(f'&ldquo;{title}.&rdquo;')

    journal_part = ""
    if journal:
        journal_part = f"<em>{journal}</em>"
        if volume:
            journal_part += f" {volume}"
        if issue:
            journal_part += f", no. {issue}"
        if year:
            journal_part += f" ({year})"
        if pages:
            journal_part += f": {pages}"
        journal_part += "."
    elif year:
        parts.append(f"({year}).")
    if journal_part:
        parts.append(journal_part)

    if doi:
        parts.append(f'<a href="https://doi.org/{doi}">https://doi.org/{doi}</a>')

    return " ".join(parts)
