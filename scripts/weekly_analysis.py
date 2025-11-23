#!/usr/bin/env python3
"""
weekly_analysis.py - Génération analyse hebdomadaire cyclisme

Ce script génère automatiquement les 6 fichiers markdown du rapport hebdomadaire :
1. workout_history_sXXX.md - Chronologie complète des séances
2. metrics_evolution_sXXX.md - Évolution des métriques
3. training_learnings_sXXX.md - Découvertes et apprentissages
4. protocol_adaptations_sXXX.md - Ajustements des protocoles
5. transition_sXXX_sXXX.md - Transition vers semaine suivante
6. bilan_final_sXXX.md - Bilan global de la semaine

Usage:
    python3 scripts/weekly_analysis.py S068
    python3 scripts/weekly_analysis.py S068 --start-date 2024-11-18
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Import de la classe IntervalsAPI depuis prepare_analysis
from prepare_analysis import IntervalsAPI


class WeeklyAnalysis:
    """Orchestrateur de l'analyse hebdomadaire"""

    def __init__(self, week_number: str, start_date: Optional[str] = None):
        """
        Args:
            week_number: Format SXXX (ex: S068)
            start_date: Format YYYY-MM-DD (optionnel, auto si None)
        """
        self.week_number = week_number
        self.week_int = int(week_number[1:])  # Ex: S068 -> 68

        # Calcul des dates
        if start_date:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            self.start_date = self._calculate_week_start()

        self.end_date = self.start_date + timedelta(days=6)

        # Chemins
        self.project_root = Path(__file__).parent.parent
        self.output_dir = self.project_root / "logs" / "weekly_reports" / week_number
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.project_root / "logs"
        self.references_dir = self.project_root / "references"

        # API Intervals.icu
        config_path = Path.home() / ".intervals_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.api = IntervalsAPI(
                    athlete_id=config.get('athlete_id'),
                    api_key=config.get('api_key')
                )
        else:
            self.api = None
            print("⚠️  Config Intervals.icu non trouvée (~/.intervals_config.json)")

        # Données collectées
        self.workouts = []
        self.metrics = {}
        self.context_files = {}

    def _calculate_week_start(self) -> datetime:
        """Calculer la date de début de la semaine basé sur le numéro"""
        # Pour l'instant, utiliser une date de référence (à ajuster)
        # Exemple: S001 = 2024-01-01 (lundi)
        reference_date = datetime(2024, 1, 1)  # S001 commence le 1er janvier 2024
        weeks_offset = self.week_int - 1
        return reference_date + timedelta(weeks=weeks_offset)

    def _next_week(self) -> str:
        """Calculer le numéro de la semaine suivante"""
        return f"S{self.week_int + 1:03d}"

    def collect_week_workouts(self) -> List[Dict]:
        """Extraire les séances de la semaine depuis workouts-history.md"""
        history_file = self.logs_dir / "workouts-history.md"

        if not history_file.exists():
            print(f"❌ Fichier {history_file} introuvable")
            return []

        print(f"📖 Lecture de {history_file}...")

        with open(history_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parser les séances
        workouts = []
        seen = set()  # Pour éviter les doublons

        # Extraire la section "## Historique" seulement
        historique_match = re.search(r'## Historique\s*\n(.*)', content, re.DOTALL)
        if not historique_match:
            print("   ⚠️  Section '## Historique' non trouvée")
            return []

        historique_content = historique_match.group(1)

        # Extraire toutes les sections ### (séances)
        # Format attendu: ### Nom de la Séance\nDate : JJ/MM/YYYY
        sections = re.split(r'\n### ', historique_content)

        for section in sections[1:]:  # Skip le premier (avant le premier ###)
            # Extraire la date
            date_match = re.search(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', section)
            if not date_match:
                continue

            date_str = date_match.group(1)
            date = datetime.strptime(date_str, '%d/%m/%Y')

            # Vérifier si la date est dans la plage de la semaine
            if self.start_date <= date <= self.end_date:
                # Extraire le nom de la séance (première ligne)
                name = section.split('\n')[0].strip()

                # Créer une clé unique pour éviter les doublons
                key = f"{date_str}_{name}"

                if key not in seen:
                    seen.add(key)

                    # Extraire toute la section jusqu'au prochain ### ou fin
                    workout = {
                        'name': name,
                        'date': date,
                        'date_str': date_str,
                        'content': '### ' + section.strip()
                    }

                    workouts.append(workout)

        # Trier par date
        workouts.sort(key=lambda x: x['date'])

        print(f"   ✅ {len(workouts)} séance(s) trouvée(s)")
        for w in workouts:
            print(f"      - [{w['date_str']}] {w['name']}")

        return workouts

    def collect_week_metrics(self) -> Dict:
        """Collecter les métriques d'évolution via API Intervals.icu"""
        if not self.api:
            print("⚠️  API non disponible, skip métriques")
            return {}

        print("📊 Collecte des métriques Intervals.icu...")

        try:
            # Dates au format ISO
            oldest = self.start_date.strftime('%Y-%m-%d')
            newest = self.end_date.strftime('%Y-%m-%d')

            # Récupérer wellness quotidien
            wellness_data = self.api.get_wellness(oldest=oldest, newest=newest)

            if not wellness_data:
                print("   ⚠️  Aucune donnée wellness disponible")
                return {}

            # Trier par date
            wellness_data.sort(key=lambda x: x['id'])

            # Extraire métriques début et fin
            first_day = wellness_data[0]
            last_day = wellness_data[-1]

            metrics = {
                'ctl_start': first_day.get('ctl', 0),
                'atl_start': first_day.get('atl', 0),
                'tsb_start': first_day.get('ctl', 0) - first_day.get('atl', 0),
                'ctl_end': last_day.get('ctl', 0),
                'atl_end': last_day.get('atl', 0),
                'tsb_end': last_day.get('ctl', 0) - last_day.get('atl', 0),
                'weight_start': first_day.get('weight', 0),
                'weight_end': last_day.get('weight', 0),
                'daily_evolution': wellness_data
            }

            print(f"   ✅ Métriques collectées (CTL: {metrics['ctl_start']:.0f}→{metrics['ctl_end']:.0f})")

            return metrics

        except Exception as e:
            print(f"   ⚠️  Erreur collecte métriques : {e}")
            return {}

    def collect_context_files(self) -> Dict[str, str]:
        """Charger les fichiers contexte du projet"""
        print("📚 Chargement des fichiers contexte...")

        context = {}

        # Fichier principal: project_prompt
        prompt_file = self.references_dir / "project_prompt_v2_1_revised.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                context['project_prompt'] = f.read()
            print("   ✅ project_prompt_v2_1_revised.md")

        # Concepts cyclisme
        concepts_file = self.references_dir / "cycling_training_concepts.md"
        if concepts_file.exists():
            with open(concepts_file, 'r', encoding='utf-8') as f:
                context['cycling_concepts'] = f.read()
            print("   ✅ cycling_training_concepts.md")

        # Documentation complète (si disponible)
        doc_file = self.project_root / "Documentation_Complète_du_Suivi_v1_5.md"
        if doc_file.exists():
            with open(doc_file, 'r', encoding='utf-8') as f:
                context['documentation'] = f.read()
            print("   ✅ Documentation_Complète_du_Suivi_v1_5.md")

        return context

    def generate_weekly_prompt(self) -> str:
        """Générer le prompt complet pour Claude"""

        # Formater les dates
        date_start_str = self.start_date.strftime('%d/%m/%Y')
        date_end_str = self.end_date.strftime('%d/%m/%Y')
        next_week = self._next_week()

        # Formater les séances
        workouts_text = "\n\n".join([w['content'] for w in self.workouts])

        # Formater les métriques
        if self.metrics:
            metrics_text = f"""### Métriques Début de Semaine
- CTL : {self.metrics['ctl_start']:.0f}
- ATL : {self.metrics['atl_start']:.0f}
- TSB : {self.metrics['tsb_start']:+.0f}
- Poids : {self.metrics['weight_start']:.1f}kg

### Métriques Fin de Semaine
- CTL : {self.metrics['ctl_end']:.0f} ({self.metrics['ctl_end'] - self.metrics['ctl_start']:+.0f})
- ATL : {self.metrics['atl_end']:.0f} ({self.metrics['atl_end'] - self.metrics['atl_start']:+.0f})
- TSB : {self.metrics['tsb_end']:+.0f} ({self.metrics['tsb_end'] - self.metrics['tsb_start']:+.0f})
- Poids : {self.metrics['weight_end']:.1f}kg ({self.metrics['weight_end'] - self.metrics['weight_start']:+.1f}kg)
"""
        else:
            metrics_text = "_Métriques non disponibles_"

        prompt = f"""# Analyse Hebdomadaire {self.week_number}

## Contexte Athlète

{self.context_files.get('project_prompt', '[Context non disponible]')}

---

## 📚 Référence Cyclisme

{self.context_files.get('cycling_concepts', '[Concepts non disponibles]')}

---

## Données de la Semaine

- **Période** : {date_start_str} → {date_end_str}
- **Nombre de séances** : {len(self.workouts)}

### Métriques Évolution

{metrics_text}

---

## Analyses des Séances

{workouts_text if workouts_text else '_Aucune séance analysée_'}

---

## Mission

Génère les **6 fichiers markdown** du rapport hebdomadaire selon le format standardisé.

### Format Attendu

Chaque fichier doit être délimité par des balises claires. Utilise EXACTEMENT ce format :

```
### FILE: workout_history_{self.week_number}.md
[Contenu du fichier workout_history]

### FILE: metrics_evolution_{self.week_number}.md
[Contenu du fichier metrics_evolution]

### FILE: training_learnings_{self.week_number}.md
[Contenu du fichier training_learnings]

### FILE: protocol_adaptations_{self.week_number}.md
[Contenu du fichier protocol_adaptations]

### FILE: transition_{self.week_number}_{next_week}.md
[Contenu du fichier transition]

### FILE: bilan_final_{self.week_number}.md
[Contenu du fichier bilan_final]
```

---

## Contenu des Fichiers

### 1. workout_history_{self.week_number}.md

Chronologie complète des 7 séances :
- Reprise des analyses complètes depuis workouts-history.md
- Métriques pré/post par séance
- Découvertes techniques
- Notes coach

### 2. metrics_evolution_{self.week_number}.md

Évolution des métriques :
- Tableau FTP si test effectué
- Progression quotidienne TSB/Fatigue/Condition
- Évolution poids
- CTL/ATL/TSB début → fin

### 3. training_learnings_{self.week_number}.md

Découvertes et apprentissages :
- Découvertes techniques majeures (3-5 points)
- Patterns physiologiques identifiés
- Protocoles validés ou invalidés
- Points de surveillance pour le futur

### 4. protocol_adaptations_{self.week_number}.md

Ajustements protocoles :
- Modifications de seuils/critères
- Nouveaux protocoles établis
- Ajustements hydratation/nutrition
- Exclusions mises à jour

### 5. transition_{self.week_number}_{next_week}.md

Transition vers {next_week} :
- État final semaine actuelle
- Acquisitions validées vs échecs
- 2-3 options de progression pour {next_week}
- Recommandation choisie avec justification

### 6. bilan_final_{self.week_number}.md

Bilan global :
- Objectifs visés vs réalisés
- Métriques finales comparées aux attentes
- 3-4 découvertes majeures
- Protocoles établis cette semaine
- Conclusion synthétique (2-3 lignes)

---

## Consignes

1. **Factuel** : Basé uniquement sur les données fournies
2. **Concis** : Éviter les redondances entre fichiers
3. **Actionnable** : Recommandations concrètes et spécifiques
4. **Traçable** : Progression/régression facilement identifiable
5. **Complet** : Aucun aspect technique omis

---

## Format de Réponse EXACT

Tu DOIS générer ta réponse avec EXACTEMENT cette structure :

### FILE: workout_history_{self.week_number}.md
[Le contenu markdown du fichier 1]

### FILE: metrics_evolution_{self.week_number}.md
[Le contenu markdown du fichier 2]

### FILE: training_learnings_{self.week_number}.md
[Le contenu markdown du fichier 3]

### FILE: protocol_adaptations_{self.week_number}.md
[Le contenu markdown du fichier 4]

### FILE: transition_{self.week_number}_{next_week}.md
[Le contenu markdown du fichier 5]

### FILE: bilan_final_{self.week_number}.md
[Le contenu markdown du fichier 6]

**IMPORTANT** :
- Ne pas ajouter de blocs de code ````markdown
- Ne pas ajouter de texte explicatif avant ou après
- Générer UNIQUEMENT les 6 sections FILE ci-dessus
- Chaque section FILE doit contenir du markdown valide

Génère maintenant les 6 fichiers du rapport hebdomadaire.
"""

        return prompt

    def parse_claude_response(self, response: str) -> Dict[str, str]:
        """Parser la réponse de Claude en 6 fichiers

        Args:
            response: La réponse complète de Claude

        Returns:
            Dict avec {filename: content}
        """
        files = {}
        current_file = None
        current_content = []

        lines = response.split('\n')

        for line in lines:
            # Détecter une nouvelle balise FILE
            if line.strip().startswith('### FILE:'):
                # Sauvegarder le fichier précédent
                if current_file and current_content:
                    # Nettoyer le contenu
                    content = '\n'.join(current_content).strip()
                    files[current_file] = content

                # Extraire le nom du nouveau fichier
                file_match = re.search(r'### FILE:\s*(.+\.md)', line)
                if file_match:
                    current_file = file_match.group(1).strip()
                    current_content = []
            else:
                # Ajouter la ligne au contenu actuel
                if current_file is not None:
                    current_content.append(line)

        # Sauvegarder le dernier fichier
        if current_file and current_content:
            content = '\n'.join(current_content).strip()
            files[current_file] = content

        return files

    def git_commit(self):
        """Commit automatique des fichiers générés"""

        commit_message = f"""Rapport Hebdomadaire {self.week_number}

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

Co-Authored-By: Claude <noreply@anthropic.com>
"""

        try:
            # Ajouter le dossier
            subprocess.run(
                ['git', 'add', str(self.output_dir)],
                check=True,
                cwd=self.project_root
            )

            # Commiter
            subprocess.run(
                ['git', 'commit', '-m', commit_message],
                check=True,
                cwd=self.project_root
            )

            print("✅ Commit git effectué")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erreur git : {e}")

    def run(self):
        """Workflow complet interactif"""

        print("=" * 70)
        print(f"  🎯 ANALYSE HEBDOMADAIRE {self.week_number}")
        print(f"  Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}")
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
                ['pbcopy'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(prompt.encode('utf-8'))
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
            result = subprocess.run(
                ['pbpaste'],
                capture_output=True,
                text=True,
                check=True
            )
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

        expected_count = 6
        if len(files) != expected_count:
            print(f"⚠️  Attention : {len(files)} fichier(s) extrait(s) au lieu de {expected_count}")
            print()
            print("Fichiers détectés :")
            for filename in files.keys():
                print(f"   - {filename}")
            print()

            continuer = input("Continuer quand même ? (o/n) : ").strip().lower()
            if continuer != 'o':
                print("❌ Analyse annulée")
                return

        print(f"✅ {len(files)} fichier(s) extrait(s)")
        print()

        # Étape 5 : Sauvegarde
        print("💾 ÉTAPE 5/5 : Sauvegarde des fichiers")
        print("-" * 70)

        for filename, content in files.items():
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # Afficher taille du fichier
            size = len(content)
            print(f"   ✅ {filename} ({size} caractères)")

        print()
        print(f"📁 Fichiers sauvegardés dans : {self.output_dir}")
        print()

        # Étape 6 : Commit git (optionnel)
        commit = input("💾 Commit git automatique ? (o/n) : ").strip().lower()
        if commit == 'o':
            print()
            self.git_commit()

        # Résumé final
        print()
        print("=" * 70)
        print("🎉 ANALYSE HEBDOMADAIRE TERMINÉE !")
        print("=" * 70)
        print()
        print(f"✅ Semaine : {self.week_number}")
        print(f"✅ Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}")
        print(f"✅ Séances analysées : {len(self.workouts)}")
        print(f"✅ Fichiers générés : {len(files)}")
        print()
        print(f"📂 Dossier : {self.output_dir}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Génération analyse hebdomadaire cyclisme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Analyse de la semaine S068
  python3 scripts/weekly_analysis.py S068

  # Analyse avec date de début spécifique
  python3 scripts/weekly_analysis.py S068 --start-date 2024-11-18
"""
    )

    parser.add_argument(
        'week',
        help="Numéro de semaine (format SXXX, ex: S068)"
    )

    parser.add_argument(
        '--start-date',
        help="Date de début de la semaine (format YYYY-MM-DD, optionnel)"
    )

    args = parser.parse_args()

    # Validation format semaine
    if not re.match(r'^S\d{3}$', args.week):
        print("❌ Format semaine invalide")
        print("   Format attendu : SXXX (ex: S068)")
        sys.exit(1)

    # Validation date si fournie
    if args.start_date:
        try:
            datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print("❌ Format date invalide")
            print("   Format attendu : YYYY-MM-DD (ex: 2024-11-18)")
            sys.exit(1)

    # Vérifier qu'on est dans le bon répertoire
    if not Path('logs/workouts-history.md').exists():
        print("❌ Erreur : Ce script doit être lancé depuis la racine du projet")
        print(f"   Répertoire courant : {Path.cwd()}")
        print()
        print("   cd /Users/stephanejouve/cyclisme-training-logs")
        print("   python3 scripts/weekly_analysis.py S068")
        sys.exit(1)

    # Lancer le workflow
    try:
        analysis = WeeklyAnalysis(args.week, args.start_date)
        analysis.run()

    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrompu (Ctrl+C)")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
