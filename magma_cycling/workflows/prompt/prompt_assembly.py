"""Prompt assembly and output methods for PromptGenerator."""

import subprocess
from datetime import date

from magma_cycling.planning.outdoor_discipline import (
    check_discipline,
    format_discipline_report,
    generate_discipline_report,
)


class PromptAssemblyMixin:
    """Final prompt assembly and clipboard output."""

    def generate_prompt(
        self,
        activity_data,
        wellness_pre,
        wellness_post,
        athlete_context,
        recent_workouts,
        athlete_feedback=None,
        planned_workout=None,
        cycling_concepts=None,
        periodization_context=None,
        session_prescription=None,
    ):
        """Generate le prompt complet pour analyse IA."""
        # Formater les données

        act = activity_data
        w_pre = self.format_wellness_data(wellness_pre)
        w_post = self.format_wellness_data(wellness_post)
        planned = self.format_planned_workout(planned_workout) if planned_workout else None

        decoupling_str = f"{act['decoupling']:.1f}%" if act["decoupling"] else "N/A"

        # Format temperature data
        temperature_str = self._format_temperature_data(
            act.get("avg_temp"),
            act.get("min_temp"),
            act.get("max_temp"),
            act.get("has_weather", False),
        )

        # Extraction robuste des métriques avec fallback
        avg_power = self.get_power_value(act, "avg")
        normalized_power = self.get_power_value(act, "np")
        avg_cadence = self.get_cadence_value(act, "avg")
        avg_hr = self.get_hr_value(act, "avg")
        max_hr = self.get_hr_value(act, "max")

        # Warning si données puissance manquantes
        power_warning = ""
        if avg_power is None and normalized_power is None:
            power_warning = "\n⚠️  ATTENTION : Aucune donnée de puissance disponible (fichier .fit incomplet ou séance sans capteur)\n   → Analyse basée sur FC, cadence et RPE uniquement\n\n"
        sleep_hours = (
            w_pre["sleep_seconds"] / 3600
            if w_pre["sleep_seconds"] and w_pre["sleep_seconds"] > 0
            else 0
        )
        weight_kg = w_pre["weight"] if w_pre["weight"] and w_pre["weight"] > 0 else 0

        # Avertissement sommeil manquant
        sleep_warning = ""
        if sleep_hours == 0:
            sleep_warning = "\n⚠️  ATTENTION : Données de sommeil non disponibles dans Intervals.icu au moment de l'analyse\n   → Saisir les données wellness (Sleep) dans Intervals.icu avant génération du prompt\n   → Ou fournir l'information dans le feedback athlète\n\n"

        # Avertissement Strava si nécessaire
        strava_warning = ""
        if act["is_strava"]:
            strava_warning = f"""
⚠️  **ATTENTION : Activité Strava**

Source : {act['source']}
Les données API peuvent être limitées par les restrictions Strava.
Certaines métriques (puissance, découplage) peuvent être manquantes ou incomplètes.
→ Vérifier les données sur l'interface web Intervals.icu si nécessaire.

"""
        prompt = f"""# Analyse d'Entraînement Cyclisme.

## Contexte Athlète

{athlete_context if athlete_context else "[Contexte non disponible - utiliser informations par défaut]"}

---

## 📚 Référence Cyclisme

{cycling_concepts if cycling_concepts else "[Concepts cyclisme non disponibles]"}

---

## Séance à Analyser

{strava_warning}{power_warning}{sleep_warning}### Informations Générales
- **Nom** : {act['name']}
- **ID** : {act['id']}
- **Type** : {act['type']}
- **Date** : {act['date']}
- **Source** : {act['source']}
- **Environnement** : {"Indoor (Home Trainer)" if act.get('is_indoor') else "Outdoor"}

### Métriques Pré-séance
- CTL : {w_pre['ctl']:.0f}
- ATL : {w_pre['atl']:.0f}
- TSB : {w_pre['tsb']:+.0f}
- Poids : {weight_kg:.1f}kg
- Sommeil : {sleep_hours:.1f}h

### Exécution
- Durée réalisée : {act['duration_min']}min
- IF : {act['intensity']:.2f}
- TSS : {self.safe_format_metric(act.get('tss'), '.0f', '')}
- Puissance moyenne : {self.safe_format_metric(avg_power, '.0f', 'W')}
- Puissance normalisée : {self.safe_format_metric(normalized_power, '.0f', 'W')}
- Cadence moyenne : {self.safe_format_metric(avg_cadence, '.0f', 'rpm')}
- FC moyenne : {self.safe_format_metric(avg_hr, '.0f', 'bpm')}
- FC max : {self.safe_format_metric(max_hr, '.0f', 'bpm')}
- Découplage cardiovasculaire : {decoupling_str}
- Température : {temperature_str}

### Métriques Post-séance
- CTL : {w_post['ctl']:.0f}
- ATL : {w_post['atl']:.0f}
- TSB : {w_post['tsb']:+.0f}

### Feedback Athlète (saisi dans Intervals.icu)

**Ressenti général** : {self._format_feel_value(act.get('feel'))}

**Notes athlète** :
{self._format_athlete_notes(act.get('description', ''), w_pre.get('comments', ''))}

**Tags** : {', '.join(act['tags']) if act['tags'] else '_Aucun tag_'}

---
"""
        # Ajouter prescription coach si disponible
        if session_prescription:
            prompt += f"""
## 🎯 Prescription Coach (Objectifs de la Séance)

{session_prescription}

**Consigne d'analyse** : Évaluer si l'exécution répond aux objectifs prescrits
ci-dessus. Identifier les écarts entre intention et réalisation.

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
            for interval in planned["intervals"]:
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

---.
"""
        # Ajouter section discipline environnement
        prompt += self._build_environment_section(act, planned)

        # Ajouter contexte de périodisation si disponible
        if periodization_context:
            pc = periodization_context
            prompt += f"""

## 📊 Contexte Périodisation (Macro/Micro-Cycle)

### Phase Actuelle : {pc['phase']}

**Objectifs Cycle** :
- CTL actuel : {pc['ctl_current']:.1f}
- CTL cible : {pc['ctl_target']:.0f}
- Déficit CTL : {pc['ctl_deficit']:.1f} points
- FTP actuel : {pc['ftp_current']}W
- FTP cible : {pc['ftp_target']}W

**Progression** :
- Durée reconstruction estimée : {pc['weeks_to_target']} semaines
- TSS semaines charge : {pc['weekly_tss_load']} TSS
- TSS semaines récupération : {pc['weekly_tss_recovery']} TSS
- Fréquence récupération : Tous les {pc['recovery_week_frequency']} semaines

**État PID Controller** : {pc['pid_status']}

**Rationale Phase** :
{pc['rationale']}

**➡️ Impact sur l'Analyse** : Les recommandations doivent tenir compte de la phase actuelle. En RECONSTRUCTION BASE, prioriser volume aérobie (Tempo/Sweet-Spot). En CONSOLIDATION, introduire progressivement FTP/VO2. En DÉVELOPPEMENT FTP, focus intensité.

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
5. **Intégrer le feedback athlète** (section "Feedback Athlète") s'il est présent - ressenti général (1-5, 1=Excellent 5=Mauvais) et notes textuelles (avec système de fallback: description activité en priorité, wellness comments si vide)
6. Recommandations concrètes basées sur les données ET le ressenti

**Gestion des données manquantes (activités Strava) :**
- Si puissance = 0W : Indiquer "_Données non disponibles (source Strava)_"
- Si découplage = N/A : Analyser sur base FC/durée/TSS uniquement
- Mentionner les limites de l'analyse dans "Points d'Attention"
- Suggérer vérification manuelle sur Intervals.icu web si critique

---

**Fournis ton analyse dans ce format EXACT (markdown) :**

### {act['name']}
ID : {act['id']}
Date : {act['date']}

#### Métriques Pré-séance
- CTL : {w_pre['ctl']:.0f}
- ATL : {w_pre['atl']:.0f}
- TSB : {w_pre['tsb']:+.0f}
- Sommeil : {sleep_hours:.1f}h

#### Exécution
- Durée : {act['duration_min']}min
- IF : {act['intensity']:.2f}
- TSS : {self.safe_format_metric(act.get('tss'), '.0f', '')}
- Puissance moyenne : {self.safe_format_metric(avg_power, '.0f', 'W')}
- Puissance normalisée : {self.safe_format_metric(normalized_power, '.0f', 'W')}
- Cadence moyenne : {self.safe_format_metric(avg_cadence, '.0f', 'rpm')}
- FC moyenne : {self.safe_format_metric(avg_hr, '.0f', 'bpm')}
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

    def _build_environment_section(self, act, planned):
        """Construit la section environnement indoor/outdoor pour le prompt."""
        is_indoor = act.get("is_indoor", False)

        if is_indoor:
            return """
