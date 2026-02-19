#!/usr/bin/env python3
"""
Script de Planification Hebdomadaire.

Génère un prompt pour votre assistant IA afin de créer les entraînements de la semaine.
Supporte tous les providers: Claude API, Mistral API, OpenAI, Ollama, Clipboard.
"""
import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from pydantic import ValidationError  # noqa: E402

from cyclisme_training_logs.config import create_intervals_client  # noqa: E402
from cyclisme_training_logs.planning.models import WeeklyPlan  # noqa: E402


class WeeklyPlanner:
    """Générateur de prompt pour planification hebdomadaire."""

    def __init__(self, week_number: str, start_date: datetime, project_root: Path):
        """Initialize the weekly planner.

        Args:
            week_number: Week identifier (e.g., "S074")
            start_date: Start date of the week (Monday)
            project_root: Root directory of the project
        """
        self.week_number = week_number

        self.start_date = start_date
        self.end_date = start_date + timedelta(days=6)
        self.project_root = project_root

        # Chemins importants
        self.references_dir = project_root / "references"

        # Get directories from data config
        from cyclisme_training_logs.config import get_data_config

        try:
            config = get_data_config()
            self.planning_dir = config.week_planning_dir
            self.weekly_reports_dir = config.data_repo_path / "weekly-reports"
        except FileNotFoundError:
            # Fallback to legacy paths
            self.logs_dir = project_root / "logs"
            self.planning_dir = self.logs_dir / "data" / "week_planning"
            self.weekly_reports_dir = self.logs_dir / "weekly_reports"

        self.planning_dir.mkdir(parents=True, exist_ok=True)

        # État collecté
        self.current_metrics: dict[str, Any] = {}
        self.context_files: dict[str, str] = {}
        self.previous_week_bilan = ""

        # API Intervals.icu
        self.api = None
        self._init_api()

    def _init_api(self):
        """Initialize l'API Intervals.icu (Sprint R9.B Phase 2 - centralized)."""
        try:
            self.api = create_intervals_client()
            print("✅ API Intervals.icu connectée")
        except ValueError as e:
            print(f"⚠️ API non disponible : {e}")
            print("   Les métriques seront approximatives")
        except Exception as e:
            print(f"⚠️ API non disponible : {e}")
            print("   Les métriques seront approximatives")

    def _previous_week_number(self) -> str:
        """Calculate le numéro de la semaine précédente."""
        current_num = int(self.week_number[1:])

        return f"S{current_num - 1:03d}"

    def _next_week_number(self) -> str:
        """Calculate le numéro de la semaine suivante."""
        current_num = int(self.week_number[1:])

        return f"S{current_num + 1:03d}"

    def _week_after_next(self) -> str:
        """Calculate le numéro de la semaine après la suivante."""
        current_num = int(self.week_number[1:])

        return f"S{current_num + 2:03d}"

    def collect_current_metrics(self) -> dict:
        """Collect les métriques actuelles depuis API."""
        print("\n📊 Collecte des métriques actuelles...")

        if not self.api:
            print("  ⚠️ API non disponible, métriques approximatives")
            return self._mock_current_metrics()

        try:
            # Date actuelle pour wellness
            today = datetime.now().strftime("%Y-%m-%d")

            # Wellness actuel
            wellness = self.api.get_wellness(oldest=today, newest=today)

            if wellness and len(wellness) > 0:
                current = wellness[0]

                from cyclisme_training_logs.utils.metrics import (
                    extract_wellness_metrics,
                )

                wellness_metrics = extract_wellness_metrics(current)
                metrics = {
                    "ctl": wellness_metrics["ctl"],
                    "atl": wellness_metrics["atl"],
                    "tsb": wellness_metrics["tsb"],
                    "weight": current.get("weight", 0),
                    "resting_hr": current.get("restingHR", 0),
                    "hrv": current.get("hrv", 0),
                    "date": today,
                }

                print(
                    f"  ✅ Métriques collectées (CTL: {metrics['ctl']:.0f}, TSB: {metrics['tsb']:+.0f})"
                )
                return metrics
            else:
                print("  ⚠️ Aucune donnée wellness disponible")
                return self._mock_current_metrics()

        except Exception as e:
            print(f"  ⚠️ Erreur collecte métriques : {e}")
            return self._mock_current_metrics()

    def _mock_current_metrics(self) -> dict:
        """Métriques mockées si API indisponible."""
        return {
            "ctl": 0,
            "atl": 0,
            "tsb": 0,
            "weight": 0,
            "resting_hr": 0,
            "hrv": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "note": "Métriques approximatives (API indisponible)",
        }

    def load_previous_week_bilan(self) -> str:
        """Load le bilan de la semaine précédente."""
        print("\n📄 Chargement bilan semaine précédente...")

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
            print(f"  ✅ Bilan {prev_week} chargé ({len(bilan_content)} chars)")
        else:
            print(f"  ⚠️ Bilan {prev_week} non trouvé : {bilan_file}")
            content_parts.append(f"[Bilan {prev_week} non disponible]")

        # Load transition (contains TSS, TSB, recommendations for next week)
        if transition_file.exists():
            transition_content = transition_file.read_text(encoding="utf-8")
            content_parts.append(f"\n\n{transition_content}")
            print(f"  ✅ Transition {prev_week} chargée ({len(transition_content)} chars)")
        else:
            print(f"  ⚠️ Transition {prev_week} non trouvée : {transition_file}")
            content_parts.append(f"\n\n[Transition {prev_week} non disponible]")

        return "\n".join(content_parts)

    def load_context_files(self) -> dict[str, str]:
        """Load les fichiers de contexte."""
        print("\n📚 Chargement fichiers contexte...")

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
                    print(f"  ✅ {filepath.name}")
                else:
                    print(f"  ⚠️ Non trouvé : {filepath.name}")
                    context[key] = f"[{filepath.name} non trouvé]"
            except Exception as e:
                print(f"  ⚠️ Erreur {filepath.name} : {e}")
                context[key] = f"[Erreur lecture {filepath.name}]"

        # Charger protocoles si disponibles
        protocols_dir = self.references_dir / "protocols"
        if protocols_dir.exists():
            protocols = []
            for protocol_file in protocols_dir.glob("*.md"):
                try:
                    protocols.append(protocol_file.read_text(encoding="utf-8"))
                    print(f"  ✅ {protocol_file.name}")
                except Exception as e:
                    print(f"  ⚠️ Erreur {protocol_file.name} : {e}")

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
                print("  ✅ intelligence.json")
            else:
                print("  ⚠️ Non trouvé : intelligence.json")
                context["intelligence"] = "[Aucune recommandation d'adaptation disponible]"
        except Exception as e:
            print(f"  ⚠️ Erreur intelligence.json : {e}")
            context["intelligence"] = f"[Erreur lecture intelligence.json: {e}]"

        return context

    def load_previous_week_workouts(self) -> str:
        """
        Load detailed workout analyses from previous week.

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
        print("\n📝 Chargement analyses détaillées semaine précédente...")

        try:
            # Get data repo path
            from cyclisme_training_logs.config import get_data_config

            config = get_data_config()
            history_file = config.data_repo_path / "workouts-history.md"

            if not history_file.exists():
                print(f"  ⚠️ workouts-history.md non trouvé : {history_file}")
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
                print(f"  ℹ️  Aucune analyse trouvée pour {prev_week}")
                return ""

            # Format section
            section = f"\n## 📊 Analyses Détaillées Semaine {prev_week}\n\n"
            section += (
                f"**{len(prev_week_workouts)} séance(s) analysée(s)** - "
                f"Retour d'expérience pour planification {self.week_number}\n\n"
            )
            section += "---\n\n"
            section += "\n\n".join(prev_week_workouts[:7])  # Max 7 workouts (1 week)

            print(f"  ✅ {len(prev_week_workouts)} analyse(s) chargée(s) pour {prev_week}")
            return section

        except Exception as e:
            print(f"  ⚠️ Erreur chargement analyses : {e}")
            return ""

    def load_periodization_context(self) -> dict | None:
        """
        Load periodization context (macro/micro-cycle position).

        Provides strategic context about training phase, CTL progression,
        and PID controller state for coherent weekly planning aligned
        with long-term objectives.

        Returns:
            Dict with periodization context or None if unavailable

        Examples:
            >>> context = planner.load_periodization_context()
            >>> context['phase']  # "RECONSTRUCTION_BASE"
            >>> context['weekly_tss_load']  # 350
        """
        print("\n🎯 Chargement contexte périodisation...")

        try:
            from cyclisme_training_logs.config.athlete_profile import AthleteProfile
            from cyclisme_training_logs.planning.peaks_phases import determine_training_phase
            from cyclisme_training_logs.workflows.pid_peaks_integration import (
                ControlMode,
                compute_integrated_correction,
            )

            # Load athlete profile
            profile = AthleteProfile.from_env()

            # Extract CTL from current metrics
            ctl_current = self.current_metrics.get("ctl", 0)

            if ctl_current == 0:
                print("  ⚠️ CTL non disponible, contexte périodisation ignoré")
                return None

            # Determine training phase
            phase_rec = determine_training_phase(
                ctl_current=ctl_current,
                ftp_current=profile.ftp,
                ftp_target=profile.ftp_target,
                athlete_age=profile.age,
            )

            # Compute PID integration status
            integrated = compute_integrated_correction(
                ctl_current=ctl_current,
                ftp_current=profile.ftp,
                ftp_target=profile.ftp_target,
                athlete_age=profile.age,
            )

            # Determine PID status
            if integrated.override_active:
                pid_status = "Override Peaks (CTL < 50 - reconstruction urgente)"
            elif integrated.mode == ControlMode.PID_CONSTRAINED:
                pid_status = "Actif avec contraintes Peaks"
            else:
                pid_status = "Actif (autonome)"

            # Format phase label
            phase_labels = {
                "reconstruction_base": "RECONSTRUCTION BASE",
                "consolidation": "CONSOLIDATION",
                "development_ftp": "DÉVELOPPEMENT FTP",
            }
            phase_label = phase_labels.get(phase_rec.phase.value, phase_rec.phase.value.upper())

            context = {
                "phase": phase_label,
                "phase_raw": phase_rec.phase.value,
                "ctl_current": ctl_current,
                "ctl_target": phase_rec.ctl_target,
                "ctl_deficit": phase_rec.ctl_deficit,
                "ftp_current": profile.ftp,
                "ftp_target": profile.ftp_target,
                "weeks_to_target": (
                    phase_rec.weeks_to_rebuild if phase_rec.weeks_to_rebuild > 0 else 0
                ),
                "pid_status": pid_status,
                "pid_override_active": integrated.override_active,
                "weekly_tss_load": phase_rec.weekly_tss_load,
                "weekly_tss_recovery": phase_rec.weekly_tss_recovery,
                "recovery_week_frequency": phase_rec.recovery_week_frequency,
                "intensity_distribution": phase_rec.intensity_distribution,
                "rationale": phase_rec.rationale,
            }

            print(f"  ✅ Phase {phase_label}, CTL {ctl_current:.1f} → {phase_rec.ctl_target:.0f}")
            return context

        except Exception as e:
            print(f"  ⚠️ Impossible de charger contexte périodisation : {e}")
            return None

    def _load_available_zwift_workouts(self) -> str:
        """Load available Zwift workouts from cache for diversity.

        Returns:
            Formatted section describing available workouts
        """
        try:
            from cyclisme_training_logs.external.zwift_client import ZwiftWorkoutClient

            client = ZwiftWorkoutClient()
            stats = client.get_cache_stats()

            if stats["total_workouts"] == 0:
                return ""

            # Build section
            section = "\n\n## 🎨 Workouts Externes Disponibles (Diversité)\n\n"
            section += "**Source:** Cache Zwift (whatsonzwift.com)\n"
            section += f"**Total disponible:** {stats['total_workouts']} workouts\n\n"

            if stats.get("by_category"):
                section += "**Par catégorie:**\n"
                for category, count in sorted(
                    stats["by_category"].items(), key=lambda x: x[1], reverse=True
                ):
                    section += f"  - {category}: {count} workout(s)\n"

            section += "\n**Instructions:**\n"
            section += "- Ces workouts peuvent être utilisés pour introduire de la DIVERSITÉ\n"
            section += "- Utiliser la commande: `poetry run search-zwift-workouts --type [TYPE] --tss [TSS]`\n"
            section += "- Le système track automatiquement l'usage pour éviter répétitions (fenêtre 21 jours)\n"
            section += "- Privilégier ces workouts pour varier des structures habituelles\n"
            section += "- Format Wahoo-compatible garanti (explicit power % on every line)\n\n"

            return section

        except Exception as e:
            logger.warning(f"Could not load Zwift workouts: {e}")
            return ""

    def generate_planning_prompt(self) -> str:
        """Generate le prompt complet pour l'assistant IA."""
        print("\n✍️ Génération du prompt de planification...")

        next_week = self._next_week_number()
        date_start_str = self.start_date.strftime("%d/%m/%Y")
        date_end_str = self.end_date.strftime("%d/%m/%Y")

        # Load periodization context and previous week workouts
        periodization_context = self.load_periodization_context()
        previous_week_workouts = self.load_previous_week_workouts()

        prompt = f"""# Planification Hebdomadaire Cyclisme - {self.week_number}.

## Contexte Athlète

{self.context_files.get('project_prompt', '[Project prompt non chargé]')}

---

## Période à Planifier

- **Semaine** : {self.week_number}
- **Dates** : {date_start_str} → {date_end_str} (7 jours)
- **Semaine suivante** : {next_week}

---

## État Actuel

### Métriques Actuelles
```json
{json.dumps(self.current_metrics, indent=2, ensure_ascii=False)}
```

### Bilan Semaine Précédente ({self._previous_week_number()})

{self.previous_week_bilan}

{previous_week_workouts}

---
"""
        # Add periodization context if available
        if periodization_context:
            pc = periodization_context
            prompt += f"""
## 🎯 Contexte Périodisation (Stratégie Macro-Cycle)

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

**Distribution Intensité Recommandée pour Phase {pc['phase']}** :
"""
            for zone, percentage in pc["intensity_distribution"].items():
                focus_marker = " ← **FOCUS**" if percentage >= 0.20 else ""
                prompt += f"- **{zone}** : {percentage * 100:.0f}%{focus_marker}\n"

            prompt += f"""
**État PID Controller** : {pc['pid_status']}

**Rationale Phase** :
{pc['rationale']}

**➡️ CRITIQUE pour Planification** : Les workouts de la semaine {self.week_number} doivent être alignés avec la phase {pc['phase']}. Respecter la distribution intensité recommandée ci-dessus et l'objectif TSS hebdomadaire ({pc['weekly_tss_load']} TSS semaine charge, {pc['weekly_tss_recovery']} TSS semaine récup).

---
"""

        prompt += """
## MÉTHODOLOGIE PEAKS COACHING (HUNTER ALLEN) - PRINCIPES OBLIGATOIRES

### Distribution Intensité Hebdomadaire (Méthode Traditionnelle)
**PRIORITAIRE pour Masters 50+ avec budget 8-12h/semaine :**
- **Récupération** : 10% TSS total
- **Endurance (56-75% FTP)** : 25%
- **Tempo (76-91% FTP)** : 35% ← **ZONE PRINCIPALE**
- **Sweet-Spot (88-93% FTP)** : Inclus dans Tempo, **PRIORISER en phase reconstruction CTL**
- **FTP (94-105%)** : 15%
- **VO2 max (106-120%)** : 10%
- **Anaérobie + Neuro (>120%)** : 5%

**Rationale** : Méthode Traditionnelle > Polarisée pour Masters 50+. Polarisée = psychologiquement insoutenable long terme (ennui Z1-Z2 + souffrance constante VO2/AC), taux abandon élevé.

---

## PRÉFÉRENCES PLANNING ATHLÈTE (PRIORITAIRE)

{self.context_files.get('planning_preferences', '[Préférences non chargées]')}

---

### Sweet-Spot : Zone Optimale FTP
**"Biggest bang for your training buck"** - Hunter Allen
- **88-93% FTP** (chevauche haut Tempo + bas FTP)
- Plus haut effet entraînement pour améliorer FTP avec sustainability psychologique
- Formats : 2x20min, 3x15min, 4x12min, continu 40-60min
- Découplage <7.5% = validation qualité

### Gestion CTL Masters 50+
**Citation Hunter Allen** : *"When you are 60 years young and your CTL drops from 80 down to 50, it's a long fight for months to get it back to 80!"*

**Règles Critiques** :
- **Maintenir CTL à 90% du maximum** en permanence (éviter variations >15 points)
- **CTL cible selon FTP** :
  - FTP 220W → CTL minimum 55-65
  - FTP 240W → CTL minimum 65-75
  - FTP 260W → CTL minimum 70-80
- **Alerte si drop >10 points en 4 semaines** (récupération lente âge 50+)
- **Progression CTL** : +2 à +3 points/semaine soutenable (max +4)
- **Semaines récup** : Tous les 3 semaines MAXIMUM (Masters 50+), jamais >3 semaines charge consécutives

### Volume TSS Recommandé
- **Semaines charge** : 350-400 TSS
- **Semaines récup** : 250-280 TSS
- **Ratio** : 3:1 (3 charge, 1 récup) ou 2:1 si fatigue accumulée

### Tests & Power Profiling
**"Testing is training and training is testing"** - Dr. Andrew Coggan
- **Ne JAMAIS bloquer semaine entière tests uniquement**
- Tests multiples même journée = OK (ordre : 5s → 1min → 5min → 20min)
- Pré-requis : TSB +10 minimum, sommeil >7h, fraîcheur optimale
- Fréquence : Tous les 8 semaines (comme FTP)

### Adaptation Physiologique
**Délai effet mesurable : 6-8 semaines**
- Cycle minimum = 6 semaines même stimulus
- Test FTP après 6-8 semaines stimulation appropriée
- Ne pas changer méthode avant 6 semaines (attendre délai adaptation)

### Éviter "Junk Miles"
**Junk Miles = Volume sans objectif structuré**
- TOUTE séance doit avoir zone(s) cible précise(s)
- Pas de "sortie libre" ou "selon envie" sauf semaine récup totale
- Si outdoor = >2 échecs discipline IF, basculer indoor cette zone

---

## Concepts d'Entraînement

{self.context_files.get('cycling_concepts', '[Concepts non chargés]')}

---

## Protocoles Validés

{self.context_files.get('protocols', '[Protocoles non chargés]')}

---

## 🧠 Intelligence AI & Adaptations Recommandées

**IMPORTANT:** Les adaptations ci-dessous proviennent du système PID (Planification Intelligente Dynamique) qui analyse l'évolution de l'athlète. Ces recommandations doivent être **prioritaires** dans la planification.

```json
{self.context_files.get('intelligence', '[Aucune recommandation disponible]')}
```

**Instructions CRITIQUES pour Test FTP:**

Si une adaptation recommande un test FTP avec affûtage, suivre ce timing précis:

1. **Semaine ACTUELLE ({self.week_number})**:
   - Continuer entraînement normal ou légère réduction volume
   - Ne PAS faire le test cette semaine
   - Ne PAS faire l'affûtage cette semaine

2. **Semaine SUIVANTE ({self._next_week_number()})**:
   - Semaine d'affûtage: réduction -40% TSS
   - Exemple: si CTL ~45, viser ~230 TSS total
   - Focus: endurance douce, récupération, fraîcheur

3. **Semaine APRÈS ({self._week_after_next()})**:
   - Test FTP samedi (jour 6)
   - Repos dimanche
   - TSB optimal pour test: +5 à +15

**Autres adaptations:**
- Analyser "evidence" pour contexte (dernier test, TSB, adhérence)
- Prioriser adaptations status="PROPOSED" + confidence="high"

---

## 🚨 RÉPÉTITIONS - RÈGLE CRITIQUE (À LIRE EN PREMIER)

**⚠️ ERREUR FRÉQUENTE À ÉVITER ABSOLUMENT** : Le placement du multiplicateur de répétition.

### ✅ FORMAT CORRECT (UNIQUE FORMAT ACCEPTÉ)

Le multiplicateur (2x, 3x, 4x, 5x...) doit TOUJOURS être placé **sur la ligne du titre de section**, jamais ailleurs.

**Structure obligatoire** :
```
[Nom section] [multiplicateur]x
- [intervalle 1]
- [intervalle 2]
- [intervalle N]
```

### 📋 Exemples Corrects Multiples

**Exemple 1 - Sweet Spot 3x10min** :
```
Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm
```
Résultat : 3 répétitions du bloc complet (10m effort + 4m récup) = 42min total

**Exemple 2 - VO2 max 5x3min** :
```
Main set 5x
- 3m 110% 95rpm
- 3m 55% 85rpm
```
Résultat : 5 répétitions du bloc = 30min total

**Exemple 3 - Seuil 4x8min** :
```
Main set 4x
- 8m 98% 90rpm
- 4m 60% 85rpm
```
Résultat : 4 répétitions du bloc = 48min total

**Exemple 4 - Pyramide 2x (structure complexe)** :
```
Main set 2x
- 3m 95% 92rpm
- 2m 65% 85rpm
- 5m 98% 90rpm
- 3m 65% 85rpm
- 3m 95% 92rpm
- 2m 65% 85rpm
```
Résultat : 2 répétitions de toute la pyramide = 36min total

### ❌ FORMATS INCORRECTS (NE JAMAIS FAIRE)

**ERREUR #1 - Multiplicateur dans la ligne d'intervalle** :
```
Main set
- 3x 10m 90%      ← ❌ FAUX - Intervals.icu ne comprendra pas
- 4m 62%
```
**Ce qui se passera** : Intervals.icu créera 1 seul intervalle bizarre ou erreur de parsing.

**ERREUR #2 - Section non standard avec multiplicateur** :
```
Test capacité 3x   ← ❌ FAUX - "Test capacité" n'est pas une section Intervals.icu
- 5m 70%
```
**Correction** : Utiliser `Main set 3x` ou `Intervals 3x`

**ERREUR #3 - Multiplicateur seul sur une ligne** :
```
Main set
3x                 ← ❌ FAUX - Le 3x doit être sur la même ligne que "Main set"
- 10m 90%
- 4m 62%
```

**ERREUR #4 - Format "répéter X fois"** :
```
Main set (répéter 3 fois)  ← ❌ FAUX - Intervals.icu ne comprend que "3x"
- 10m 90%
```

### 📊 Tableau Comparatif

| ❌ INCORRECT | ✅ CORRECT |
|-------------|-----------|
| `Main set`<br>`- 3x 10m 90%` | `Main set 3x`<br>`- 10m 90%` |
| `Test 4x`<br>`- 5m 95%` | `Main set 4x`<br>`- 5m 95%` |
| `Main set`<br>`3x`<br>`- 8m 88%` | `Main set 3x`<br>`- 8m 88%` |
| `Intervals (x3)`<br>`- 5m 110%` | `Intervals 3x`<br>`- 5m 110%` |

### 🎯 Sections Valides pour Répétitions

Seules ces sections sont reconnues par Intervals.icu :
- `Main set 3x` ✅
- `Intervals 4x` ✅
- `Work 5x` ✅
- `Efforts 2x` ✅

Sections NON valides :
- `Test capacité 3x` ❌
- `Bloc principal 4x` ❌
- `Série 5x` ❌

**Utiliser toujours "Main set" en cas de doute.**

---

## Guide Intervals.icu Workout Builder

**Documentation officielle** : Le fichier `David_-_Intervals_icu_-_Workout_builder_-_Guide_-_.pdf` dans le projet contient la syntaxe complète.

**Syntaxe de base validée** :
- Durée : `10m`, `30s`, `1h30`
- Intensité : `90%` (% FTP), `100-140w` (watts absolus)
- Cadence : `85rpm` ou `80-90rpm` (plage)
- Ramp : `ramp 50-65%` (progression)

**Exemple complet valide avec répétitions** :
```
Warmup
- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm
```

---

## Mission

Génère les **7 entraînements** pour la semaine {self.week_number} selon les critères suivants :

### Format de Sortie OBLIGATOIRE - Intervals.icu Natif

Pour chaque jour, génère **UNIQUEMENT** le code Intervals.icu pur (pas de markdown, pas de balises) :

```
=== WORKOUT {self.week_number}-01-TYPE-NomExercice-V001 ===

[Nom séance] ([durée]min, [TSS] TSS)

Warmup
- [durée] [intensité%] [cadence]rpm

Main set
- [structure]

Cooldown
- [durée] [intensité%] [cadence]rpm

=== FIN WORKOUT ===
```

**IMPORTANT** :
- Pas de `###`, `**`, ou autre markdown
- Format texte pur Intervals.icu uniquement
- Chaque workout séparé par `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- Directement copiable dans Intervals.icu Workout Builder

### Convention de Nommage

- **Format** : `SSSS-JJ-TYPE-NomExercice-V001`
- **SSSS** : {self.week_number}
- **JJ** : 01 à 07 (lundi à dimanche)
- **TYPE** : END, INT, FTP, SPR, CLM, REC, FOR, CAD, TEC, MIX, PDC, TST
- **NomExercice** : CamelCase sans accents (ex: EnduranceBase, SweetSpotProgressif)

### Types d'Entraînements (CODE)

- **END** : Endurance (Z2, base aérobie)
- **INT** : Intervalles (Sweet-Spot, Seuil, VO2)
- **FTP** : Test FTP ou séance FTP spécifique
- **SPR** : Sprint (efforts maximaux courts)
- **CLM** : Contre-la-montre (efforts soutenus haute intensité)
- **REC** : Récupération active
- **FOR** : Force (cadence basse, couple élevé)
- **CAD** : Technique cadence (variations RPM)
- **TEC** : Technique générale
- **MIX** : Mixte (plusieurs types dans la séance)
- **PDC** : Pédaling/Cadence (technique pédalage)
- **TST** : Test (VO2 max, sprint, etc.)

### Contraintes Obligatoires

1. **Dimanche = REPOS OBLIGATOIRE** (aucune séance)
2. **TSB Management** :
   - Si TSB actuel < +5 : Pas de VO2 max
   - Si TSB < 0 : Prioriser récupération/endurance
   - Si TSB > +10 : Possibilité intensité élevée
3. **Progression CTL** : +3 à +4 points/semaine maximum
4. **Indoor-only** : Toutes séances indoor (Zwift/TrainingPeaks Virtual)
5. **Hydratation** : Spécifier protocole si séance >75min
6. **Mercredi allégé** : Séance technique ou récupération privilégiée

### Structure Type par Jour

- **Lundi** : Endurance Z2 ou Technique
- **Mardi** : Sweet-Spot ou Intervalles modérés
- **Mercredi** : Technique/Cadence ou Récupération
- **Jeudi** : Endurance progressive ou Force
- **Vendredi** : Activation ou Sweet-Spot léger
- **Samedi** : Volume (endurance longue) ou Intensité haute si TSB favorable
- **Dimanche** : **REPOS COMPLET**

### Règles Intensité

1. **Z2 (Endurance)** : 60-75% FTP
   - Durée : 45-90min
   - Cadence : 85-90 rpm naturelle

2. **Sweet-Spot** : 88-93% FTP
   - Blocs : 8-12min maximum
   - Récupération : 50% de la durée bloc
   - Maximum 3-4 blocs par séance

3. **Seuil** : 95-105% FTP
   - Blocs : 5-8min maximum
   - Récupération : durée bloc minimum
   - Précédé de validation TSB

4. **VO2 Max** : 106-120% FTP
   - **UNIQUEMENT si TSB ≥ +5**
   - Blocs : 3-5min
   - Ratio travail/repos : 1:1 minimum
   - Maximum 20min cumulés haute intensité

### Checklist VO2 Max (5 critères)

Si tu proposes une séance VO2 max, vérifie :
1. ✅ TSB actuel ≥ +5
2. ✅ Pas d'intensité >85% FTP dans les 48h précédentes
3. ✅ Placé mardi ou jeudi (milieu de semaine)
4. ✅ Séance récupération le lendemain
5. ✅ CTL progression raisonnable (+3-4 max)

### Validation Technique

Pour chaque séance, spécifie :
- **Découplage cardiaque attendu** : <7.5% optimal
- **RPE estimé** : Échelle 1-10
- **Focus technique** : Cadence, position, transitions
- **Hydratation** : 500ml/h standard, 600ml/h si >75min ou >88% FTP

### Documentation par Séance

```markdown
### WORKOUT: {self.week_number}-0X-TYPE-NomExercice-V001

**Objectif** : [Objectif physiologique]
**TSS** : [valeur]
**Durée** : [minutes]
**IF** : [Intensity Factor]

[Structure Intervals.icu]

**Points clés** :
- [Consigne technique 1]
- [Consigne technique 2]
- [Hydratation si nécessaire]

**Placement semaine** : [Justification]
```

---

## Format Intervals.icu - Rappel

Utilise la syntaxe Intervals.icu standard :

```
Warmup
- 10m 50-65% 85rpm

Main set
- 8m 90% 90rpm
- 3m 65% 85rpm

Cooldown
- 10m 65-50% 85rpm
```

**Syntaxe** :
- Durée : `10m`, `30s`, `1h`
- Intensité : `90%` (% FTP) ou `100-140w` (watts absolus)
- Cadence : `85rpm` ou `80-90rpm` (plage)
- **Répétitions** : Mettre le multiplicateur sur la ligne du titre de section
  - ✅ Correct : `Main set 3x`
  - ❌ Incorrect : `- 3x 10m 90%`

---

## Livrables Attendus

Génère **7 blocs WORKOUT** (un par jour, dimanche = mention repos) au format texte pur Intervals.icu.

**Exemple de format attendu** :

```
=== WORKOUT {self.week_number}-01-END-EnduranceBase-V001 ===

Endurance Base (70min, 52 TSS)

Warmup
- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set
- 45m 68-72% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm

=== FIN WORKOUT ===


=== WORKOUT {self.week_number}-02-INT-SweetSpot-V001 ===

Sweet Spot 3x10 (74min, 78 TSS)

Warmup
- 12m ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm

=== FIN WORKOUT ===
```

**Continue ce format pour les 7 jours.** Chaque workout doit être :
- Délimité par `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- Format texte pur (pas de markdown **bold** ou ###)
- Directement copiable dans Intervals.icu
- Syntaxe validée : durée + % FTP + cadence

---
{self._load_available_zwift_workouts()}
---

## Commence Maintenant la Planification !

Génère les 7 entraînements pour {self.week_number} ({date_start_str} → {date_end_str}) au format ci-dessus.

**RAPPEL CRITIQUE** :
- ✅ Format TEXTE PUR Intervals.icu (pas de markdown)
- ✅ Délimiteurs `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- ✅ Syntaxe : `10m 90% 92rpm` (espace entre valeurs)
- ✅ Ramp : `ramp 50-65%` (pas `Ramp`)
- ❌ AUCUN `**bold**`, `###`, ou autre markdown
- ❌ AUCUNE explication après les workouts

**🚨 RÉPÉTITIONS - RAPPEL FINAL** :
- ✅ CORRECT : `Main set 3x` sur la ligne du titre
- ✅ CORRECT : `Main set 5x` sur la ligne du titre
- ❌ FAUX : `- 3x 10m 90%` dans l'intervalle
- ❌ FAUX : `Main set` puis `3x` sur ligne suivante
- ❌ FAUX : `Test capacité 3x` (section invalide)

**Exemple répétitions valide** :
```
Main set 4x
- 8m 95% 90rpm
- 4m 62% 85rpm
```

Le but est que je puisse **copier-coller directement** chaque bloc dans Intervals.icu Workout Builder sans modification.
"""
        return prompt

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy le texte dans le presse-papier (macOS)."""
        try:
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return True
        except Exception as e:
            print(f"⚠️ Erreur copie presse-papier : {e}")
            return False

    def update_session_status(self, session_id: str, status: str, reason: str | None = None):
        """
        Update le statut d'une séance dans le JSON avec protection Pydantic.

        Args:
            session_id: ID de la séance (ex: S074-01)
            status: Nouveau statut (completed, cancelled, skipped, etc.)
            reason: Raison de l'annulation/modification (optionnel).

        Returns:
            bool: True si succès, False si erreur

        Note:
            Utilise WeeklyPlan (Pydantic) pour validation automatique et
            protection contre shallow copy. Migration: 08-02-2026.
        """
        json_file = self.planning_dir / f"week_planning_{self.week_number}.json"

        if not json_file.exists():
            print(f"⚠️ Planning JSON non trouvé : {json_file}")
            return False

        try:
            # ✅ Chargement sécurisé avec Pydantic (validation auto)
            plan = WeeklyPlan.from_json(json_file)
        except (FileNotFoundError, ValidationError) as e:
            print(f"⚠️ Erreur de chargement du planning : {e}")
            return False

        # Trouver et mettre à jour la séance
        session_found = False
        for session in plan.planned_sessions:
            if session.session_id == session_id:
                # ✅ Validation automatique par Pydantic (validate_assignment=True)
                try:
                    # IMPORTANT: Définir skip_reason AVANT de changer le statut
                    # (validator Pydantic vérifie que skip_reason est présent si status='skipped')
                    if reason:
                        if status == "cancelled":
                            # Note: cancellation_reason/date not in Session model yet
                            # Keep backward compatibility for now
                            pass
                        elif status == "skipped":
                            session.skip_reason = reason  # Défini AVANT statut

                    session.status = status  # Type-checked et validé!

                except ValidationError as e:
                    print(f"⚠️ Valeur invalide pour le statut : {e}")
                    return False

                session_found = True
                break

        if not session_found:
            print(f"⚠️ Séance {session_id} non trouvée dans le planning")
            return False

        # Mettre à jour last_updated
        plan.last_updated = datetime.now(UTC)

        # ✅ Sauvegarde atomique via Pydantic
        try:
            plan.to_json(json_file)
        except Exception as e:
            print(f"⚠️ Erreur de sauvegarde : {e}")
            return False

        print(f"✅ Séance {session_id} mise à jour : {status}")
        if reason:
            print(f"   Raison : {reason}")

        return True

    def save_planning_json(self, workouts_data: list | None = None):
        """
        Backup le planning au format JSON.

        Args:
            workouts_data: Liste des workouts générés (optionnel, créera template si None).
        """
        json_file = self.planning_dir / f"week_planning_{self.week_number}.json"

        # Si pas de workouts fournis, créer template basique
        if workouts_data is None:
            workouts_data = []
            for day in range(7):
                date = self.start_date + timedelta(days=day)
                session_num = day + 1
                workouts_data.append(
                    {
                        "session_id": f"{self.week_number}-{session_num:02d}",
                        "date": date.strftime("%Y-%m-%d"),
                        "name": f"Session{session_num}",
                        "type": "END",  # Default type
                        "version": "V001",
                        "tss_planned": 0,
                        "duration_min": 0,
                        "description": "À définir",
                        "status": "planned",
                    }
                )

        # Get athlete_id from config
        from cyclisme_training_logs.config import get_intervals_config

        intervals_config = get_intervals_config()

        planning = {
            "week_id": self.week_number,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "created_at": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
            "version": 1,
            "athlete_id": intervals_config.athlete_id,
            "tss_target": sum(w.get("tss_planned", 0) for w in workouts_data),
            "planned_sessions": workouts_data,
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(planning, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Planning JSON sauvegardé : {json_file}")
        return json_file

    def run(self):
        """Execute le workflow complet."""
        print("=" * 70)

        print(f"📅 PLANIFICATION HEBDOMADAIRE {self.week_number}")
        print(
            f"Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}"
        )
        print("=" * 70)

        # Étape 1 : Collecter métriques
        self.current_metrics = self.collect_current_metrics()

        # Étape 2 : Charger bilan semaine précédente
        self.previous_week_bilan = self.load_previous_week_bilan()

        # Étape 3 : Charger contexte
        self.context_files = self.load_context_files()

        # Étape 4 : Générer prompt
        prompt = self.generate_planning_prompt()

        # Étape 4.5 : Créer JSON template du planning
        self.save_planning_json()

        # Étape 5 : Copier dans presse-papier
        print("\n📋 Copie dans le presse-papier...")
        if self.copy_to_clipboard(prompt):
            print("  ✅ Prompt copié (Cmd+V pour coller)")
        else:
            print("  ⚠️ Copie manuelle nécessaire")
            print("\n" + "=" * 70)
            print(prompt)
            print("=" * 70)

        # Instructions
        print("\n" + "=" * 70)
        print("📝 PROCHAINES ÉTAPES (MÉTHODE RECOMMANDÉE) :")
        print("=" * 70)
        print()
        print("1. Choisir votre assistant IA (Claude, Mistral, OpenAI, Ollama)")
        print("2. Coller le prompt (Cmd+V)")
        print("3. Attendre que l'IA génère les 7 entraînements")
        print("4. Copier la réponse COMPLÈTE de l'IA")
        print()
        print("5. Sauvegarder dans un fichier :")
        workouts_file = self.planning_dir / f"{self.week_number}_workouts.txt"
        print(f"   pbpaste > {workouts_file}")
        print()
        print("6. Uploader depuis le fichier (PLUS FIABLE que clipboard) :")
        print(f"   poetry run upload-workouts --week-id {self.week_number} \\")
        print(f"     --start-date {self.start_date.strftime('%Y-%m-%d')} \\")
        print(f"     --file {workouts_file}")
        print()
        print("💡 Pourquoi utiliser --file ?")
        print("   • Clipboard volatile (peut être écrasé)")
        print("   • Fichier = traçabilité et possibilité de rejouer")
        print("   • Moins d'erreurs de manipulation")
        print()
        print("💡 Tip: Utilisez 'workflow-coach' pour automatisation complète")
        print()
        print("=" * 70)
        print(f"✅ Planification {self.week_number} prête !")
        print("=" * 70)


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Générer prompt de planification hebdomadaire pour assistant IA"
    )
    parser.add_argument(
        "--week-id", type=str, required=True, help="Numéro de semaine (format SXXX, ex: S072)"
    )
    parser.add_argument(
        "--start-date", type=str, required=True, help="Date de début (lundi) au format YYYY-MM-DD"
    )
    parser.add_argument(
        "--project-root", type=str, help="Racine du projet (défaut: répertoire parent du script)"
    )

    args = parser.parse_args()

    # Validation format semaine
    if not args.week_id.startswith("S") or len(args.week_id) != 4:
        print(f"❌ Format semaine invalide : {args.week_id}")
        print("   Utiliser le format SXXX (ex: S072)")
        sys.exit(1)

    # Parsing date
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Format date invalide : {args.start_date}")
        print("   Utiliser le format YYYY-MM-DD (ex: 2024-11-24)")
        sys.exit(1)

    # Vérifier que c'est un lundi
    if start_date.weekday() != 0:
        print(f"⚠️ Attention : {args.start_date} n'est pas un lundi")
        print(f"   Jour détecté : {start_date.strftime('%A')}")
        response = input("Continuer quand même ? (o/n) : ")
        if response.lower() != "o":
            sys.exit(0)

    # Déterminer project_root
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = Path(__file__).parent.parent

    if not project_root.exists():
        print(f"❌ Répertoire projet non trouvé : {project_root}")
        sys.exit(1)

    # Exécuter planification
    planner = WeeklyPlanner(args.week_id, start_date, project_root)
    planner.run()


if __name__ == "__main__":
    main()
