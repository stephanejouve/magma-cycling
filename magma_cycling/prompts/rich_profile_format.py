"""Format the 6 BT-017 rich profile fields into a markdown section for AI prompts.

The rich profile fields (hrv_baseline, injury_history, macro_plan,
nutrition_strategy, sleep_baseline, availability_pattern) are stored in the
athlete YAML and dispatched via ``update-athlete-profile``. This module reads
them via the ``profile_rich`` loaders and emits a compact markdown digest for
injection into the Coach AI system prompt.

Migration-noop: when all 6 fields are missing (or invalid), an empty string is
returned — no section noise in the prompt for athletes who have not populated
the rich profile yet.
"""

from __future__ import annotations

import logging
from pathlib import Path

from magma_cycling.config.profile_rich import (
    AvailabilityPattern,
    HrvBaseline,
    InjuryHistory,
    MacroPlan,
    NutritionStrategy,
    SleepBaseline,
    load_availability_pattern,
    load_hrv_baseline,
    load_injury_history,
    load_macro_plan,
    load_nutrition_strategy,
    load_sleep_baseline,
)

logger = logging.getLogger(__name__)


def format_rich_profile(path: Path | None = None) -> str:
    """Emit a markdown section for the 6 BT-017 rich profile fields.

    Args:
        path: Override for the athlete YAML path. When ``None``, delegates to
            the ``profile_rich`` loaders (which resolve via
            ``resolve_athlete_yaml_path``).

    Returns:
        A multi-line markdown string starting with ``## Contexte
        physiologique enrichi``, or an empty string when all 6 fields are
        missing (migration-noop).
    """
    hrv = _safe_load(load_hrv_baseline, path)
    injuries = _safe_load(load_injury_history, path)
    macro = _safe_load(load_macro_plan, path)
    nutrition = _safe_load(load_nutrition_strategy, path)
    sleep = _safe_load(load_sleep_baseline, path)
    availability = _safe_load(load_availability_pattern, path)

    sections: list[str] = []
    if hrv is not None:
        sections.extend(_format_hrv(hrv))
    if injuries is not None:
        sections.extend(_format_injuries(injuries))
    if macro is not None:
        sections.extend(_format_macro(macro))
    if nutrition is not None:
        sections.extend(_format_nutrition(nutrition))
    if sleep is not None:
        sections.extend(_format_sleep(sleep))
    if availability is not None:
        sections.extend(_format_availability(availability))

    if not sections:
        return ""

    return "\n".join(["## Contexte physiologique enrichi", *sections])


def _safe_load(loader, path):
    try:
        return loader(path) if path is not None else loader()
    except Exception:
        logger.debug("rich profile loader %s failed", loader.__name__)
        return None


def _format_hrv(hrv: HrvBaseline) -> list[str]:
    lines = [
        "",
        "### HRV baseline (rMSSD)",
        f"- Range baseline : {_num(hrv.rmssd_min)}-{_num(hrv.rmssd_max)} ms",
    ]
    if hrv.rmssd_peak is not None:
        lines.append(f"- Plafond recuperation : {_num(hrv.rmssd_peak)} ms")
    lines.append(f"- Seuil alerte fatigue : < {_num(hrv.alert_threshold)} ms")
    if hrv.recovery_pattern:
        lines.append(f"- Pattern recuperation : {hrv.recovery_pattern}")
    if hrv.anomalies:
        lines.append("- Anomalies documentees :")
        for a in hrv.anomalies:
            excl = " [exclu stats]" if a.exclude_from_stats else ""
            lines.append(f"  - {a.date.isoformat()} : {_num(a.value)} ms — {a.context}{excl}")
    return lines


def _format_injuries(inj: InjuryHistory) -> list[str]:
    if not inj.active and not inj.watch_points:
        return []
    lines = ["", "### Historique blessures"]
    if inj.active:
        lines.append("- Blessures actives :")
        for i in inj.active:
            parts = [f"{i.area} ({i.status})"]
            if i.onset_date:
                parts.append(f"depuis {i.onset_date.isoformat()}")
            if i.last_followup:
                parts.append(f"suivi {i.last_followup.isoformat()}")
            if i.notes:
                parts.append(i.notes)
            lines.append(f"  - {' — '.join(parts)}")
    if inj.watch_points:
        lines.append("- Points de vigilance permanents :")
        for w in inj.watch_points:
            lines.append(f"  - {w}")
    return lines


def _format_macro(macro: MacroPlan) -> list[str]:
    if not macro.weekly_tss and macro.ctl_target is None and macro.peak_event is None:
        return []
    lines = ["", "### Plan macro"]
    if macro.ctl_target is not None:
        lines.append(f"- CTL cible (macrocycle) : {_num(macro.ctl_target)}")
    if macro.peak_event is not None:
        pe = macro.peak_event
        lines.append(f"- Evenement A : {pe.name} ({pe.date.isoformat()})")
        if pe.ctl_target is not None:
            lines.append(f"  - CTL cible J-0 : {_num(pe.ctl_target)}")
        if pe.tsb_target_min is not None and pe.tsb_target_max is not None:
            lines.append(f"  - TSB cible J-0 : {pe.tsb_target_min:+.1f} a {pe.tsb_target_max:+.1f}")
        if pe.strategy:
            lines.append(f"  - Strategie : {pe.strategy}")
    if macro.weekly_tss:
        lines.append("- TSS hebdo cible :")
        for w in macro.weekly_tss:
            note = f" — {w.notes}" if w.notes else ""
            lines.append(f"  - {w.week_label} : {w.tss_target} TSS{note}")
    return lines


def _format_nutrition(n: NutritionStrategy) -> list[str]:
    lines = [
        "",
        "### Strategie nutrition (evenement)",
        f"- Glucides / h : {n.carbs_per_hour_min}-{n.carbs_per_hour_max} g",
    ]
    if n.known_issues:
        lines.append("- Points de vigilance :")
        for issue in n.known_issues:
            lines.append(f"  - {issue}")
    return lines


def _format_sleep(s: SleepBaseline) -> list[str]:
    hrs, mins = divmod(s.avg_duration_minutes, 60)
    lines = [
        "",
        "### Sommeil baseline",
        f"- Duree moyenne : {hrs}h{mins:02d}",
        f"- Deficit nocturne : {s.deficit_per_night_minutes} min",
    ]
    if s.bedtime_target:
        lines.append(f"- Heure coucher cible : {s.bedtime_target}")
    return lines


def _format_availability(a: AvailabilityPattern) -> list[str]:
    if not a.weekly_slots and not a.notes:
        return []
    lines = ["", "### Disponibilites hebdo"]
    if a.weekly_slots:
        for s in a.weekly_slots:
            parts = [f"{s.day_of_week.upper()} {s.time_window} : {s.activity}"]
            if s.typical_tss:
                parts.append(f"~{s.typical_tss} TSS")
            lines.append(f"- {' — '.join(parts)}")
    if a.notes:
        lines.append(f"- Notes : {a.notes}")
    return lines


def _num(x: float) -> str:
    """Render a float trimming a trailing .0 (rMSSD ranges look nicer as ints)."""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)
