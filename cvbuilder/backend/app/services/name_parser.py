"""Parse free-text author name strings into structured name parts."""

from __future__ import annotations

import re
from typing import Optional, TypedDict


class ParsedName(TypedDict, total=False):
    given_name: Optional[str]
    family_name: Optional[str]
    middle_name: Optional[str]
    suffix: Optional[str]


# Common surname particles (case-insensitive matching)
_PARTICLES = {
    "van", "von", "de", "del", "della", "di", "du", "des", "der", "den",
    "la", "le", "el", "al", "bin", "ibn", "ben", "st", "st.", "mac", "mc",
    "o'", "d'",
}

# Recognised suffixes
_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v", "phd", "md"}


def _is_initials(token: str) -> bool:
    """Return True if token looks like initials (e.g. 'J', 'JK', 'J.')."""
    cleaned = token.replace(".", "")
    return len(cleaned) <= 3 and cleaned.isalpha() and cleaned.isupper()


def _split_initials(token: str) -> tuple[str, Optional[str]]:
    """Split an initials token like 'JK' into ('J', 'K')."""
    cleaned = token.replace(".", "")
    if len(cleaned) == 1:
        return cleaned, None
    return cleaned[0], cleaned[1:]


def _extract_suffix(tokens: list[str]) -> tuple[list[str], Optional[str]]:
    """Remove and return a suffix token from the list if present."""
    if not tokens:
        return tokens, None
    # Check last token
    if tokens[-1].rstrip(".,").lower() in _SUFFIXES:
        suffix = tokens[-1].rstrip(",")
        return tokens[:-1], suffix
    return tokens, None


def _collect_particle_family(tokens: list[str], start: int) -> tuple[str, int]:
    """Starting at `start`, collect surname particles + family name.

    Returns (family_name, index_past_end).
    """
    parts: list[str] = []
    i = start
    while i < len(tokens):
        low = tokens[i].lower().rstrip(",")
        if low in _PARTICLES or tokens[i].lower().rstrip(",") in _PARTICLES:
            parts.append(tokens[i].rstrip(","))
            i += 1
        else:
            break
    # The next token (or last remaining) is the core family name
    if i < len(tokens):
        parts.append(tokens[i].rstrip(","))
        i += 1
    return " ".join(parts), i


