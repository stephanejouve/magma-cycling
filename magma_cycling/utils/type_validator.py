"""Semantic validation between session_type and content (description + TSS)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_INTENSITY_KEYWORDS = re.compile(r"\d+\s*%|FTP|seuil|threshold|VO2|MAP|sprint|force", re.IGNORECASE)
_INTERVAL_PATTERN = re.compile(r"\d+\s*x\s*\d+\s*m(?:in)?", re.IGNORECASE)
_HIGH_ZONE_KEYWORDS = re.compile(r"1[0-2]\d\s*%|VO2\s*max|MAP|zone\s*[56]|PMA", re.IGNORECASE)


@dataclass
class TypeValidation:
    """Result of session type validation."""

    valid: bool
    warnings: list[str] = field(default_factory=list)
    suggested_type: str | None = None


def validate_session_type(
    session_type: str,
    description: str,
    tss: int | float | None = None,
) -> TypeValidation:
    """Validate coherence between session_type and its content.

    Args:
        session_type: Session type code (REC, END, INT, VO2, MAP, FRC, etc.)
        description: Session description text.
        tss: Planned TSS (optional).

    Returns:
        TypeValidation with valid flag, warnings, and optional suggested type.
    """
    warnings: list[str] = []
    suggested: str | None = None
    tss_val = tss or 0

    if session_type == "REC":
        if tss_val > 40:
            warnings.append(f"REC avec TSS={tss_val} (attendu <= 40)")
        if _INTENSITY_KEYWORDS.search(description):
            warnings.append("REC contient des mots-clés d'intensité")
            suggested = "INT"

    elif session_type == "END":
        if _INTERVAL_PATTERN.search(description):
            warnings.append("END contient une structure d'intervalles")
            suggested = "INT"

    elif session_type in ("INT", "VO2", "MAP", "FRC"):
        if tss_val < 30 and not _INTENSITY_KEYWORDS.search(description):
            warnings.append(f"{session_type} avec TSS={tss_val} et pas de mots-clés intensité")
            suggested = "REC" if tss_val <= 30 else "END"

    return TypeValidation(
        valid=len(warnings) == 0,
        warnings=warnings,
        suggested_type=suggested,
    )
