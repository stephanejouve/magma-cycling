#!/usr/bin/env python3
"""
weekly_analysis.py - Génération analyse hebdomadaire cyclisme (DEPRECATED).

⚠️  DEPRECATED - Ce script est obsolète et sera supprimé dans une version future.

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: E (Eliminate)
    Status: Deprecated
    Priority: P4
    Version: 1.0
    Deprecation Date: 2025-12-26
    Replacement: cyclisme_training_logs.workflows.workflow_weekly

Migration vers le nouveau système (Phase 2 - Weekly Analysis System):
    Ancien (deprecated):
        python3 cyclisme_training_logs/weekly_analysis.py --week-id S073

    Nouveau (recommandé):
        poetry run weekly-analysis --week S073 --start-date 2025-01-06

Avantages du nouveau système:
- Architecture modulaire (WeeklyAggregator → WeeklyAnalyzer → WeeklyWorkflow)
- Extension de DataAggregator base class (Phase 1 infrastructure)
- Tests complets (30+ tests)
- API programmatique en plus du CLI
- Meilleure gestion d'erreurs et validation
- Génération automatisée sans clipboard manuel

Documentation:
    cyclisme_training_logs/workflows/workflow_weekly.py
    cyclisme_training_logs/analyzers/weekly_aggregator.py
    cyclisme_training_logs/analyzers/weekly_analyzer.py

Ce script génère automatiquement les 6 fichiers markdown du rapport hebdomadaire :
1. workout_history_sXXX.md - Chronologie complète des séances
2. metrics_evolution_sXXX.md - Évolution des métriques
3. training_learnings_sXXX.md - Découvertes et apprentissages
4. protocol_adaptations_sXXX.md - Ajustements des protocoles
5. transition_sXXX_sXXX.md - Transition vers semaine suivante
6. bilan_final_sXXX.md - Bilan global de la semaine

Usage (DEPRECATED):
    python3 cyclisme_training_logs/weekly_analysis.py --week-id S068
    python3 cyclisme_training_logs/weekly_analysis.py --week-id S068 --start-date 2024-11-18.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Import du client API unifié
from cyclisme_training_logs.api.intervals_client import IntervalsClient


class WeeklyAnalysis:
    """Orchestrateur de l'analyse hebdomadaire."""

    def __init__(self, week_number: str, start_date: str | None = None):
        """
        Args:.

            week_number: Format SXXX (ex: S068)
            start_date: Format YYYY-MM-DD (optionnel, auto si None).
        """
        self.week_number = week_number

        self.week_int = int(week_number[1:])  # Ex: S068 -> 68

        # Calcul des dates
        if start_date:
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            self.start_date = self._calculate_week_start()

        self.end_date = self.start_date + timedelta(days=6)

        # Chemins
        self.project_root = Path(__file__).parent.parent
        self.references_dir = self.project_root / "references"

        # Use data repo config if available
        from cyclisme_training_logs.config import get_data_config

        try:
            config = get_data_config()
            self.logs_dir = config.data_repo_path
            self.output_dir = config.bilans_dir / week_number
        except FileNotFoundError:
            # Fallback to legacy paths
            self.logs_dir = self.project_root / "logs"
            self.output_dir = self.project_root / "logs" / "weekly_reports" / week_number

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API Intervals.icu
        config_path = Path.home() / ".intervals_config.json"
        self.api: IntervalsClient | None
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                self.api = IntervalsClient(
                    athlete_id=config.get("athlete_id"), api_key=config.get("api_key")
                )
        else:
            self.api = None
            print("⚠️  Config Intervals.icu non trouvée (~/.intervals_config.json)")

        # Données collectées
        self.workouts: list[dict[str, Any]] = []
        self.metrics: dict[str, Any] = {}
        self.context_files: dict[str, str] = {}

    def _calculate_week_start(self) -> datetime:
        """Calculate la date de début de la semaine basé sur le numéro.

        Reads reference date from .config.json with multi-season support (no hardcoded dates).
        """
        from cyclisme_training_logs.config import get_week_config

        # Load reference date and offset from config (multi-season aware)
        week_config = get_week_config()
        reference_date, weeks_offset = week_config.get_reference_for_week(self.week_number)

        # Convert date to datetime
        reference_datetime = datetime.combine(reference_date, datetime.min.time())

        return reference_datetime + timedelta(weeks=weeks_offset)

    def _next_week(self) -> str:
        """Calculate le numéro de la semaine suivante."""
        return f"S{self.week_int + 1:03d}"

    def collect_week_workouts(self) -> list[dict]:
        """Extract les séances de la semaine depuis workouts-history.md."""
        history_file = self.logs_dir / "workouts-history.md"

        if not history_file.exists():
            print(f"❌ Fichier {history_file} introuvable")
            return []

        print(f"📖 Lecture de {history_file}...")

        with open(history_file, encoding="utf-8") as f:
            content = f.read()

        # Parser les séances
        workouts = []
        seen = set()  # Pour éviter les doublons

        # Extraire la section "# Historique" (avec support de # ou ##)
        historique_match = re.search(r"#+ Historique.*?\n(.*)", content, re.DOTALL)
        if not historique_match:
            print("   ⚠️  Section 'Historique' non trouvée")
            return []

        historique_content = historique_match.group(1)

        # Extraire toutes les sections ### (séances)
        # Format attendu: ### Nom de la Séance\nDate : JJ/MM/YYYY
        sections = re.split(r"\n### ", historique_content)

        for section in sections[1:]:  # Skip le premier (avant le premier ###)
            # Extraire la date
            date_match = re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})", section)
            if not date_match:
                continue

            date_str = date_match.group(1)
            date = datetime.strptime(date_str, "%d/%m/%Y")

            # Vérifier si la date est dans la plage de la semaine
            if self.start_date <= date <= self.end_date:
                # Extraire le nom de la séance (première ligne)
                name = section.split("\n")[0].strip()

                # Créer une clé unique pour éviter les doublons
                key = f"{date_str}_{name}"

                if key not in seen:
                    seen.add(key)

                    # Extraire toute la section jusqu'au prochain ### ou fin
                    workout = {
                        "name": name,
                        "date": date,
                        "date_str": date_str,
                        "content": "### " + section.strip(),
                    }

                    workouts.append(workout)

        # Trier par date
        workouts.sort(key=lambda x: x["date"])

        print(f"   ✅ {len(workouts)} séance(s) trouvée(s)")
        for w in workouts:
            print(f"      - [{w['date_str']}] {w['name']}")

        return workouts

    def collect_week_metrics(self) -> dict:
        """Collect métriques évolution via API."""
        if not self.api:
            print("⚠️  API non disponible, skip métriques")
            return {}

        print("📊 Collecte des métriques Intervals.icu...")

        try:
            # Dates au format ISO
            start_date_str = self.start_date.strftime("%Y-%m-%d")
            end_date_str = self.end_date.strftime("%Y-%m-%d")

            # Récupérer wellness début et fin
            wellness_data = self.api.get_wellness(oldest=start_date_str, newest=end_date_str)

            if not wellness_data:
                print("   ⚠️  Aucune donnée wellness disponible")
                return self._mock_metrics()

            # Trier par date
            wellness_data.sort(key=lambda x: x["id"])
            wellness_start = wellness_data[0]
            wellness_end = wellness_data[-1]

            # Récupérer activités de la semaine
            activities = self.api.get_activities(oldest=start_date_str, newest=end_date_str)

            # Calculer métriques quotidiennes
            daily_metrics = []
            current_date = self.start_date

            while current_date <= self.end_date:
                date_str = current_date.strftime("%Y-%m-%d")

                # Trouver wellness pour cette date
                day_wellness = next((w for w in wellness_data if w["id"] == date_str), None)

                if day_wellness:
                    from cyclisme_training_logs.utils.metrics import (
                        extract_wellness_metrics,
                    )

                    day_metrics = extract_wellness_metrics(day_wellness)
                    daily_metrics.append(
                        {
                            "date": date_str,
                            "ctl": day_metrics["ctl"],
                            "atl": day_metrics["atl"],
                            "tsb": day_metrics["tsb"],
                            "weight": day_wellness.get("weight"),
                        }
                    )
                else:
                    daily_metrics.append(
                        {
                            "date": date_str,
                            "ctl": None,
                            "atl": None,
                            "tsb": None,
                            "weight": None,
                        }
                    )

                current_date += timedelta(days=1)

            from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

            start_metrics = extract_wellness_metrics(wellness_start)
            end_metrics = extract_wellness_metrics(wellness_end)

            metrics: dict[str, Any] = {
                "start": {
                    "ctl": start_metrics["ctl"],
                    "atl": start_metrics["atl"],
                    "tsb": start_metrics["tsb"],
                    "weight": wellness_start.get("weight", 0) if wellness_start else 0,
                },
                "end": {
                    "ctl": end_metrics["ctl"],
                    "atl": end_metrics["atl"],
                    "tsb": end_metrics["tsb"],
                    "weight": wellness_end.get("weight", 0) if wellness_end else 0,
                },
                "daily": daily_metrics,
                "activities_count": len(activities) if activities else 0,
            }

            print(
                f"   ✅ Métriques collectées (CTL: {metrics['start']['ctl']:.0f}→{metrics['end']['ctl']:.0f})"
            )

            return metrics

        except Exception as e:
            print(f"   ⚠️  Erreur collecte métriques API : {e}")
            print("      Utilisation de données mockées...")
            return self._mock_metrics()

    def _mock_metrics(self) -> dict:
        """Return des métriques mockées en cas d'erreur API."""
        return {
            "start": {"ctl": 0, "atl": 0, "tsb": 0, "weight": 0},
            "end": {"ctl": 0, "atl": 0, "tsb": 0, "weight": 0},
            "daily": [],
            "activities_count": len(self.workouts),
        }

    def collect_context_files(self) -> dict[str, str]:
        """Load fichiers contexte projet."""
        print("📚 Chargement des fichiers contexte...")

        context = {}

        files_to_load = {
            "project_prompt": "references/project_prompt_v2_1_revised.md",
            "cycling_concepts": "references/cycling_training_concepts.md",
        }

        for key, path in files_to_load.items():
            try:
                filepath = self.project_root / path
                if filepath.exists():
                    context[key] = filepath.read_text(encoding="utf-8")
                    print(f"   ✅ Chargé : {path}")
                else:
                    print(f"   ⚠️  Fichier non trouvé : {filepath}")
                    context[key] = f"[Fichier {path} non trouvé]"
            except Exception as e:
                print(f"   ⚠️  Erreur lecture {path} : {e}")
                context[key] = f"[Erreur lecture {path}]"

        return context

    def generate_weekly_prompt(self) -> str:
        """Generate le prompt complet pour Claude."""
        next_week = f"S{int(self.week_number[1:]) + 1:03d}"

        # Formater les séances
        workouts_text = "\n\n".join(
            [f"#### {workout['name']}\n{workout['content']}" for workout in self.workouts]
        )

        # Formater les dates
        start_date_str = self.start_date.strftime("%d/%m/%Y")
        end_date_str = self.end_date.strftime("%d/%m/%Y")

        prompt = f"""# Analyse Hebdomadaire Cyclisme - {self.week_number}.

## Contexte Athlète
{self.context_files.get('project_prompt', '[Project prompt non chargé]')}

## Période Analysée
- **Semaine** : {self.week_number}
- **Dates** : {start_date_str} → {end_date_str}
- **Séances réalisées** : {len(self.workouts)}

## Données de la Semaine

### Métriques Évolution
```json
{json.dumps(self.metrics, indent=2, ensure_ascii=False)}
```

### Analyses des Séances
{workouts_text}

## Mission

Génère les **6 fichiers markdown obligatoires** du rapport hebdomadaire selon le format standardisé.

### Format de Sortie OBLIGATOIRE

Tu DOIS structurer ta réponse avec ces délimiteurs exacts :

```markdown
### FILE: workout_history_{self.week_number}.md
[Contenu complet du fichier 1]

### FILE: metrics_evolution_{self.week_number}.md
[Contenu complet du fichier 2]

### FILE: training_learnings_{self.week_number}.md
[Contenu complet du fichier 3]

### FILE: protocol_adaptations_{self.week_number}.md
[Contenu complet du fichier 4]

### FILE: transition_{self.week_number}_{next_week}.md
[Contenu complet du fichier 5]

### FILE: bilan_final_{self.week_number}.md
[Contenu complet du fichier 6]
```

## Consignes Qualité

1. **Factuel** : Métriques précises, données vérifiables depuis les analyses
2. **Concis** : Éviter redondances entre les 6 fichiers
3. **Actionnable** : Recommandations spécifiques pour {next_week}
4. **Traçable** : Progression/régression identifiable sur chaque métrique
5. **Complet** : Aucun aspect technique des séances omis

## Règles Spécifiques par Fichier

### 1. workout_history_{self.week_number}.md
- Chronologie stricte (lundi → dimanche)
- Format par séance : Date | Durée | TSS | IF | RPE
- Métriques pré/post (CTL/ATL/TSB)
- Notes techniques factuelles

### 2. metrics_evolution_{self.week_number}.md
- Tableau FTP avec contexte tests
- Progression quotidienne TSB/Fatigue
- Évolution poids début → fin
- Validations techniques (découplage, HRRc si applicable)

### 3. training_learnings_{self.week_number}.md
- Maximum 5 découvertes majeures
- Patterns physiologiques identifiés
- Protocoles validés/invalidés avec preuves
- Points surveillance {next_week}

### 4. protocol_adaptations_{self.week_number}.md
- Ajustements justifiés par data
- Seuils/critères mis à jour
- Modifications hydratation/nutrition si nécessaire
- Exclusions avec raisons

### 5. transition_{self.week_number}_{next_week}.md
- État final factuel (TSB/Fatigue/Validations)
- 2-3 scénarios progression justifiés
- Recommandation avec arguments data-driven
- Timeline objectifs cycle en cours

### 6. bilan_final_{self.week_number}.md
- Synthèse ≤ 500 mots
- 3-4 points critiques maximum
- Protocoles établis cette semaine
- Conclusion actionnable

Commence maintenant l'analyse !
"""
        return prompt

    def parse_claude_response(self, response: str) -> dict[str, str]:
        """Parse la réponse de Claude en 6 fichiers.

        Args:
            response: La réponse complète de Claude

        Returns:
            Dict avec {filename: content}
        """
        files = {}

        current_file = None
        current_content: list[str] = []

        lines = response.split("\n")

        for line in lines:
            # Détecter une nouvelle balise FILE
            if line.strip().startswith("### FILE:"):
                # Sauvegarder le fichier précédent
                if current_file and current_content:
                    # Nettoyer le contenu
                    content = "\n".join(current_content).strip()
                    files[current_file] = content

                # Extraire le nom du nouveau fichier
                file_match = re.search(r"### FILE:\s*(.+\.md)", line)
                if file_match:
                    current_file = file_match.group(1).strip()
                    current_content = []
            else:
                # Ajouter la ligne au contenu actuel
                if current_file is not None:
                    current_content.append(line)

        # Sauvegarder le dernier fichier
        if current_file and current_content:
            content = "\n".join(current_content).strip()
            files[current_file] = content

        return files

    def validate_generated_files(self, files: dict[str, str]) -> bool:
        """Validate les fichiers générés."""
        next_week = f"S{int(self.week_number[1:]) + 1:03d}"

        expected_files = {
            f"workout_history_{self.week_number}.md": 2000,  # min chars
            f"metrics_evolution_{self.week_number}.md": 1000,
            f"training_learnings_{self.week_number}.md": 1500,
            f"protocol_adaptations_{self.week_number}.md": 500,
            f"transition_{self.week_number}_{next_week}.md": 800,
            f"bilan_final_{self.week_number}.md": 1000,
        }

        errors = []
        warnings = []

        for expected_file, min_length in expected_files.items():
            if expected_file not in files:
                errors.append(f"❌ Fichier manquant : {expected_file}")
            elif len(files[expected_file]) < min_length:
                warnings.append(
                    f"⚠️ Fichier court : {expected_file} "
                    f"({len(files[expected_file])} chars, min {min_length})"
                )
            else:
                print(f"   ✅ {expected_file} ({len(files[expected_file])} chars)")

        if errors:
            print("\n❌ Erreurs critiques :")
            for error in errors:
                print(f"   {error}")
            return False

        if warnings:
            print("\n⚠️  Avertissements :")
            for warning in warnings:
                print(f"   {warning}")
            print()
            response = input("Continuer quand même ? (O/n) : ")
            return response.lower() != "n"

        return True

    def git_commit(self):
        """Commit automatique des fichiers générés."""
        commit_message = f"""Rapport Hebdomadaire {self.week_number}.

Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}
Séances : {len(self.workouts)}

Fichiers générés :
- workout_history_{self.week_number}.md
- metrics_evolution_{self.week_number}.md
- training_learnings_{self.week_number}.md
- protocol_adaptations_{self.week_number}.md
- transition_{self.week_number}_{self._next_week()}.md
- bilan_final_{self.week_number}.md

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>.
"""
        try:
            # Ajouter le dossier
            subprocess.run(["git", "add", str(self.output_dir)], check=True, cwd=self.project_root)

            # Commiter
            subprocess.run(
                ["git", "commit", "-m", commit_message], check=True, cwd=self.project_root
            )

            print("✅ Commit git effectué")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erreur git : {e}")

    def run(self):
        """Workflow complet interactif."""
        # DEPRECATION WARNING

        print("\n" + "=" * 70)
        print("⚠️  DEPRECATION WARNING")
        print("=" * 70)
        print()
        print("Ce script 'weekly_analysis.py' est OBSOLÈTE (Gartner E).")
        print("Il sera supprimé dans une version future.")
        print()
        print("Utilisez le nouveau système Weekly Analysis (Phase 2):")
        print()
        print(
            f"  poetry run weekly-analysis --week {self.week_number} --start-date {self.start_date.strftime('%Y-%m-%d')}"
        )
        print()
        print("Avantages du nouveau système:")
        print("  - Architecture modulaire et testée")
        print("  - Intégration Phase 1 infrastructure")
        print("  - Génération automatisée sans clipboard manuel")
        print()
        print("Documentation: cyclisme_training_logs/workflows/workflow_weekly.py")
        print("=" * 70)
        print()

        response = input("Continuer avec le script obsolète ? (o/n) : ").strip().lower()
        if response != "o":
            print("\n✅ Utilisez le nouveau système avec: poetry run weekly-analysis --help")
            return

        print()

        print("=" * 70)
        print(f"  🎯 ANALYSE HEBDOMADAIRE {self.week_number}")
        print(
            f"  Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}"
        )
        print("=" * 70)
        print()

        # Étape 1 : Collecte données
        print("📊 ÉTAPE 1/5 : Collecte des données")
        print("-" * 70)

        self.workouts = self.collect_week_workouts()

        if len(self.workouts) == 0:
            print()
            print("⚠️  Aucune séance trouvée pour cette semaine")
            print("   Vérifier les dates ou le fichier workouts-history.md")
            return

        self.metrics = self.collect_week_metrics()
        self.context_files = self.collect_context_files()

        print()

        # Étape 2 : Génération prompt
        print("📝 ÉTAPE 2/5 : Génération du prompt")
        print("-" * 70)
        prompt = self.generate_weekly_prompt()

        # Copier dans le presse-papier
        try:
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.communicate(prompt.encode("utf-8"))
            print("✅ Prompt copié dans le presse-papier !")
        except Exception as e:
            print(f"⚠️  Erreur copie presse-papier : {e}")
            print("   Affichage du prompt à la place...")
            print()
            print(prompt[:500] + "...")
        print()

        # Étape 3 : Instructions utilisateur
        print("=" * 70)
        print("🔄 ÉTAPE 3/5 : ACTIONS UTILISATEUR")
        print("=" * 70)
        print()
        print("1. Ouvre Claude.ai dans ton navigateur")
        print("   → https://claude.ai")
        print()
        print("2. Colle le prompt (Cmd+V ou Ctrl+V)")
        print()
        print("3. Attends que Claude génère les 6 fichiers")
        print("   ⏱️  Temps estimé : 1-2 minutes")
        print()
        print("4. Copie TOUTE la réponse de Claude")
        print("   → Du premier ### FILE: jusqu'au dernier mot")
        print()
        print("5. Reviens ici et appuie sur Entrée")
        print()
        print("=" * 70)
        print()

        input("✋ Appuie sur ENTRÉE quand la réponse est copiée...")

        # Étape 4 : Parser réponse
        print()
        print("📥 ÉTAPE 4/5 : Extraction des fichiers")
        print("-" * 70)

        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            claude_response = result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return

        if not claude_response or len(claude_response) < 100:
            print("❌ Presse-papier vide ou contenu trop court")
            print("   Copie la réponse de Claude et relance le script")
            return

        print("✂️  Parsing de la réponse...")
        files = self.parse_claude_response(claude_response)

        # Validation des fichiers
        print()
        print("📋 Validation des fichiers...")
        if not self.validate_generated_files(files):
            print("❌ Validation échouée. Abandon.")
            return

        print()
        print(f"✅ Validation réussie : {len(files)} fichier(s)")
        print()

        # Étape 5 : Sauvegarde
        print("💾 ÉTAPE 5/5 : Sauvegarde des fichiers")
        print("-" * 70)

        for filename, content in files.items():
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            # Afficher taille du fichier
            size = len(content)
            print(f"   ✅ {filename} ({size} caractères)")

        print()
        print(f"📁 Fichiers sauvegardés dans : {self.output_dir}")
        print()

        # Étape 6 : Commit git (optionnel)
        commit = input("💾 Commit git automatique ? (o/n) : ").strip().lower()
        if commit == "o":
            print()
            self.git_commit()

        # Résumé final
        print()
        print("=" * 70)
        print("🎉 ANALYSE HEBDOMADAIRE TERMINÉE !")
        print("=" * 70)
        print()
        print(f"✅ Semaine : {self.week_number}")
        print(
            f"✅ Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}"
        )
        print(f"✅ Séances analysées : {len(self.workouts)}")
        print(f"✅ Fichiers générés : {len(files)}")
        print()
        print(f"📂 Dossier : {self.output_dir}")
        print()