def parse_author_name(name: str) -> ParsedName:
    """Parse a free-text author name into structured parts.

    Handles common academic formats:
    - "Family Given"          → Lessler J
    - "Family GivenMiddle"    → Lessler JK
    - "Given Family"          → Justin Lessler
    - "Given Middle Family"   → Justin K Lessler
    - "Family, Given"         → Lessler, Justin
    - "Family, Given Middle"  → Lessler, Justin K
    - "Family, G. M."         → Lessler, J. K.
    - Particles: "van der Berg A", "de la Cruz, Maria"
    - Suffixes: "Smith Jr, J", "Jones III, Robert"
    """
    if not name or not name.strip():
        return ParsedName(given_name=None, family_name=None, middle_name=None, suffix=None)

    name = name.strip()
    # Normalise whitespace
    name = re.sub(r"\s+", " ", name)

    result = ParsedName(given_name=None, family_name=None, middle_name=None, suffix=None)

    # ── Comma format: "Family, Given [Middle]" or "Family Suffix, Given" ──
    if "," in name:
        parts = [p.strip() for p in name.split(",", maxsplit=2)]
        family_part = parts[0]
        given_part = parts[1] if len(parts) > 1 else ""

        # Check if second segment is a suffix (e.g. "Smith, Jr" with possible 3rd part)
        if given_part.rstrip(".,").lower() in _SUFFIXES:
            result["suffix"] = given_part.rstrip(",")
            if len(parts) > 2:
                given_part = parts[2].strip()
            else:
                # "Smith, Jr" with no given — treat as family + suffix only
                result["family_name"] = family_part
                return result

        # Check for suffix at end of family part: "Smith Jr, J"
        fam_tokens = family_part.split()
        if len(fam_tokens) > 1 and fam_tokens[-1].rstrip(".,").lower() in _SUFFIXES:
            result["suffix"] = fam_tokens[-1].rstrip(",")
            family_part = " ".join(fam_tokens[:-1])

        result["family_name"] = family_part

        # Parse given part
        given_tokens = given_part.split()
        given_tokens, suffix = _extract_suffix(given_tokens)
        if suffix and not result["suffix"]:
            result["suffix"] = suffix

        if len(given_tokens) == 0:
            pass
        elif len(given_tokens) == 1:
            tok = given_tokens[0].rstrip(".")
            if _is_initials(tok):
                first, mid = _split_initials(tok)
                result["given_name"] = first + "."
                if mid:
                    result["middle_name"] = ".".join(mid) + "."
            else:
                result["given_name"] = given_tokens[0]
        else:
            result["given_name"] = given_tokens[0]
            mid_parts = given_tokens[1:]
            result["middle_name"] = " ".join(mid_parts)

        return result

    # ── No comma: positional parsing ──
    tokens = name.split()
    tokens, suffix = _extract_suffix(tokens)
    result["suffix"] = suffix

    if len(tokens) == 0:
        return result

    if len(tokens) == 1:
        # Single token — treat as family name (mononym)
        result["family_name"] = tokens[0]
        return result

    # Check if first token looks like a family name followed by initials
    # Pattern: "Lessler J" or "Lessler JK"
    if len(tokens) == 2:
        if _is_initials(tokens[1]):
            # "Lessler J" or "Lessler JK"
            result["family_name"] = tokens[0]
            first, mid = _split_initials(tokens[1])
            result["given_name"] = first + "."
            if mid:
                result["middle_name"] = ".".join(mid) + "."
            return result
        elif _is_initials(tokens[0]):
            # "J Lessler" or "JK Lessler"
            first, mid = _split_initials(tokens[0])
            result["given_name"] = first + "."
            if mid:
                result["middle_name"] = ".".join(mid) + "."
            result["family_name"] = tokens[1]
            return result
        else:
            # "Justin Lessler" — first=given, last=family
            result["given_name"] = tokens[0]
            result["family_name"] = tokens[1]
            return result

    # 3+ tokens
    # Check for leading initials: "J K Lessler"
    if _is_initials(tokens[0]) and not _is_initials(tokens[-1]):
        result["given_name"] = tokens[0] if "." in tokens[0] else tokens[0] + "."
        # Everything between first and last could be middle or particles
        remaining = tokens[1:]
        # Find where family name starts (could have particles)
        # Walk backwards from end: last non-particle is family, particles before it are part of family
        family_start = len(remaining) - 1
        while family_start > 0 and remaining[family_start - 1].lower().rstrip(",") in _PARTICLES:
            family_start -= 1
        result["family_name"] = " ".join(remaining[family_start:])
        mid_tokens = remaining[:family_start]
        if mid_tokens:
            result["middle_name"] = " ".join(mid_tokens)
        return result

    # Check for trailing initials: "Lessler J K" — unlikely but handle
    if _is_initials(tokens[-1]) and not _is_initials(tokens[0]):
        # Could be "van der Berg J K" — collect particle family from start
        family_name, idx = _collect_particle_family(tokens, 0)
        # Remaining tokens should be initials
        init_tokens = tokens[idx:]
        if init_tokens:
            first_init = init_tokens[0].replace(".", "")
            result["given_name"] = first_init[0] + "." if first_init else None
            if len(first_init) > 1:
                result["middle_name"] = ".".join(first_init[1:]) + "."
            elif len(init_tokens) > 1:
                mid = "".join(t.replace(".", "") for t in init_tokens[1:])
                result["middle_name"] = ".".join(mid) + "." if mid else None
        result["family_name"] = family_name
        return result

    # Default: "Given Middle ... Family" — first=given, last=family, middle=rest
    result["given_name"] = tokens[0]
    # Walk backwards to find family (with particles)
    family_start = len(tokens) - 1
    while family_start > 1 and tokens[family_start - 1].lower().rstrip(",") in _PARTICLES:
        family_start -= 1
    result["family_name"] = " ".join(tokens[family_start:])
    mid_tokens = tokens[1:family_start]
    if mid_tokens:
        result["middle_name"] = " ".join(mid_tokens)

    return result


def compose_author_name(
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    middle_name: Optional[str] = None,
    suffix: Optional[str] = None,
) -> str:
    """Compose a display name from structured parts.

    Returns "Family GivenInitial" format (e.g. "Lessler J" or "Lessler JK").
    """
    if not family_name:
        return given_name or ""

    parts = [family_name]

    initials = ""
    if given_name:
        initials += given_name[0].upper()
    if middle_name:
        for part in middle_name.replace(".", " ").split():
            if part:
                initials += part[0].upper()
    if initials:
        parts.append(initials)

    name = " ".join(parts)
    if suffix:
        name += f" {suffix}"
    return name
