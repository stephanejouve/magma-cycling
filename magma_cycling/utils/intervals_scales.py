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
