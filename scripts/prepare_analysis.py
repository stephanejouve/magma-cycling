#!/usr/bin/env python3
"""
prepare_analysis.py - Prépare le prompt d'analyse pour Claude.ai

Ce script :
1. Récupère la dernière séance depuis Intervals.icu
2. Charge le contexte athlète et les logs récents
3. Génère un prompt optimisé pour analyse par Claude.ai
4. Copie le prompt dans le presse-papier macOS
5. Affiche les instructions pour l'utilisateur

Usage:
    python3 scripts/prepare_analysis.py [--activity-id XXXXXX]
    python3 scripts/prepare_analysis.py --config ~/.intervals_config.json
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import requests


class IntervalsAPI:
    """Client pour l'API Intervals.icu"""

    BASE_URL = "https://intervals.icu/api/v1"

    def __init__(self, athlete_id, api_key):
        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = (f"API_KEY", api_key)
        self.session.headers.update({"Content-Type": "application/json"})

    def get_activities(self, oldest=None, newest=None):
        """Récupérer les activités"""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/activities"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_activity(self, activity_id):
        """Récupérer les détails complets d'une activité"""
        url = f"{self.BASE_URL}/activity/{activity_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_wellness(self, oldest=None, newest=None):
        """Récupérer les données wellness"""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/wellness"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_events(self, oldest=None, newest=None):
        """Récupérer les événements du calendrier (incluant workouts planifiés)"""
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
        params = {}
        if oldest:
            params['oldest'] = oldest
        if newest:
            params['newest'] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_planned_workout(self, activity_id, activity_date):
        """Trouver le workout planifié associé à une activité

        Args:
            activity_id: ID de l'activité (ex: 'i107424849')
            activity_date: Date de l'activité (datetime object)

        Returns:
            Dict contenant le workout planifié ou None si pas trouvé
        """
        # Chercher dans une fenêtre de +/- 2 jours autour de l'activité
        oldest = (activity_date - timedelta(days=2)).strftime('%Y-%m-%d')
        newest = (activity_date + timedelta(days=2)).strftime('%Y-%m-%d')

        events = self.get_events(oldest=oldest, newest=newest)

        # Trouver l'événement avec paired_activity_id correspondant
        for event in events:
            if event.get('paired_activity_id') == activity_id:
                return event

        return None


