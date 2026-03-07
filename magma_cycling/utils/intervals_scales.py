"""Intervals.icu scale constants and formatters."""

FEEL_LABELS: dict[int, str] = {
    1: "Excellent",
    2: "Bien",
    3: "Moyen",
    4: "Passable",
    5: "Mauvais",
}

FEEL_EMOJIS: dict[int, str] = {
    1: "\U0001f60a",
    2: "\U0001f642",
    3: "\U0001f610",
    4: "\U0001f615",
    5: "\U0001f623",
}


def format_feel(value: int | None, with_emoji: bool = False) -> str:
    """Format Feel value (1-5 Intervals.icu scale).

    Args:
        value: Feel value 1-5 or None (1=Excellent, 5=Poor).
        with_emoji: If True, prepend emoji and append (N/5).

    Returns:
        Formatted label string.
    """
    if value is None:
        return "_Non renseigné_"

    label = FEEL_LABELS.get(value)
    if label is None:
        return f"_Valeur inconnue: {value}_"

    if with_emoji:
        emoji = FEEL_EMOJIS.get(value, "")
        return f"{emoji} {label} ({value}/5)"

    return label


SLEEP_QUALITY_LABELS: dict[int, str] = {
    1: "Excellent",
    2: "Good",
    3: "Average",
    4: "Poor",
}


def sleep_score_to_quality(score: int | None) -> int | None:
    """Convert Withings sleep_score (0-100) to Intervals.icu sleepQuality (1-4).

    Intervals.icu uses an inverted 1-4 scale:
      1 = Excellent (score >= 90)
      2 = Good      (score >= 75)
      3 = Average   (score >= 60)
      4 = Poor      (score < 60)
    """
    if score is None:
        return None
    if score >= 90:
        return 1
    if score >= 75:
        return 2
    if score >= 60:
        return 3
    return 4


def format_sleep_quality(value: int | None) -> str:
    """Format sleepQuality value (1-4 Intervals.icu scale).

    Args:
        value: Sleep quality value 1-4 or None (1=Excellent, 4=Poor).

    Returns:
        Formatted label string.
    """
    if value is None:
        return "_Non renseigné_"

    label = SLEEP_QUALITY_LABELS.get(value)
    if label is None:
        return f"_Valeur inconnue: {value}_"

    return label
