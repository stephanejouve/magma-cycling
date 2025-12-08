#!/usr/bin/env python3
"""
prepare_weekly_report.py - Prépare le prompt pour le bilan hebdomadaire

Ce script :
1. Extrait les séances de la semaine depuis workouts-history.md
2. Charge le contexte athlète et les logs récents
3. Génère un prompt structuré pour Claude.ai
4. Copie dans le presse-papier

Usage:
    python3 scripts/prepare_weekly_report.py --week 067
    python3 scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11
"""

import argparse
import json
import subprocess
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path


class WeeklyReportGenerator:
    """Générateur de prompt pour bilan hebdomadaire"""

    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.references_dir = self.project_root / "references"
        self.logs_dir = self.project_root / "logs"
        self.bilans_dir = self.project_root / "logs" / "weekly_reports"

    def load_athlete_context(self):
        """Charger le contexte athlète"""
        prompt_file = self.references_dir / "project_prompt_v2_1_revised.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def extract_week_workouts(self, week_number, start_date=None):
        """Extraire les séances d'une semaine spécifique"""
        history_file = self.logs_dir / "workouts-history.md"
        if not history_file.exists():
            return None

        with open(history_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Si date de début fournie, extraire par plage de dates
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = start + timedelta(days=7)

            workouts = []
            sections = content.split('###')

            for section in sections:
                if 'Date :' not in section:
                    continue

                # Extraire la date
                date_match = re.search(r'Date\s*:\s*(\d{2}/\d{2}/\d{4})', section)
                if date_match:
                    date_str = date_match.group(1)
                    workout_date = datetime.strptime(date_str, '%d/%m/%Y')

                    if start <= workout_date < end:
                        workouts.append('###' + section)

            return '\n'.join(workouts) if workouts else None

        # Sinon, extraire par pattern de semaine (S067, etc.)
        week_pattern = f"S{week_number:03d}"
        workouts = []
        sections = content.split('###')

        for section in sections:
            if week_pattern in section and 'Date :' in section:
                workouts.append('###' + section)

        return '\n'.join(workouts) if workouts else None

    def read_full_log(self, filename):
        """Lire un log complet"""
        log_file = self.logs_dir / filename
        if not log_file.exists():
            return f"_Fichier {filename} non trouvé_"

        with open(log_file, 'r', encoding='utf-8') as f:
            return f.read()

    def generate_prompt(self, week_number, week_workouts, athlete_context, start_date=None, end_date=None):
        """Générer le prompt pour Claude.ai"""

        # Calculer dates si non fournies
        if start_date and not end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = start + timedelta(days=6)
            end_date = end.strftime('%Y-%m-%d')

        date_range = f"{start_date} → {end_date}" if start_date else "À déterminer depuis les séances"

        prompt = f"""# Bilan Hebdomadaire S{week_number:03d}

## Contexte Athlète

{athlete_context if athlete_context else "[Contexte non disponible]"}

---

## Séances de la Semaine (S{week_number:03d})

**Période** : {date_range}

{week_workouts if week_workouts else "_Aucune séance trouvée pour cette semaine_"}

---

## Logs Continus (État Actuel)

### workouts-history.md
```
[Voir séances ci-dessus - extrait de la semaine]
```

### metrics-evolution.md
```
{self.read_full_log("metrics-evolution.md")[:3000]}
... [Continuer lecture si nécessaire]
```

### training-learnings.md
```
{self.read_full_log("training-learnings.md")[:2000]}
... [Continuer lecture si nécessaire]
```

### workout-templates.md
```
{self.read_full_log("workout-templates.md")[:2000]}
... [Continuer lecture si nécessaire]
```

---

## Demande de Génération

En tant qu'assistant coach, génère les **6 fichiers markdown obligatoires** pour le bilan de la semaine S{week_number:03d}.

**IMPORTANT** : Générer les fichiers dans l'ordre suivant avec le format EXACT :

### 1. workout_history_S{week_number:03d}.md

Contenu :
- Contexte semaine (TSS réalisé vs planifié, indoor/outdoor)
- Chronologie complète : toutes les séances détaillées
- Format standard pour chaque séance
- Découvertes techniques par séance
- Notes coach factuelles
- Évolution métriques finale vs début
- Enseignements majeurs (3-5 points)
- Recommandations semaine suivante

### 2. metrics_evolution_S{week_number:03d}.md

Contenu :
- Tableau FTP complet
- Progression quotidienne TSB/Fatigue/Condition/TSS
- Évolution poids début→fin
- Métriques clés finales (CTL/ATL/TSB estimés)
- Validations techniques semaine

### 3. training_learnings_S{week_number:03d}.md

Contenu :
- Découvertes techniques majeures
- Patterns physiologiques identifiés
- Innovations testées
- Limites/seuils découverts
- Protocoles validés/invalidés
- Points surveillance futurs

### 4. protocol_adaptations_S{week_number:03d}.md

Contenu :
- Ajustements protocoles suite enseignements
- Nouveaux seuils/critères techniques
- Modifications hydratation/nutrition
- Adaptations matériel/discipline
- Exclusions/interdictions mises à jour
- Surveillance renforcée identifiée

### 5. transition_S{week_number:03d}_S{week_number+1:03d}.md

Contenu :
- État final semaine (TSB/Fatigue/Validations)
- Acquisitions confirmées vs échecs
- Options progression semaine suivante (2-3 scénarios)
- Recommandation justifiée
- Timeline objectifs (tests, cycles)
- Risques identifiés progression

### 6. bilan_final_S{week_number:03d}.md

Contenu :
- Objectifs visés vs réalisés (synthèse factuelle)
- Métriques finales comparées début
- Découvertes majeures (max 3-4 points critiques)
- Séances clés analysées (succès/échecs)
- Protocoles établis/validés
- Ajustements recommandés cycle suivant
- Enseignements comportementaux
- Conclusion synthétique (2-3 phrases)

---

**Format de Production** :

Pour chaque fichier, générer :

```markdown
# [Titre du fichier]

[Contenu structuré selon le template ci-dessus]

---

**Semaine** : S{week_number:03d}
**Période** : {date_range}
**Généré le** : {datetime.now().strftime('%d/%m/%Y')}
```

**Règles de Production** :
1. Format Markdown exclusivement
2. Ton factuel, concis, technique
3. Données vérifiables
4. Recommandations spécifiques et actionnables
5. Aucun aspect technique omis

**Ordre de génération** : Respecter strictement l'ordre 1→6

---

Génère maintenant les 6 fichiers de bilan pour la semaine S{week_number:03d}.
"""

        return prompt

    def copy_to_clipboard(self, text):
        """Copier dans le presse-papier"""
        try:
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(text.encode('utf-8'))
            return True
        except Exception as e:
            print(f"⚠️  Erreur copie presse-papier : {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Préparer le prompt pour bilan hebdomadaire"
    )

    parser.add_argument(
        '--week',
        type=int,
        required=True,
        help="Numéro de semaine (ex: 67 pour S067)"
    )
    parser.add_argument(
        '--start-date',
        help="Date début semaine (YYYY-MM-DD, ex: 2025-11-11)"
    )
    parser.add_argument(
        '--project-root',
        default='.',
        help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    week_number = args.week

    print(f"📊 Préparation bilan hebdomadaire S{week_number:03d}")
    print("=" * 60)
    print()

    generator = WeeklyReportGenerator(args.project_root)

    # Charger contexte
    print("📖 Chargement du contexte athlète...")
    athlete_context = generator.load_athlete_context()
    if athlete_context:
        print("   ✅ Contexte chargé")
    else:
        print("   ⚠️  Contexte non trouvé")

    # Extraire séances de la semaine
    print(f"🔍 Extraction des séances S{week_number:03d}...")
    week_workouts = generator.extract_week_workouts(week_number, args.start_date)

    if week_workouts:
        # Compter le nombre de séances
        workout_count = week_workouts.count('###')
        print(f"   ✅ {workout_count} séance(s) trouvée(s)")
    else:
        print(f"   ⚠️  Aucune séance trouvée pour S{week_number:03d}")
        print()
        print("💡 Suggestions :")
        print(f"   - Vérifier que les séances sont nommées S{week_number:03d}-XX-...")
        print(f"   - Utiliser --start-date pour extraire par plage de dates")
        print(f"   - Exemple : --start-date 2025-11-11 (lundi de la semaine)")

    print()
    print("✍️  Génération du prompt...")

    # Générer le prompt
    prompt = generator.generate_prompt(
        week_number=week_number,
        week_workouts=week_workouts,
        athlete_context=athlete_context,
        start_date=args.start_date
    )

    # Copier dans presse-papier
    print("📋 Copie dans le presse-papier...")
    if generator.copy_to_clipboard(prompt):
        print("   ✅ Prompt copié !")
    else:
        print("   ⚠️  Échec copie, affichage :")
        print()
        print(prompt[:500])
        print("...")

    print()
    print("=" * 60)
    print(f"✅ PROMPT PRÊT POUR BILAN S{week_number:03d}")
    print("=" * 60)
    print()
    print("📝 ÉTAPES SUIVANTES :")
    print()
    print("1. Ouvrir Claude.ai")
    print("   → https://claude.ai")
    print()
    print("2. Coller le prompt (Cmd+V)")
    print()
    print("3. Attendre génération des 6 fichiers (~2-3 minutes)")
    print()
    print("4. Copier chaque fichier généré")
    print()
    print("5. Exécuter le script d'organisation :")
    print(f"   python3 scripts/organize_weekly_report.py --week {week_number}")
    print()
    print("=" * 60)


if __name__ == '__main__':
    main()
