"""Context loading methods for WeeklyPlanner."""

import json
import re
import sys
from pathlib import Path
from typing import Any


class ContextLoadingMixin:
    """File I/O for reference files, previous week bilan, and workout analyses."""

    def _fetch_actual_tss(self, plan) -> dict[str, int] | None:
        """Fetch actual TSS from Intervals.icu for completed sessions.

        Returns a dict mapping session_id to actual TSS, or None if unavailable.
        Uses 2 API calls: get_activities + get_events for the whole week.
        """
        try:
            from magma_cycling.config import create_intervals_client

            client = create_intervals_client()

            start = str(plan.start_date)
            end = str(plan.end_date)

            activities = client.get_activities(oldest=start, newest=end)
            events = client.get_events(oldest=start, newest=end)

            # activity_id → icu_training_load
            activity_tss = {}
            for a in activities:
                aid = a.get("id")
                tss = a.get("icu_training_load")
                if aid and tss is not None:
                    activity_tss[aid] = round(tss)

            # event_id → paired_activity_id
            event_to_activity = {}
            for e in events:
                eid = e.get("id")
                paid = e.get("paired_activity_id")
                if eid and paid:
                    event_to_activity[eid] = paid

            # session_id → actual TSS
            result = {}
            for s in plan.planned_sessions:
                if s.status == "completed" and s.intervals_id:
                    activity_id = event_to_activity.get(s.intervals_id)
                    if activity_id and activity_id in activity_tss:
                        result[s.session_id] = activity_tss[activity_id]

            return result if result else None
        except Exception:
            return None

    def _compute_live_bilan(self, week_id: str) -> str | None:
        """Compute bilan from Control Tower when bilan file is stale or missing."""
        try:
            from magma_cycling.planning.control_tower import planning_tower

            plan = planning_tower.read_week(week_id)

            completed = [s for s in plan.planned_sessions if s.status == "completed"]
            active = [
                s
                for s in plan.planned_sessions
                if s.status not in ("cancelled", "rest_day", "skipped")
            ]

            if not completed:
                return None

            # Try to enrich with actual TSS from Intervals.icu
            actual_tss_map = self._fetch_actual_tss(plan)
            has_actual = actual_tss_map is not None

            if has_actual:
                total_tss = sum(
                    actual_tss_map.get(s.session_id, s.tss_planned or 0) for s in completed
                )
                tss_label = "TSS total réel"
                tss_source = "live + Intervals.icu"
            else:
                total_tss = sum(s.tss_planned or 0 for s in completed)
                tss_label = "TSS total planifié"
                tss_source = "live"

            compliance = (len(completed) / len(active) * 100) if active else 0

            lines = [
                f"# Bilan Final {week_id} (données planning {tss_source})\n",
                "## Objectifs vs Réalisé\n",
                f"- **Compliance :** {compliance:.1f}%",
                f"- **Séances planifiées :** {len(active)}",
                f"- **Séances exécutées :** {len(completed)}\n",
                "## Métriques Clés\n",
                f"- **{tss_label} :** {total_tss}",
                f"- **TSS moyen :** {total_tss / len(completed):.1f}\n",
                "## Séances Complétées\n",
            ]

            for s in completed:
                if has_actual and s.session_id in actual_tss_map:
                    tss_val = actual_tss_map[s.session_id]
                    tss_display = f"TSS réel: {tss_val}"
                else:
                    tss_display = f"TSS planifié: {s.tss_planned or 0}"
                lines.append(
                    f"- {s.session_id} ({s.session_type}) — {s.name} — "
                    f"{tss_display}, {s.duration_min or 0}min"
                )

            return "\n".join(lines)
        except Exception:
            return None

    def load_previous_week_bilan(self) -> str:
        """Load le bilan de la semaine précédente."""
        print("\n📄 Chargement bilan semaine précédente...", file=sys.stderr)

        prev_week = self._previous_week_number()
        prev_week_dir = self.weekly_reports_dir / prev_week

        # Use lowercase week ID for filename (standard depuis workflow_weekly)
        bilan_file = prev_week_dir / f"bilan_final_{prev_week.lower()}.md"
        transition_file = prev_week_dir / f"transition_{prev_week.lower()}.md"

        content_parts = []

        # Load bilan_final
        if bilan_file.exists():
            bilan_content = bilan_file.read_text(encoding="utf-8")

            # Detect stale bilan: compliance 0% but completed sessions exist
            if "Compliance : 0.0%" in bilan_content or "Séances exécutées : 0" in bilan_content:
                live_bilan = self._compute_live_bilan(prev_week)
                if live_bilan:
                    print(
                        f"  ⚠️  Bilan {prev_week} stale (0%), " "enrichi avec données planning live",
                        file=sys.stderr,
                    )
                    bilan_content = live_bilan

            content_parts.append(f"## Bilan Final {prev_week}\n\n{bilan_content}")
            print(f"  ✅ Bilan {prev_week} chargé ({len(bilan_content)} chars)", file=sys.stderr)
        else:
            # Fichier absent — tenter un bilan live
            live_bilan = self._compute_live_bilan(prev_week)
            if live_bilan:
                print(
                    f"  ℹ️  Bilan {prev_week} absent, généré depuis planning",
                    file=sys.stderr,
                )
                content_parts.append(f"## Bilan Final {prev_week}\n\n{live_bilan}")
            else:
                print(f"  ⚠️ Bilan {prev_week} non trouvé : {bilan_file}", file=sys.stderr)
                content_parts.append(f"[Bilan {prev_week} non disponible]")

        # Load transition (contains TSS, TSB, recommendations for next week)
        if transition_file.exists():
            transition_content = transition_file.read_text(encoding="utf-8")
            content_parts.append(f"\n\n{transition_content}")
            print(
                f"  ✅ Transition {prev_week} chargée ({len(transition_content)} chars)",
                file=sys.stderr,
            )
        else:
            print(f"  ⚠️ Transition {prev_week} non trouvée : {transition_file}", file=sys.stderr)
            content_parts.append(f"\n\n[Transition {prev_week} non disponible]")

        return "\n".join(content_parts)

    def load_context_files(self) -> dict[str, str]:
        """Load les fichiers de contexte."""
        print("\n📚 Chargement fichiers contexte...", file=sys.stderr)

        context = {}

        files_to_load = {
            "project_prompt": self.references_dir / "project_prompt_v2_1_revised.md",
            "cycling_concepts": self.references_dir / "cycling_training_concepts.md",
            "documentation": self.project_root / "Documentation_Complète_du_Suivi_v1_5.md",
            "planning_preferences": self.project_root / "project-docs" / "PLANNING_PREFERENCES.md",
        }

        for key, filepath in files_to_load.items():
            try:
                if filepath.exists():
                    context[key] = filepath.read_text(encoding="utf-8")
                    print(f"  ✅ {filepath.name}", file=sys.stderr)
                else:
                    print(f"  ⚠️ Non trouvé : {filepath.name}", file=sys.stderr)
                    context[key] = f"[{filepath.name} non trouvé]"
            except Exception as e:
                print(f"  ⚠️ Erreur {filepath.name} : {e}", file=sys.stderr)
                context[key] = f"[Erreur lecture {filepath.name}]"

        # Charger protocoles si disponibles
        protocols_dir = self.references_dir / "protocols"
        if protocols_dir.exists():
            protocols = []
            for protocol_file in protocols_dir.glob("*.md"):
                try:
                    protocols.append(protocol_file.read_text(encoding="utf-8"))
                    print(f"  ✅ {protocol_file.name}", file=sys.stderr)
                except Exception as e:
                    print(f"  ⚠️ Erreur {protocol_file.name} : {e}", file=sys.stderr)

            if protocols:
                context["protocols"] = "\n\n---\n\n".join(protocols)

        # Charger intelligence.json (recommandations PID et adaptations)
        intelligence_file = Path.home() / "data" / "intelligence.json"
        try:
            if intelligence_file.exists():
                intelligence_data = json.loads(intelligence_file.read_text(encoding="utf-8"))
                context["intelligence"] = _summarize_intelligence(intelligence_data)
                print("  ✅ intelligence.json (résumé)", file=sys.stderr)
            else:
                print("  ⚠️ Non trouvé : intelligence.json", file=sys.stderr)
                context["intelligence"] = "[Aucune recommandation d'adaptation disponible]"
        except Exception as e:
            print(f"  ⚠️ Erreur intelligence.json : {e}", file=sys.stderr)
            context["intelligence"] = f"[Erreur lecture intelligence.json: {e}]"

        return context

    def load_previous_week_workouts(self) -> str:
        """Load detailed workout analyses from previous week.

        Extracts workout analyses from workouts-history.md for the previous week
        to provide detailed feedback on execution, decoupling, adherence, and
        athlete feedback for better planning decisions.

        Returns:
            Formatted section with detailed workout analyses or empty string if unavailable

        Examples:
            >>> planner = WeeklyPlanner("S082", datetime(2026, 2, 24), Path("."))
            >>> analyses = planner.load_previous_week_workouts()
            >>> "S081-01" in analyses  # Previous week workouts
            True
        """
        print("\n📝 Chargement analyses détaillées semaine précédente...", file=sys.stderr)

        try:
            # Get data repo path
            from magma_cycling.config import get_data_config

            config = get_data_config()
            history_file = config.data_repo_path / "workouts-history.md"

            if not history_file.exists():
                print(f"  ⚠️ workouts-history.md non trouvé : {history_file}", file=sys.stderr)
                return ""

            content = history_file.read_text(encoding="utf-8")

            # Extract previous week workouts
            prev_week = self._previous_week_number()
            prev_week_pattern = f"{prev_week}-"  # e.g., "S081-"

            # Split by ### headers (not ####) using regex lookahead
            entries = re.split(r"(?:^|\n)(?=### )", content)

            # Filter workouts from previous week
            prev_week_workouts = []
            for entry in entries:
                entry = entry.strip()
                if entry and prev_week_pattern in entry[:80]:
                    prev_week_workouts.append(entry)

            if not prev_week_workouts:
                print(f"  ℹ️  Aucune analyse trouvée pour {prev_week}", file=sys.stderr)
                return ""

            # Format section
            section = f"\n## 📊 Analyses Détaillées Semaine {prev_week}\n\n"
            section += (
                f"**{len(prev_week_workouts)} séance(s) analysée(s)** - "
                f"Retour d'expérience pour planification {self.week_number}\n\n"
            )
            section += "---\n\n"
            section += "\n\n".join(prev_week_workouts[:7])  # Max 7 workouts (1 week)

            print(
                f"  ✅ {len(prev_week_workouts)} analyse(s) chargée(s) pour {prev_week}",
                file=sys.stderr,
            )
            return section

        except Exception as e:
            print(f"  ⚠️ Erreur chargement analyses : {e}", file=sys.stderr)
            return ""


