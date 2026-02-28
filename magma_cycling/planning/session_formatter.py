"""
Session formatting utilities for AI prompts.

Extracted from workflow_coach.py to improve testability and reusability.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""


def format_remaining_sessions_compact(remaining_sessions: list[dict]) -> str:
    """Format compact planning pour prompt AI (cible ~150 tokens).

    Args:
        remaining_sessions: Liste de sessions futures avec structure:
            - date: Date session (YYYY-MM-DD)
            - session_id: ID session (ex: S081-05)
            - name: Nom workout (ex: EnduranceDouce)
            - type: Type workout (END, INT, TEC, etc.)
            - version: Version (ex: V001)
            - tss_planned: TSS prévu
            - status: Statut (planned, rest_day, etc.)

    Returns:
        str: Planning formaté pour inclusion dans prompt, ou chaîne vide si aucune session

    Examples:
        >>> sessions = [
        ...     {
        ...         "date": "2026-03-05",
        ...         "session_id": "S081-05",
        ...         "name": "EnduranceDouce",
        ...         "type": "END",
        ...         "version": "V001",
        ...         "tss_planned": 50,
        ...         "status": "planned"
        ...     }
        ... ]
        >>> output = format_remaining_sessions_compact(sessions)
        >>> "PLANNING RESTANT (1 séances)" in output
        True
        >>> "2026-03-05: S081-05-END-EnduranceDouce-V001 (50 TSS)" in output
        True

        >>> # Rest day
        >>> sessions = [
        ...     {
        ...         "date": "2026-03-06",
        ...         "session_id": "S081-06",
        ...         "name": "Repos",
        ...         "type": "REST",
        ...         "status": "rest_day"
        ...     }
        ... ]
        >>> output = format_remaining_sessions_compact(sessions)
        >>> "2026-03-06: REPOS" in output
        True

        >>> # Empty list
        >>> format_remaining_sessions_compact([])
        ''
    """
    if not remaining_sessions:
        return ""

    lines = [f"\n## PLANNING RESTANT ({len(remaining_sessions)} séances)\n"]

    for session in remaining_sessions:
        date = session["date"]
        session_id = session["session_id"]
        name = session["name"]
        workout_type = session["type"]
        tss = session.get("tss_planned", 0)

        # Construct workout code
        workout_code = f"{session_id}-{workout_type}-{name}-{session.get('version', 'V001')}"

        if session.get("status") == "rest_day":
            lines.append(f"{date}: REPOS")
        else:
            lines.append(f"{date}: {workout_code} ({tss} TSS)")

    return "\n".join(lines)