def main():
    """Command-line entry point for weekly training analysis."""
    parser = argparse.ArgumentParser(
        description="Génération analyse hebdomadaire cyclisme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Analyse de la semaine S068
  python3 cyclisme_training_logs/weekly_analysis.py --week-id S068

  # Analyse avec date de début spécifique
  python3 cyclisme_training_logs/weekly_analysis.py --week-id S068 --start-date 2024-11-18.
""",
    )

    parser.add_argument(
        "--week-id", type=str, required=True, help="Numéro de semaine (format SXXX, ex: S072)"
    )

    parser.add_argument(
        "--start-date", help="Date de début de la semaine (format YYYY-MM-DD, optionnel)"
    )

    args = parser.parse_args()

    # Validation format semaine
    if not re.match(r"^S\d{3}$", args.week_id):
        print("❌ Format semaine invalide")
        print("   Format attendu : SXXX (ex: S068)")
        sys.exit(1)

    # Validation date si fournie
    if args.start_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            print("❌ Format date invalide")
            print("   Format attendu : YYYY-MM-DD (ex: 2024-11-18)")
            sys.exit(1)

    # Note: CWD check supprimé - config.py gère les paths automatiquement
    # Fonctionne depuis n'importe quel répertoire (code repo ou data repo)

    # Lancer le workflow
    try:
        analysis = WeeklyAnalysis(args.week_id, args.start_date)
        analysis.run()

    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrompu (Ctrl+C)")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n❌ Erreur inattendue : {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