class PromptGenerator:
    """Générateur de prompt pour analyse Claude.ai"""

    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.references_dir = self.project_root / "references"
        self.logs_dir = self.project_root / "logs"
        self.feedback_dir = Path(".athlete_feedback")
        self.feedback_file = self.feedback_dir / "last_feedback.json"

    def load_athlete_context(self):
        """Charger le contexte athlète depuis project_prompt_v2_1_revised.md"""
        prompt_file = self.references_dir / "project_prompt_v2_1_revised.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def load_recent_workouts(self, limit=5):
        """Charger les N dernières séances depuis workouts-history.md"""
        history_file = self.logs_dir / "workouts-history.md"
        if not history_file.exists():
            return None

        with open(history_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extraire les dernières entrées (simplifié)
        # On cherche les sections ### et prend les N premières après "## Historique"
        sections = content.split('###')
        recent = []
        count = 0
        for section in sections:
            if count >= limit:
                break
            if section.strip() and 'Date :' in section:
                recent.append('###' + section)
                count += 1

        return '\n'.join(recent) if recent else None

    def load_cycling_concepts(self):
        """Charger les concepts d'entraînement cyclisme"""
        concepts_file = self.references_dir / "cycling_training_concepts.md"
        if concepts_file.exists():
            with open(concepts_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def load_athlete_feedback(self):
        """Charger le feedback athlète s'il existe"""
        if not self.feedback_file.exists():
            return None

        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Erreur lecture feedback : {e}")
            return None

    def format_athlete_feedback(self, feedback):
        """Formater le feedback pour inclusion dans le prompt"""
        if not feedback:
            return None

        parts = []

        if feedback.get('rpe'):
            parts.append(f"**RPE** : {feedback['rpe']}/10")

        if feedback.get('ressenti_general'):
            parts.append(f"**Ressenti** : {feedback['ressenti_general']}")

        if feedback.get('difficultes'):
            parts.append(f"**Difficultés** :\n{feedback['difficultes']}")

        if feedback.get('points_positifs'):
            parts.append(f"**Points positifs** :\n{feedback['points_positifs']}")

        if feedback.get('contexte'):
            parts.append(f"**Contexte** : {feedback['contexte']}")

        if feedback.get('sensations_physiques'):
            sensations = ', '.join(feedback['sensations_physiques'])
            parts.append(f"**Sensations physiques** : {sensations}")

        if feedback.get('notes_libres'):
            parts.append(f"**Notes libres** :\n{feedback['notes_libres']}")

        return '\n\n'.join(parts) if parts else None

    def format_activity_data(self, activity):
        """Formater les données d'activité pour le prompt"""
        date = datetime.fromisoformat(activity['start_date_local'].replace('Z', '+00:00'))

        # Vérifier si l'activité vient de Strava
        is_strava = activity.get('source') == 'STRAVA'

        data = {
            'name': activity.get('name', 'Séance'),
            'type': activity.get('type', 'Cyclisme'),
            'date': date.strftime('%d/%m/%Y'),
            'date_iso': date.strftime('%Y-%m-%d'),
            'duration_min': activity.get('moving_time', 0) // 60,
            'tss': activity.get('icu_training_load', 0),
            'intensity': activity.get('icu_intensity', 0) / 100.0,
            'avg_power': activity.get('icu_average_watts', 0),
            'np': activity.get('icu_weighted_avg_watts', 0),
            'avg_cadence': activity.get('average_cadence', 0),
            'avg_hr': activity.get('average_heartrate', 0),
            'max_hr': activity.get('max_heartrate', 0),
            'decoupling': activity.get('decoupling', None),
            'description': activity.get('description', ''),
            'tags': activity.get('tags', []),
            'is_strava': is_strava,
            'source': activity.get('source', 'Unknown'),
        }

        return data

    def format_wellness_data(self, wellness):
        """Formater les données wellness"""
        if not wellness:
            return {
                'ctl': 0,
                'atl': 0,
                'tsb': 0,
                'weight': 0,
                'sleep_seconds': 0,
            }

        ctl = wellness.get('ctl', 0)
        atl = wellness.get('atl', 0)

        return {
            'ctl': ctl,
            'atl': atl,
            'tsb': ctl - atl,
            'weight': wellness.get('weight', 0),
            'sleep_seconds': wellness.get('sleepSecs', 0),
            'sleep_quality': wellness.get('sleepQuality', 0),
        }

    def format_planned_workout(self, planned_event):
        """Formater le workout planifié pour le prompt

        Args:
            planned_event: L'événement contenant le workout planifié

        Returns:
            Dict avec les informations formatées ou None
        """
        if not planned_event or not planned_event.get('workout_doc'):
            return None

        workout_doc = planned_event['workout_doc']

        # Extraire les données principales
        formatted = {
            'name': planned_event.get('name', 'Workout planifié'),
            'description': planned_event.get('description', ''),
            'duration_min': workout_doc.get('duration', 0) // 60,
            'tss_planned': planned_event.get('icu_training_load', 0),
            'avg_watts_planned': workout_doc.get('average_watts', 0),
            'np_planned': workout_doc.get('normalized_power', 0),
            'intensity_planned': planned_event.get('icu_intensity', 0) / 100.0 if planned_event.get('icu_intensity') else 0,
            'joules': workout_doc.get('joules', 0),
        }

        # Formater la structure des intervalles
        steps = workout_doc.get('steps', [])
        intervals = []

        for i, step in enumerate(steps):
            if 'reps' in step:
                # C'est un bloc d'intervalles répétés
                reps = step['reps']
                sub_steps = step.get('steps', [])
                interval_desc = []
                for sub in sub_steps:
                    power_info = self._format_power(sub.get('power', {}))
                    cadence = sub.get('cadence', {}).get('value', 0)
                    duration_min = sub.get('duration', 0) / 60
                    interval_desc.append(f"{duration_min:.0f}min @ {power_info} / {cadence}rpm")
                intervals.append(f"{reps}x ({' → '.join(interval_desc)})")
            else:
                # Step simple
                power_info = self._format_power(step.get('power', {}))
                cadence = step.get('cadence', {}).get('value', 0)
                duration_min = step.get('duration', 0) / 60
                step_type = ""
                if step.get('warmup'):
                    step_type = "[Warmup] "
                elif step.get('cooldown'):
                    step_type = "[Cooldown] "
                intervals.append(f"{step_type}{duration_min:.0f}min @ {power_info} / {cadence}rpm")

        formatted['intervals'] = intervals

        # Répartition des zones (time in zones)
        zone_times = workout_doc.get('zoneTimes', [])
        zones_str = []
        for zone in zone_times:
            if zone.get('secs', 0) > 0 and not zone.get('gap'):  # Ignorer Sweet Spot (gap=true)
                zone_name = zone.get('name', zone.get('id', 'Z?'))
                zone_min = zone['secs'] / 60
                zones_str.append(f"{zone_name}: {zone_min:.0f}min")

        formatted['zone_distribution'] = ', '.join(zones_str) if zones_str else 'N/A'

        return formatted

    def _format_power(self, power_dict):
        """Formater une valeur de puissance (gère %, watts absolus, rampes)"""
        if not power_dict:
            return "N/A"

        units = power_dict.get('units', '')

        if units == '%ftp':
            if 'value' in power_dict:
                return f"{power_dict['value']}%FTP"
            elif 'start' in power_dict and 'end' in power_dict:
                return f"{power_dict['start']}-{power_dict['end']}%FTP"
        elif units == 'w':
            return f"{power_dict.get('value', 0)}W"
        elif units == 'power_zone':
            return f"Z{power_dict.get('value', '?')}"

        return "N/A"

    def generate_prompt(self, activity_data, wellness_pre, wellness_post, athlete_context, recent_workouts, athlete_feedback=None, planned_workout=None, cycling_concepts=None):
        """Générer le prompt complet pour Claude.ai"""

        # Formater les données
        act = activity_data
        w_pre = self.format_wellness_data(wellness_pre)
        w_post = self.format_wellness_data(wellness_post)
        planned = self.format_planned_workout(planned_workout) if planned_workout else None

        decoupling_str = f"{act['decoupling']:.1f}%" if act['decoupling'] else "N/A"
        sleep_hours = w_pre['sleep_seconds'] / 3600 if w_pre['sleep_seconds'] and w_pre['sleep_seconds'] > 0 else 0
        weight_kg = w_pre['weight'] if w_pre['weight'] and w_pre['weight'] > 0 else 0

        # Avertissement Strava si nécessaire
        strava_warning = ""
        if act['is_strava']:
            strava_warning = f"""
⚠️  **ATTENTION : Activité Strava**
Source : {act['source']}
Les données API peuvent être limitées par les restrictions Strava.
Certaines métriques (puissance, découplage) peuvent être manquantes ou incomplètes.
→ Vérifier les données sur l'interface web Intervals.icu si nécessaire.

"""

        prompt = f"""# Analyse d'Entraînement Cyclisme

## Contexte Athlète

{athlete_context if athlete_context else "[Contexte non disponible - utiliser informations par défaut]"}

---

## 📚 Référence Cyclisme

{cycling_concepts if cycling_concepts else "[Concepts cyclisme non disponibles]"}

---

## Séance à Analyser

{strava_warning}### Informations Générales
- **Nom** : {act['name']}
- **Type** : {act['type']}
- **Date** : {act['date']}
- **Source** : {act['source']}

### Métriques Pré-séance
- CTL : {w_pre['ctl']:.0f}
- ATL : {w_pre['atl']:.0f}
- TSB : {w_pre['tsb']:+.0f}
- Poids : {weight_kg:.1f}kg
- Sommeil : {sleep_hours:.1f}h

### Exécution
- Durée réalisée : {act['duration_min']}min
- IF : {act['intensity']:.2f}
- TSS : {act['tss']:.0f}
- Puissance moyenne : {act['avg_power']:.0f}W
- Puissance normalisée : {act['np']:.0f}W
- Cadence moyenne : {act['avg_cadence']:.0f}rpm
- FC moyenne : {act['avg_hr']:.0f}bpm
- FC max : {act['max_hr']:.0f}bpm
- Découplage cardiovasculaire : {decoupling_str}

### Métriques Post-séance
- CTL : {w_post['ctl']:.0f}
- ATL : {w_post['atl']:.0f}
- TSB : {w_post['tsb']:+.0f}

### Description / Tags
{act['description'] if act['description'] else '_Aucune description_'}
{', '.join(act['tags']) if act['tags'] else ''}

---
"""

        # Ajouter section workout planifié si disponible
        if planned:
            prompt += f"""
## 📋 Workout Planifié vs Réalisé

### Objectifs Planifiés
- **Nom** : {planned['name']}
- **Durée prévue** : {planned['duration_min']}min
- **TSS prévu** : {planned['tss_planned']:.0f}
- **IF prévue** : {planned['intensity_planned']:.2f}
- **Puissance moy. prévue** : {planned['avg_watts_planned']:.0f}W
- **NP prévue** : {planned['np_planned']:.0f}W

### Structure Planifiée
"""
            for interval in planned['intervals']:
                prompt += f"- {interval}\n"

            prompt += f"""
### Répartition Zones Planifiée
{planned['zone_distribution']}

### Description Workout
{planned['description'][:500] if planned['description'] else '_Aucune description_'}{'...' if len(planned['description']) > 500 else ''}

### Comparaison Planifié vs Réalisé
- Durée : {planned['duration_min']}min prévu → {act['duration_min']}min réalisé ({act['duration_min'] - planned['duration_min']:+}min)
- TSS : {planned['tss_planned']:.0f} prévu → {act['tss']:.0f} réalisé ({act['tss'] - planned['tss_planned']:+.0f})
- IF : {planned['intensity_planned']:.2f} prévue → {act['intensity']:.2f} réalisée ({act['intensity'] - planned['intensity_planned']:+.2f})
- Puissance moy. : {planned['avg_watts_planned']:.0f}W prévue → {act['avg_power']:.0f}W réalisée ({act['avg_power'] - planned['avg_watts_planned']:+.0f}W)
- NP : {planned['np_planned']:.0f}W prévue → {act['np']:.0f}W réalisée ({act['np'] - planned['np_planned']:+.0f}W)

**Consigne d'analyse** : Évaluer l'adhérence au plan et identifier les écarts significatifs (>10% en durée/TSS, >5% en IF).

---
"""

        prompt += f"""
## Séances Récentes (Contexte)

{recent_workouts if recent_workouts else "_Historique non disponible_"}

---
"""

        # Ajouter feedback athlète si disponible
        if athlete_feedback:
            feedback_text = self.format_athlete_feedback(athlete_feedback)
            if feedback_text:
                prompt += f"""
## 💭 Retour Athlète (Ressenti Subjectif)

{feedback_text}

**Important** : Ce retour subjectif enrichit l'analyse objective des métriques. Croiser les deux perspectives pour une analyse complète.

---
"""

        prompt += """
## Demande d'Analyse

En tant qu'assistant coach, analyse cette séance avec un regard factuel et technique.

**Critères d'analyse :**
1. Factuel, basé uniquement sur les métriques disponibles
2. Évaluer qualité via découplage (<7.5% = validé)
3. Contextualiser avec TSB pré-séance et sommeil
4. Identifier patterns (Sweet-Spot, Endurance, VO2, etc.)
5. Recommandations concrètes basées sur les données

**Gestion des données manquantes (activités Strava) :**
- Si puissance = 0W : Indiquer "_Données non disponibles (source Strava)_"
- Si découplage = N/A : Analyser sur base FC/durée/TSS uniquement
- Mentionner les limites de l'analyse dans "Points d'Attention"
- Suggérer vérification manuelle sur Intervals.icu web si critique

---

**Fournis ton analyse dans ce format EXACT (markdown) :**

### {act['name']}
Date : {act['date']}

#### Métriques Pré-séance
- CTL : {w_pre['ctl']:.0f}
- ATL : {w_pre['atl']:.0f}
- TSB : {w_pre['tsb']:+.0f}
- Sommeil : {sleep_hours:.1f}h

#### Exécution
- Durée : {act['duration_min']}min
- IF : {act['intensity']:.2f}
- TSS : {act['tss']:.0f}
- Puissance moyenne : {act['avg_power']:.0f}W
- Puissance normalisée : {act['np']:.0f}W
- Cadence moyenne : {act['avg_cadence']:.0f}rpm
- FC moyenne : {act['avg_hr']:.0f}bpm
- Découplage : {decoupling_str}

#### Exécution Technique
[2-3 phrases sur validation zone, qualité technique, cohérence métriques]

#### Charge d'Entraînement
[2 phrases sur TSS, TSB, implications]

#### Validation Objectifs
- ✅/❌ [Critère 1]
- ✅/❌ [Critère 2]
- ✅/❌ [Critère 3 si pertinent]

#### Points d'Attention
- [Point 1]
- [Point 2 si pertinent]

#### Recommandations Progression
1. [Recommandation 1]
2. [Recommandation 2]

#### Métriques Post-séance
- CTL : {w_post['ctl']:.0f}
- ATL : {w_post['atl']:.0f}
- TSB : {w_post['tsb']:+.0f}

---

**IMPORTANT :**
- Générer UNIQUEMENT le bloc markdown ci-dessus
- Pas de texte explicatif avant ou après
- Pas de bloc de code (````markdown)
- Format directement insérable dans workouts-history.md
- Être concis et factuel

---

Génère maintenant l'entrée d'analyse.
"""

        return prompt

    def copy_to_clipboard(self, text):
        """Copier le texte dans le presse-papier macOS"""
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
            print(f"⚠️  Erreur lors de la copie dans le presse-papier : {e}")
            return False


def load_config(config_file):
    """Charger la configuration depuis un fichier JSON"""
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        return None

    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Préparer le prompt d'analyse pour Claude.ai"
    )

    parser.add_argument(
        '--athlete-id',
        help="ID de l'athlète Intervals.icu (ex: i123456)"
    )
    parser.add_argument(
        '--api-key',
        help="Clé API Intervals.icu"
    )
    parser.add_argument(
        '--config',
        default='~/.intervals_config.json',
        help="Fichier de configuration JSON (défaut: ~/.intervals_config.json)"
    )
    parser.add_argument(
        '--activity-id',
        help="ID de l'activité spécifique à analyser (sinon prend la dernière)"
    )
    parser.add_argument(
        '--project-root',
        default='.',
        help="Racine du projet (défaut: répertoire courant)"
    )

    args = parser.parse_args()

    # Charger la config
    config = load_config(args.config)

    athlete_id = args.athlete_id or (config and config.get('athlete_id'))
    api_key = args.api_key or (config and config.get('api_key'))

    if not athlete_id or not api_key:
        print("❌ Erreur: athlete_id et api_key requis")
        print("\nCréer ~/.intervals_config.json avec:")
        print('{"athlete_id": "i123456", "api_key": "YOUR_KEY"}')
        sys.exit(1)

    print("🔄 Préparation du prompt d'analyse...")
    print()

    try:
        # Connexion à l'API
        api = IntervalsAPI(athlete_id, api_key)

        # Récupérer l'activité
        if args.activity_id:
            print(f"📥 Récupération de l'activité {args.activity_id}...")
            activity = api.get_activity(args.activity_id)
            activities = [activity]
        else:
            print("📥 Récupération de la dernière activité...")
            # L'API Intervals.icu exige oldest ET newest
            newest_date = datetime.now()
            oldest_date = newest_date - timedelta(days=7)  # Chercher dans les 7 derniers jours

            activities = api.get_activities(
                oldest=oldest_date.strftime('%Y-%m-%d'),
                newest=newest_date.strftime('%Y-%m-%d')
            )

            if not activities:
                print("❌ Aucune activité trouvée dans les 7 derniers jours")
                sys.exit(1)

            # Trier par date décroissante et prendre la plus récente
            activities.sort(key=lambda x: x['start_date_local'], reverse=True)
            activity = activities[0]

        # Date de l'activité
        date = activity['start_date_local'][:10]
        activity_date = datetime.fromisoformat(activity['start_date_local'].replace('Z', '+00:00'))

        # Récupérer wellness
        wellness_data = api.get_wellness(oldest=date, newest=date)
        wellness = wellness_data[0] if wellness_data else None

        # Récupérer le workout planifié si disponible
        print(f"   ✅ Activité : {activity.get('name', 'Séance')}")
        print(f"   📅 Date : {date}")

        print("🔍 Recherche du workout planifié...")
        planned_workout = api.get_planned_workout(activity['id'], activity_date)
        if planned_workout:
            print(f"   ✅ Workout planifié trouvé : {planned_workout.get('name', 'N/A')}")
        else:
            print("   ℹ️  Pas de workout planifié associé (séance libre)")

        # Vérifier si l'activité vient de Strava
        if activity.get('source') == 'STRAVA':
            print()
            print("   ⚠️  ATTENTION : Cette activité vient de Strava")
            print("   Les données API sont limitées (restriction Strava)")
            print("   Certaines métriques peuvent être manquantes")
            print("   → Vérifier sur Intervals.icu web si besoin")

        print()

        # Générer le prompt
        generator = PromptGenerator(args.project_root)

        print("📖 Chargement du contexte...")
        athlete_context = generator.load_athlete_context()
        recent_workouts = generator.load_recent_workouts(limit=3)
        cycling_concepts = generator.load_cycling_concepts()

        # Charger feedback athlète si disponible
        athlete_feedback = generator.load_athlete_feedback()
        if athlete_feedback:
            print("   ✅ Feedback athlète trouvé !")
            if athlete_feedback.get('rpe'):
                print(f"      RPE : {athlete_feedback['rpe']}/10")
            if athlete_feedback.get('ressenti_general'):
                print(f"      Ressenti : {athlete_feedback['ressenti_general'][:50]}...")
        else:
            print("   ℹ️  Pas de feedback athlète (optionnel)")
            print("      → Utiliser collect_athlete_feedback.py pour enrichir l'analyse")

        print("✍️  Génération du prompt...")
        prompt = generator.generate_prompt(
            activity_data=generator.format_activity_data(activity),
            wellness_pre=wellness,
            wellness_post=wellness,  # Simplifié pour l'instant
            athlete_context=athlete_context,
            recent_workouts=recent_workouts,
            athlete_feedback=athlete_feedback,
            planned_workout=planned_workout,
            cycling_concepts=cycling_concepts
        )

        # Copier dans le presse-papier
        print("📋 Copie dans le presse-papier...")
        if generator.copy_to_clipboard(prompt):
            print("   ✅ Prompt copié !")

            # Effacer le feedback après utilisation
            if athlete_feedback and generator.feedback_file.exists():
                generator.feedback_file.unlink()
                print("   ✅ Feedback athlète consommé et effacé")
        else:
            print("   ⚠️  Échec de la copie, affichage du prompt :")
            print()
            print(prompt)

        print()
        print("=" * 60)
        print("✅ PROMPT PRÊT POUR CLAUDE.AI")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Ouvrir Claude.ai dans votre navigateur")
        print("   → https://claude.ai")
        print()
        print("2. Coller le prompt (Cmd+V)")
        print()
        print("3. Attendre l'analyse de Claude")
        print()
        print("4. Copier la réponse de Claude (UNIQUEMENT le bloc markdown)")
        print()
        print("5. Exécuter le script d'insertion :")
        print("   python3 scripts/insert_analysis.py")
        print()
        print("=" * 60)

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur API: {e}")
        if e.response.status_code == 401:
            print("   → Vérifier l'API key et l'athlete_id")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
