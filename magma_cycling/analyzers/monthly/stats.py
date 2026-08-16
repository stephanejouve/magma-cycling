"""Statistical aggregation mixin for MonthlyAnalyzer."""

from collections import defaultdict
from typing import Any

from magma_cycling.analyzers.tss_target import compute_active_tss_target


class StatsMixin:
    """Monthly statistical aggregation."""

    def aggregate_statistics(
        self, weekly_data: list[dict], actual_tss_map: dict | None = None
    ) -> dict:
        """Aggregate monthly statistics from weekly data.

        Args:
            weekly_data: List of weekly planning dicts.
            actual_tss_map: Optional mapping {intervals_id: actual_tss} from
                Intervals.icu. When provided, completed/modified sessions with
                an intervals_id use real TSS instead of tss_planned.

        Returns:
            Dictionary with monthly metrics. BT-039 : exposition de 2 cibles
            distinctes — ``tss_target_total`` (cible initiale, intention) et
            ``tss_target_active_total`` (cible active post-annulations, référence
            d'adhérence). ``tss_achievement_rate`` calculé sur la cible active
            (voie A validée Coach AI). Marqueur ``tss_source_map`` liste les
            session_id dont le TSS provient du fallback ``planned`` (pas de
            match Intervals.icu).
        """
        stats: dict[str, Any] = {
            "total_weeks": len(weekly_data),
            "total_sessions": 0,
            "completed": 0,
            "skipped": 0,
            "cancelled": 0,
            "modified": 0,
            "rest_days": 0,
            "tss_realized": 0,
            "tss_target_total": 0,
            # BT-039 : cible active (post-annulations) — voie A pour adhérence
            "tss_target_active_total": 0,
            # BT-039 marqueur origine TSS réalisé — liste des session_id ayant
            # fallback tss_planned (pas d'intervals_id ou pas de match map)
            "tss_source_map": {"intervals": [], "planned_fallback": []},
            "sessions_by_type": defaultdict(int),
            "sessions_by_status": defaultdict(int),
            "tss_by_week": [],
            "weekly_details": [],
        }

        for week in sorted(weekly_data, key=lambda w: w["start_date"]):
            week_active_target = compute_active_tss_target(week)
            week_stats = {
                "week_id": week["week_id"],
                "start_date": week["start_date"],
                "end_date": week["end_date"],
                "tss_target": week.get("tss_target", 0),
                # BT-039 : cible active côté par côté (référence adhérence)
                "tss_target_active": week_active_target,
                "tss_actual": 0,
                "sessions": len(week.get("planned_sessions", [])),
            }

            stats["tss_target_total"] += week.get("tss_target", 0)
            stats["tss_target_active_total"] += week_active_target

            for session in week.get("planned_sessions", []):
                stats["total_sessions"] += 1
                status = session.get("status", "unknown")
                session_type = session.get("type", "unknown")

                tss_planned = session.get("tss_planned", 0)
                intervals_id = session.get("intervals_id")
                # Use actual TSS for completed/modified sessions when available
                if intervals_id and actual_tss_map and f"i{intervals_id}" in actual_tss_map:
                    tss = actual_tss_map[f"i{intervals_id}"]
                    tss_source = "intervals"
                else:
                    tss = tss_planned
                    tss_source = "planned_fallback"

                # BT-039 : ne tracer l'origine QUE pour les sessions dont
                # le TSS est effectivement comptabilisé dans le réalisé
                # (completed, modified). Les autres n'entrent pas dans le
                # calcul → pas de bruit dans la légende.
                if status in ("completed", "modified"):
                    session_id = session.get("session_id", "?")
                    stats["tss_source_map"][tss_source].append(session_id)

                # Count by status
                stats["sessions_by_status"][status] += 1

                if status == "completed":
                    stats["completed"] += 1
                    stats["tss_realized"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "skipped":
                    stats["skipped"] += 1
                elif status == "cancelled":
                    stats["cancelled"] += 1
                elif status == "modified":
                    stats["modified"] += 1
                    stats["tss_realized"] += tss
                    week_stats["tss_actual"] += tss
                elif status == "rest_day":
                    stats["rest_days"] += 1

                # Count by type (exclude rest days)
                if status != "rest_day":
                    stats["sessions_by_type"][session_type] += 1

            stats["tss_by_week"].append(week_stats)
            stats["weekly_details"].append(week_stats)

        # Calculate adherence rate
        total_planned = (
            stats["completed"] + stats["skipped"] + stats["cancelled"] + stats["modified"]
        )
        if total_planned > 0:
            stats["adherence_rate"] = (stats["completed"] + stats["modified"]) / total_planned * 100
        else:
            stats["adherence_rate"] = 0

        # BT-039 : TSS achievement rate calculé sur cible ACTIVE (voie A).
        # Protection division par zéro : semaine 100 % annulée → active=0 →
        # taux d'adhérence non-défini (None), caller doit afficher « — ».
        if stats["tss_target_active_total"] > 0:
            stats["tss_achievement_rate"] = (
                stats["tss_realized"] / stats["tss_target_active_total"] * 100
            )
        else:
            stats["tss_achievement_rate"] = None

        return stats
