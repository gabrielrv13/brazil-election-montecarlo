"""Candidate color mappings for election visualizations."""

from __future__ import annotations

import unicodedata


SECOND_ROUND_2026_COLORS: dict[str, str] = {
    "lula": "#e74c3c",
    "flavio bolsonaro": "#3498db",
    "f. bolsonaro": "#3498db",
}


def normalize_candidate_name(name: str) -> str:
    """Normalize candidate names for accent- and case-insensitive matching."""
    normalized = unicodedata.normalize("NFKD", name)
    without_accents = "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )
    return " ".join(without_accents.casefold().split())


def candidate_color(
    name: str,
    *,
    fallback: str,
    mapping: dict[str, str] | None = None,
) -> str:
    """Return a candidate's mapped color or the supplied fallback."""
    colors = SECOND_ROUND_2026_COLORS if mapping is None else mapping
    normalized_mapping = {
        normalize_candidate_name(candidate): color
        for candidate, color in colors.items()
    }
    return normalized_mapping.get(normalize_candidate_name(name), fallback)


def candidate_palette(
    candidates: list[str],
    base_palette: list[str],
) -> list[str]:
    """Build an identity-based palette, preserving candidate order.

    Known 2026 runoff candidates keep their assigned colors regardless
    of input order. Unmapped candidates receive generic colors that do
    not collide with colors reserved for known candidates when possible.
    """
    if not candidates:
        return []

    reserved = {
        candidate_color(name, fallback=None)
        for name in candidates
    }
    reserved.discard(None)

    result: list[str] = []
    used: set[str] = set()

    for index, name in enumerate(candidates):
        known_color = candidate_color(name, fallback=None)

        if known_color is not None:
            color = known_color
        else:
            available = [
                color for color in base_palette
                if color not in reserved and color not in used
            ]
            if available:
                color = available[0]
            elif base_palette:
                color = base_palette[index % len(base_palette)]
            else:
                color = "#7f7f7f"

        result.append(color)
        used.add(color)

    return result