## 🏠 Environnement : Indoor (Home Trainer)

→ Conditions contrôlées. Évaluer la précision d'exécution par rapport au plan.
Pas de variables externes (vent, terrain, trafic). L'adhérence au plan doit être optimale.

---
"""
        # Outdoor : ajouter analyse discipline si planned workout avec IF
        if planned and planned.get("intensity_planned", 0) > 0 and act.get("intensity", 0) > 0:
            discipline_check = check_discipline(
                workout_name=act.get("name", "Séance"),
                workout_date=date.fromisoformat(act["date_iso"]),
                intensity_zone=self._guess_intensity_zone(act.get("intensity", 0)),
                environment="outdoor",
                if_planned=planned["intensity_planned"],
                if_actual=act["intensity"],
            )
            report = generate_discipline_report(discipline_check)
            discipline_md = format_discipline_report(report)

            return f"""
## 🌳 {discipline_md}

**Consigne** : En outdoor, évaluer la capacité à respecter l'intensité cible.
Déviation >10% = échec discipline (surcharge). Recommander indoor si récidive.

---
"""
        # Outdoor sans planned workout
        return """
## 🌳 Environnement : Outdoor

→ Variables externes possibles (vent, dénivelé, trafic).
Tenir compte de ces facteurs dans l'évaluation de l'exécution.

---
"""

    @staticmethod
    def _guess_intensity_zone(intensity_factor):
        """Détermine la zone d'intensité à partir de l'IF."""
        if intensity_factor >= 1.05:
            return "VO2"
        elif intensity_factor >= 0.91:
            return "FTP"
        elif intensity_factor >= 0.84:
            return "Sweet-Spot"
        elif intensity_factor >= 0.76:
            return "Tempo"
        elif intensity_factor >= 0.56:
            return "Endurance"
        else:
            return "Recovery"

    def copy_to_clipboard(self, text):
        """Copy le texte dans le presse-papier macOS."""
        try:
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.communicate(text.encode("utf-8"))
            return True
        except Exception as e:
            print(f"⚠️  Erreur lors de la copie dans le presse-papier : {e}")
            return False
