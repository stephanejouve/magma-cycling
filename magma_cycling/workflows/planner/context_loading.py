"""Context loading methods for WeeklyPlanner."""

import json
import sys
from pathlib import Path


class ContextLoadingMixin:
    """File I/O for reference files, previous week bilan, and workout analyses."""

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
            content_parts.append(f"## Bilan Final {prev_week}\n\n{bilan_content}")
            print(f"  ✅ Bilan {prev_week} chargé ({len(bilan_content)} chars)", file=sys.stderr)
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
                # Format as readable text for AI
                context["intelligence"] = json.dumps(
                    intelligence_data, indent=2, ensure_ascii=False
                )
                print("  ✅ intelligence.json", file=sys.stderr)
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

            # Split by ### headers (each workout)
            sections = content.split("###")

            # Filter workouts from previous week
            prev_week_workouts = []
            for section in sections:
                if prev_week_pattern in section[:50]:  # Check in first 50 chars (title area)
                    # Keep only up to next ### or end
                    prev_week_workouts.append("###" + section)

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