def _summarize_intelligence(data: dict[str, Any]) -> str:
    """Summarize intelligence data for prompt injection.

    Filters and compresses intelligence to reduce prompt size:
    - Learnings: keep confidence >= medium, deduplicate evidence, max 5 items
    - Adaptations: keep only PROPOSED, 1 per protocol_name (most recent)
    - Patterns: pass through as-is
    """
    sections = []

    # --- Learnings: confidence >= medium, max 5 evidence ---
    learnings = data.get("learnings", {})
    kept_learnings = []
    for lid, learning in learnings.items():
        conf = learning.get("confidence", "low")
        if conf in ("medium", "high", "validated"):
            evidence = learning.get("evidence", [])
            unique_evidence = list(dict.fromkeys(evidence))  # deduplicate, preserve order
            total = len(unique_evidence)
            summary = {
                "id": lid,
                "category": learning.get("category"),
                "description": learning.get("description"),
                "confidence": conf,
                "impact": learning.get("impact"),
                "evidence": unique_evidence[:5],
            }
            if total > 5:
                summary["evidence_total"] = total
            kept_learnings.append(summary)

    if kept_learnings:
        sections.append(f"## Learnings ({len(kept_learnings)} sur {len(learnings)})\n")
        sections.append(json.dumps(kept_learnings, indent=2, ensure_ascii=False))

    # --- Adaptations: PROPOSED only, 1 per protocol_name (most recent) ---
    adaptations = data.get("adaptations", {})
    best_by_protocol: dict[str, tuple[int, str, dict]] = {}
    for aid, adapt in adaptations.items():
        if adapt.get("status") != "PROPOSED":
            continue
        protocol = adapt.get("protocol_name", "")
        # Extract timestamp from ID (last segment)
        try:
            ts = int(aid.rsplit("_", 1)[-1])
        except (ValueError, IndexError):
            ts = 0
        if protocol not in best_by_protocol or ts > best_by_protocol[protocol][0]:
            best_by_protocol[protocol] = (ts, aid, adapt)

    if best_by_protocol:
        kept_adaptations = []
        for _ts, aid, adapt in best_by_protocol.values():
            kept_adaptations.append(
                {
                    "id": aid,
                    "protocol_name": adapt.get("protocol_name"),
                    "adaptation_type": adapt.get("adaptation_type"),
                    "proposed_rule": adapt.get("proposed_rule"),
                    "justification": adapt.get("justification"),
                    "confidence": adapt.get("confidence"),
                }
            )
        sections.append(
            f"\n## Adaptations PROPOSED ({len(kept_adaptations)} sur {len(adaptations)})\n"
        )
        sections.append(json.dumps(kept_adaptations, indent=2, ensure_ascii=False))

    # --- Patterns: pass through ---
    patterns = data.get("patterns", {})
    if patterns:
        sections.append(f"\n## Patterns ({len(patterns)})\n")
        sections.append(json.dumps(list(patterns.values()), indent=2, ensure_ascii=False))

    if not sections:
        return "[Aucune recommandation d'adaptation disponible]"

    return "\n".join(sections)
