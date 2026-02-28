"""History insertion methods for WorkflowCoach."""

import logging
import re
import subprocess
import sys

from magma_cycling.core.timeline_injector import TimelineInjector
from magma_cycling.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class HistoryMixin:
    """Markdown preview, clipboard, export, session type detection, and history insertion."""

    def _preview_markdowns(self, markdowns: list):
        """Affiche preview des markdowns générés.

        Args:
            markdowns: Liste de tuples (date, markdown_text).
        """
        print("\n" + "=" * 70)

        print("👁️  PREVIEW MARKDOWNS GÉNÉRÉS")
        print("=" * 70)

        for i, (date, markdown) in enumerate(markdowns, 1):
            lines = markdown.split("\n")
            chars = len(markdown)
            title = lines[0] if lines else "Sans titre"

            print(f"\n📄 Markdown {i}/{len(markdowns)}")
            print(f"   Date    : {date}")
            print(f"   Titre   : {title}")
            print(f"   Lignes  : {len(lines)}")
            print(f"   Chars   : {chars}")
            print("\n   Début :")
            for line in lines[:10]:
                print(f"   {line}")
            if len(lines) > 10:
                print(f"   ... ({len(lines) - 10} lignes suivantes)")

        print("\n" + "=" * 70)

    def _copy_to_clipboard(self, markdowns: list) -> bool:
        """Copy markdowns dans clipboard macOS.

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon.
        """
        # Combiner tous les markdowns

        combined = "\n\n".join(markdown for _, markdown in markdowns)

        try:
            # Copier via pbcopy (macOS)
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.communicate(input=combined.encode("utf-8"))

            if process.returncode == 0:
                print(f"\n✅ {len(markdowns)} markdowns copiés dans le presse-papier")
                print(f"   Total : {len(combined)} caractères")
                return True
            else:
                print("\n❌ Erreur lors de la copie")
                return False

        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            return False

    def _export_markdowns(self, markdowns: list, week_id: str) -> bool:
        """Export markdowns vers fichier.

        Args:
            markdowns: Liste de tuples (date, markdown_text)
            week_id: ID semaine (ex: S070)

        Returns:
            True si succès, False sinon.
        """
        from datetime import datetime

        from magma_cycling.config import get_data_config

        config = get_data_config()

        output_dir = config.week_planning_dir
        output_file = output_dir / f"special_sessions_{week_id}.md"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# Sessions Spéciales - Semaine {week_id}\n\n")
                f.write(f"Généré le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                for _date, markdown in markdowns:
                    f.write(markdown)
                    f.write("\n\n")

            print(f"\n✅ Export réussi : {output_file}")
            print(f"   {len(markdowns)} sessions documentées")
            return True

        except Exception as e:
            print(f"\n❌ Erreur export : {e}")
            return False

    def _detect_session_type_from_markdown(self, markdown: str) -> str | None:
        """Détecter type de session depuis markdown.

        Args:
            markdown: Texte markdown de la session

        Returns:
            str: Type session ("rest", "cancelled", "skipped") ou None si non détecté
        """
        markdown_lower = markdown.lower()

        # Patterns pour repos
        if any(pattern in markdown_lower for pattern in ["-rec-", "repos", "recovery", "rest day"]):
            return "rest"

        # Patterns pour annulations
        if any(pattern in markdown_lower for pattern in ["annul", "cancelled", "cancel"]):
            return "cancelled"

        # Patterns pour sautées
        if any(pattern in markdown_lower for pattern in ["saut", "skipped", "skip"]):
            return "skipped"

        return None

    def _insert_to_history(self, markdowns: list) -> bool:
        """Insère markdowns dans workouts-history.md.

        Args:
            markdowns: Liste de tuples (date, markdown_text)

        Returns:
            True si succès, False sinon.
        """
        # Always use data repo config (never fallback to code repo)

        if self.config:
            history_file = self.config.workouts_history_path
        else:
            from magma_cycling.config import get_data_config

            history_file = get_data_config().workouts_history_path

        if not history_file.exists():
            print(f"\n❌ Fichier introuvable : {history_file}")
            return False

        try:
            # Phase 4: Insertion chronologique intelligente avec TimelineInjector
            injector = TimelineInjector(history_file=history_file, check_duplicates=True)

            injection_results = []
            for date, markdown in markdowns:
                # Extraire date du markdown (format: YYYY-MM-DD)
                from datetime import datetime

                workout_date = datetime.strptime(date, "%Y-%m-%d").date()

                result = injector.inject_chronologically(
                    workout_entry=markdown.strip(), workout_date=workout_date
                )
                injection_results.append((date, result))

                if result.success:
                    print(f"   ✓ {date} inséré ligne {result.line_number}")
                elif result.duplicate_found:
                    print(f"   ⚠️  {date} déjà présent (duplicate ignoré)")
                else:
                    print(f"   ❌ {date} erreur: {result.error}")

            # Compter succès
            success_count = sum(1 for _, r in injection_results if r.success)
            duplicate_count = sum(1 for _, r in injection_results if r.duplicate_found)

            print(f"\n✅ Insertion chronologique réussie dans {history_file}")
            print(f"   {success_count} sessions insérées")
            if duplicate_count > 0:
                print(f"   {duplicate_count} duplicates ignorés")

            # PHASE 4: Marquer sessions spéciales comme documentées
            state = WorkflowState(project_root=self.project_root)

            for date, markdown in markdowns:
                # Extraire session_id depuis markdown (format: "### S072-07-REC-...")
                match = re.search(r"###\s+(S\d+-\d+)", markdown)
                if match:
                    session_id = match.group(1)

                    # Détecter type de session depuis markdown
                    session_type = self._detect_session_type_from_markdown(markdown)

                    if session_type:
                        try:
                            state.mark_special_session_documented(session_id, session_type, date)
                            print(
                                f"   ✓ {session_type.capitalize()} {session_id} marquée documentée"
                            )
                        except Exception as e:
                            print(f"   ⚠️  Erreur marking {session_id}: {e}")

            return True

        except Exception as e:
            print(f"\n❌ Erreur insertion : {e}")
            return False

    def step_6_insert_analysis(self):
        """Étape 6 : Insérer l'analyse dans les logs."""
        self.clear_screen()

        # Afficher le nom de la séance dans le header
        subtitle = "Étape 6/7 : Mise à jour workouts-history.md"
        if self.activity_name:
            subtitle += f"\n🚴 {self.activity_name}"

        self.print_header("💾 Insertion dans les Logs", subtitle)

        print("Insertion de l'analyse depuis le presse-papier...")
        print()
        print("⏱️  Temps estimé : 5 secondes")
        self.print_separator()

        # For API providers, write analysis to clipboard first
        if self.current_provider != "clipboard" and hasattr(self, "analysis_result"):
            try:
                subprocess.run(["pbcopy"], input=self.analysis_result.encode("utf-8"), check=True)
                logger.info(
                    f"Analysis written to clipboard for insert_analysis.py ({len(self.analysis_result)} chars)"
                )
            except Exception as e:
                logger.error(f"Failed to write analysis to clipboard: {e}")
                print(f"❌ Erreur écriture clipboard : {e}")
                sys.exit(1)

        # Lancer le script d'insertion - Module import au lieu de Poetry entrypoint
        cmd = [sys.executable, "-m", "magma_cycling.insert_analysis"]
        if self.auto_mode:
            cmd.append("--yes")
        result = subprocess.run(cmd)

        if result.returncode != 0:
            print()
            print("❌ Erreur lors de l'insertion de l'analyse.")
            print("   Vérifier le format et réessayer.")
            sys.exit(1)

        print()
        print("✅ Analyse insérée dans logs/workouts-history.md !")

        # Mark activity as analyzed ONLY after successful insertion
        if self.activity_id:
            from magma_cycling.workflow_state import WorkflowState

            state = WorkflowState(self.project_root)
            # Extract date from activity_data if available
            if hasattr(self, "activity_data") and self.activity_data:
                activity_date = self.activity_data.get("start_date_local", "")[:10]  # YYYY-MM-DD
            else:
                from datetime import datetime

                activity_date = datetime.now().strftime("%Y-%m-%d")

            state.mark_analyzed(self.activity_id, activity_date)
            print(f"✅ Activité {self.activity_id} marquée comme analysée")

            # Post analysis to Intervals.icu as a note
            print()
            print("📤 Publication de l'analyse sur Intervals.icu...")
            success = self._post_analysis_to_intervals()
            if success:
                print(f"✅ Analyse publiée sur Intervals.icu (activité {self.activity_id})")
            else:
                print(
                    "⚠️  Échec publication sur Intervals.icu (analyse toujours dans workouts-history.md)"
                )

        self.wait_user()
