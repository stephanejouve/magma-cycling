# 📊 PROMPT CLAUDE CODE - WEEKLY ANALYSIS SYSTEM (PHASE 2)

**Phase :** Prompt 2 - Phase 2 (Weekly Analysis Automation)  
**Objectif :** Système complet d'analyse hebdomadaire avec 6 reports automatisés  
**Durée estimée :** 2-3 heures  
**Priorité :** 🔥 HIGH (dépend Phase 1 complétée)

---

## 🎯 MISSION

Créer un système complet d'analyse hebdomadaire qui génère automatiquement 6 reports markdown en exploitant l'infrastructure v2 (Phase 1) :

1. **Créer `analyzers/weekly_aggregator.py`** - Agrégation données hebdomadaires
2. **Créer `analyzers/weekly_analyzer.py`** - Génération 6 reports
3. **Créer `workflows/workflow_weekly.py`** - CLI + orchestration
4. **Deprecate `weekly_analysis.py`** - Marquer legacy (E)
5. **Tests complets** - Coverage ≥70%

---

## 📁 CONTEXTE PROJET

### **Infrastructure v2 Disponible (Phase 1)**
```
✅ core/timeline_injector.py - Chronological injection
✅ core/data_aggregator.py - Abstract aggregator
✅ core/prompt_generator.py - Composable prompts
✅ analyzers/daily_aggregator.py - Daily analysis

Git: commit b3abc9f (v2.1.0-core-infrastructure)
Tests: Passing
```

### **État Actuel**
```
Location: ~/cyclisme-training-logs/
Valid files: 21/51 (41.2%)
Gartner I: 20 files
Gartner M: 0 files (dette résolue ✅)
weekly_analysis.py: 25,190 bytes (à deprecate)
```

### **Objectif Phase 2**
```
Système automatisé:
  Input:  --week S073 --start-date 2025-01-06
  Output: 6 fichiers markdown (workout_history, metrics, learnings, etc.)
  
Remplace:
  - weekly_analysis.py (manuel)
  - weekly_planner.py (partiel)
  - prepare_weekly_report.py (partiel)
```

---

## 📋 ÉTAPE 1 : CRÉER `analyzers/weekly_aggregator.py`

### **Fichier à créer :** `cyclisme_training_logs/analyzers/weekly_aggregator.py`

**Objectif :** Implémentation concrète `WeeklyDataAggregator` qui collecte et agrège données hebdomadaires

### **Contenu complet :**

```python
"""
Weekly workout data aggregator for comprehensive analysis.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Agrégateur hebdomadaire implémentant DataAggregator pour collecter
et traiter données complètes d'une semaine d'entraînement. Collecte
7 workouts, métriques évolution (CTL/ATL/TSB), feedback athlète,
et génère structure pour 6 reports.

Examples:
    Basic weekly aggregation::

        from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
        from datetime import date
        
        # Agréger semaine S073
        aggregator = WeeklyAggregator(
            week="S073",
            start_date=date(2025, 1, 6)
        )
        
        result = aggregator.aggregate()
        
        if result.success:
            # Données disponibles
            workouts = result.data['processed']['workouts']
            metrics = result.data['processed']['metrics_evolution']
            learnings = result.data['processed']['learnings']

    Advanced with custom config::

        from pathlib import Path
        
        # Configuration personnalisée
        aggregator = WeeklyAggregator(
            week="S073",
            start_date=date(2025, 1, 6),
            data_dir=Path("~/training-logs"),
            config={
                'include_feedback': True,
                'compute_trends': True,
                'validate_compliance': True
            }
        )
        
        result = aggregator.aggregate()
        
        # Accès détaillé
        weekly_data = result.data['processed']
        print(f"Total TSS: {weekly_data['summary']['total_tss']}")
        print(f"Compliance: {weekly_data['compliance']['rate']:.1f}%")

    Integration with analyzer::

        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer
        
        # Pipeline complet
        aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
        aggregation = aggregator.aggregate()
        
        # Passer au analyzer
        analyzer = WeeklyAnalyzer(aggregation.data['processed'])
        reports = analyzer.generate_all_reports()

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging

from cyclisme_training_logs.core.data_aggregator import DataAggregator
from cyclisme_training_logs.sync_intervals import IntervalsAPI

logger = logging.getLogger(__name__)


class WeeklyAggregator(DataAggregator):
    """
    Agrégateur hebdomadaire pour analyse complète semaine.
    
    Collecte et agrège :
    - 7 workouts de la semaine (activités Intervals.icu)
    - Métriques évolution quotidienne (CTL/ATL/TSB)
    - Feedback athlète pour chaque séance
    - Données wellness (sommeil, poids, HRV)
    - Compliance planifié vs exécuté
    
    Structure données pour 6 reports :
    1. workout_history - Chronologie détaillée
    2. metrics_evolution - Évolution métriques
    3. training_learnings - Enseignements techniques
    4. protocol_adaptations - Ajustements protocoles
    5. transition - Recommandations semaine suivante
    6. bilan_final - Synthèse globale
    """
    
    def __init__(
        self,
        week: str,
        start_date: date,
        data_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialiser agrégateur weekly.
        
        Args:
            week: Numéro semaine (ex: S073)
            start_date: Date début semaine (lundi)
            data_dir: Répertoire données (défaut: ~/training-logs)
            config: Configuration optionnelle
        """
        super().__init__(data_dir=data_dir, config=config)
        self.week = week
        self.start_date = start_date
        self.end_date = start_date + timedelta(days=6)
        self.api = IntervalsAPI()
    
    def collect_raw_data(self) -> Dict[str, Any]:
        """
        Collecter données brutes hebdomadaires.
        
        Returns:
            Dict avec :
            - activities: Liste 7 activités
            - metrics_daily: Évolution quotidienne CTL/ATL/TSB
            - feedback: Feedback athlète par séance
            - wellness: Données wellness quotidiennes
            - planned: Workouts planifiés
        """
        raw_data = {}
        
        # 1. Activités hebdomadaires
        try:
            logger.info(f"Fetching activities for week {self.week}")
            activities = self._fetch_weekly_activities()
            raw_data['activities'] = activities
            logger.info(f"Collected {len(activities)} activities")
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            self.errors.append(f"Activities fetch error: {e}")
            raw_data['activities'] = []
        
        # 2. Métriques quotidiennes
        try:
            logger.info("Fetching daily metrics evolution")
            metrics_daily = self._fetch_daily_metrics()
            raw_data['metrics_daily'] = metrics_daily
        except Exception as e:
            logger.warning(f"Failed to fetch metrics: {e}")
            self.warnings.append(f"Metrics incomplete: {e}")
            raw_data['metrics_daily'] = []
        
        # 3. Feedback athlète
        try:
            feedback = self._load_weekly_feedback()
            raw_data['feedback'] = feedback
            logger.info(f"Loaded feedback for {len(feedback)} sessions")
        except Exception as e:
            logger.warning(f"No feedback found: {e}")
            self.warnings.append("No athlete feedback available")
            raw_data['feedback'] = {}
        
        # 4. Wellness data
        try:
            wellness = self._fetch_wellness_data()
            raw_data['wellness'] = wellness
        except Exception as e:
            logger.warning(f"No wellness data: {e}")
            raw_data['wellness'] = {}
        
        # 5. Planned workouts (compliance)
        if self.config.get('validate_compliance', True):
            try:
                planned = self._fetch_planned_workouts()
                raw_data['planned'] = planned
            except Exception as e:
                logger.warning(f"No planned workouts: {e}")
                raw_data['planned'] = []
        
        return raw_data
    
    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traiter données brutes hebdomadaires.
        
        Args:
            raw_data: Données collectées
            
        Returns:
            Données structurées pour 6 reports
        """
        processed = {}
        
        # 1. Summary général
        processed['summary'] = self._compute_weekly_summary(raw_data['activities'])
        
        # 2. Workouts détaillés (pour workout_history)
        processed['workouts'] = self._process_workouts_detailed(
            raw_data['activities'],
            raw_data.get('feedback', {})
        )
        
        # 3. Metrics evolution (pour metrics_evolution)
        processed['metrics_evolution'] = self._process_metrics_evolution(
            raw_data.get('metrics_daily', [])
        )
        
        # 4. Training learnings (pour training_learnings)
        processed['learnings'] = self._extract_training_learnings(
            raw_data['activities'],
            raw_data.get('feedback', {})
        )
        
        # 5. Protocol adaptations (pour protocol_adaptations)
        processed['protocol_adaptations'] = self._identify_protocol_changes(
            processed['learnings'],
            processed['metrics_evolution']
        )
        
        # 6. Compliance (pour transition)
        if 'planned' in raw_data:
            processed['compliance'] = self._compute_compliance(
                raw_data['activities'],
                raw_data['planned']
            )
        
        # 7. Transition data (pour transition + bilan)
        processed['transition'] = self._prepare_transition_data(
            processed['summary'],
            processed['metrics_evolution'],
            processed['learnings']
        )
        
        # 8. Wellness insights
        if raw_data.get('wellness'):
            processed['wellness_insights'] = self._analyze_wellness(
                raw_data['wellness']
            )
        
        return processed
    
    def format_output(self, processed_data: Dict[str, Any]) -> str:
        """
        Formater sortie markdown (summary).
        
        Args:
            processed_data: Données traitées
            
        Returns:
            Markdown summary
        """
        summary = processed_data.get('summary', {})
        
        output = [f"# Semaine {self.week} - Summary\n"]
        
        # Période
        output.append(f"**Période :** {self.start_date} → {self.end_date}\n")
        
        # Metrics
        output.append("## Métriques Globales\n")
        output.append(f"- **Séances :** {summary.get('total_sessions', 0)}")
        output.append(f"- **TSS total :** {summary.get('total_tss', 0)}")
        output.append(f"- **Durée totale :** {summary.get('total_duration', 0) // 60} min")
        output.append(f"- **TSS moyen :** {summary.get('avg_tss', 0):.1f}")
        
        # CTL/ATL/TSB
        if 'final_metrics' in summary:
            metrics = summary['final_metrics']
            output.append("\n## Forme")
            output.append(f"- **CTL :** {metrics.get('ctl', 0):.1f}")
            output.append(f"- **ATL :** {metrics.get('atl', 0):.1f}")
            output.append(f"- **TSB :** {metrics.get('tsb', 0):.1f}")
        
        return "\n".join(output)
    
    # ==================== MÉTHODES PRIVÉES ====================
    
    def _fetch_weekly_activities(self) -> List[Dict[str, Any]]:
        """Fetch activités semaine depuis Intervals.icu."""
        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()
        
        activities = self.api.get_activities(
            oldest=start_str,
            newest=end_str
        )
        
        # Trier par date
        activities.sort(key=lambda x: x.get('start_date_local', ''))
        
        return activities
    
    def _fetch_daily_metrics(self) -> List[Dict[str, Any]]:
        """Fetch métriques quotidiennes (CTL/ATL/TSB)."""
        metrics = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            try:
                wellness = self.api.get_wellness(current_date.isoformat())
                if wellness:
                    metrics.append({
                        'date': current_date.isoformat(),
                        'ctl': wellness.get('ctl', 0),
                        'atl': wellness.get('atl', 0),
                        'tsb': wellness.get('tsb', 0),
                        'ramp_rate': wellness.get('ramp_rate', 0)
                    })
            except Exception as e:
                logger.warning(f"No metrics for {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        return metrics
    
    def _load_weekly_feedback(self) -> Dict[str, Any]:
        """Charger feedback athlète pour la semaine."""
        feedback_dir = self.data_dir / 'feedback'
        if not feedback_dir.exists():
            return {}
        
        feedback = {}
        for feedback_file in feedback_dir.glob('*.json'):
            try:
                with open(feedback_file, 'r') as f:
                    data = json.load(f)
                    activity_id = feedback_file.stem
                    feedback[activity_id] = data
            except Exception as e:
                logger.warning(f"Failed to load {feedback_file}: {e}")
        
        return feedback
    
    def _fetch_wellness_data(self) -> Dict[str, Any]:
        """Fetch données wellness (sommeil, poids, HRV)."""
        wellness = {}
        current_date = self.start_date
        
        while current_date <= self.end_date:
            try:
                data = self.api.get_wellness(current_date.isoformat())
                if data:
                    wellness[current_date.isoformat()] = {
                        'sleep_quality': data.get('sleepQuality', 0),
                        'sleep_hours': data.get('sleepSecs', 0) / 3600,
                        'weight': data.get('weight', 0),
                        'hrv': data.get('hrvSDNN', 0),
                        'resting_hr': data.get('restingHR', 0)
                    }
            except Exception as e:
                logger.warning(f"No wellness for {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        return wellness
    
    def _fetch_planned_workouts(self) -> List[Dict[str, Any]]:
        """Fetch workouts planifiés pour compliance check."""
        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()
        
        planned = self.api.get_events(
            oldest=start_str,
            newest=end_str,
            category='WORKOUT'
        )
        
        return planned
    
    def _compute_weekly_summary(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculer summary hebdomadaire."""
        summary = {
            'total_sessions': len(activities),
            'total_tss': sum(a.get('training_load', 0) for a in activities),
            'total_duration': sum(a.get('moving_time', 0) for a in activities),
            'avg_tss': 0,
            'avg_if': 0,
            'total_distance': sum(a.get('distance', 0) for a in activities)
        }
        
        if activities:
            summary['avg_tss'] = summary['total_tss'] / len(activities)
            
            # IF moyen (si disponible)
            ifs = [a.get('if', 0) for a in activities if a.get('if', 0) > 0]
            if ifs:
                summary['avg_if'] = sum(ifs) / len(ifs)
        
        # Métriques finales (dernière journée)
        if activities:
            last_activity = activities[-1]
            summary['final_metrics'] = {
                'ctl': last_activity.get('ctl', 0),
                'atl': last_activity.get('atl', 0),
                'tsb': last_activity.get('tsb', 0)
            }
        
        return summary
    
    def _process_workouts_detailed(
        self,
        activities: List[Dict[str, Any]],
        feedback: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Traiter workouts avec détails pour workout_history."""
        workouts = []
        
        for i, activity in enumerate(activities, 1):
            activity_id = str(activity.get('id', ''))
            
            workout = {
                'session_number': i,
                'date': activity.get('start_date_local', ''),
                'activity_id': activity_id,
                'name': activity.get('name', 'Unknown'),
                'type': activity.get('type', 'Ride'),
                'duration': activity.get('moving_time', 0),
                'tss': activity.get('training_load', 0),
                'if': activity.get('if', 0),
                'normalized_power': activity.get('normalized_power', 0),
                'average_power': activity.get('average_power', 0),
                'average_hr': activity.get('average_hr', 0),
                'max_hr': activity.get('max_hr', 0)
            }
            
            # Ajouter feedback si disponible
            if activity_id in feedback:
                workout['feedback'] = feedback[activity_id]
            
            workouts.append(workout)
        
        return workouts
    
    def _process_metrics_evolution(
        self,
        metrics_daily: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Traiter évolution métriques."""
        if not metrics_daily:
            return {}
        
        evolution = {
            'daily': metrics_daily,
            'trends': {}
        }
        
        # Calculer tendances
        if len(metrics_daily) >= 2:
            first = metrics_daily[0]
            last = metrics_daily[-1]
            
            evolution['trends'] = {
                'ctl_change': last['ctl'] - first['ctl'],
                'atl_change': last['atl'] - first['atl'],
                'tsb_change': last['tsb'] - first['tsb']
            }
        
        return evolution
    
    def _extract_training_learnings(
        self,
        activities: List[Dict[str, Any]],
        feedback: Dict[str, Any]
    ) -> List[str]:
        """Extraire enseignements training (pour AI analysis)."""
        learnings = []
        
        # Patterns répétés
        high_tss_days = [
            a for a in activities 
            if a.get('training_load', 0) > 80
        ]
        
        if high_tss_days:
            learnings.append(
                f"{len(high_tss_days)} séances haute charge (TSS >80)"
            )
        
        # IF élevés
        high_if_days = [
            a for a in activities
            if a.get('if', 0) > 1.0
        ]
        
        if high_if_days:
            learnings.append(
                f"{len(high_if_days)} séances intensité élevée (IF >1.0)"
            )
        
        # Feedback patterns
        low_rpe = [
            fid for fid, f in feedback.items()
            if f.get('rpe', 10) <= 3
        ]
        
        if low_rpe:
            learnings.append(
                f"{len(low_rpe)} séances RPE faible (≤3)"
            )
        
        return learnings
    
    def _identify_protocol_changes(
        self,
        learnings: List[str],
        metrics_evolution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identifier changements protocoles nécessaires."""
        adaptations = []
        
        # Check TSB trends
        trends = metrics_evolution.get('trends', {})
        tsb_change = trends.get('tsb_change', 0)
        
        if tsb_change < -10:
            adaptations.append({
                'type': 'recovery',
                'reason': f'TSB dropped {tsb_change:.1f} points',
                'recommendation': 'Add recovery day next week'
            })
        
        return adaptations
    
    def _compute_compliance(
        self,
        activities: List[Dict[str, Any]],
        planned: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculer compliance planifié vs exécuté."""
        compliance = {
            'planned_count': len(planned),
            'executed_count': len(activities),
            'rate': 0,
            'missed': [],
            'extra': []
        }
        
        if planned:
            compliance['rate'] = (len(activities) / len(planned)) * 100
        
        # Identifier séances manquées (simplification)
        if len(activities) < len(planned):
            compliance['missed'] = planned[len(activities):]
        
        return compliance
    
    def _prepare_transition_data(
        self,
        summary: Dict[str, Any],
        metrics_evolution: Dict[str, Any],
        learnings: List[str]
    ) -> Dict[str, Any]:
        """Préparer données transition semaine suivante."""
        transition = {
            'current_state': {
                'total_tss': summary.get('total_tss', 0),
                'avg_tss': summary.get('avg_tss', 0),
                'final_tsb': summary.get('final_metrics', {}).get('tsb', 0)
            },
            'recommendations': [],
            'focus_areas': learnings[:3] if learnings else []
        }
        
        # Recommandations basées sur TSB
        tsb = transition['current_state']['final_tsb']
        
        if tsb < -15:
            transition['recommendations'].append(
                'Recovery week recommended (TSB very low)'
            )
        elif tsb > 10:
            transition['recommendations'].append(
                'Ready for intensity increase (TSB positive)'
            )
        
        return transition
    
    def _analyze_wellness(self, wellness: Dict[str, Any]) -> Dict[str, Any]:
        """Analyser données wellness."""
        insights = {
            'sleep_quality_avg': 0,
            'sleep_hours_avg': 0,
            'weight_trend': 0,
            'hrv_avg': 0
        }
        
        if not wellness:
            return insights
        
        # Moyennes
        sleep_qualities = [
            w['sleep_quality'] for w in wellness.values()
            if w.get('sleep_quality', 0) > 0
        ]
        
        if sleep_qualities:
            insights['sleep_quality_avg'] = sum(sleep_qualities) / len(sleep_qualities)
        
        sleep_hours = [
            w['sleep_hours'] for w in wellness.values()
            if w.get('sleep_hours', 0) > 0
        ]
        
        if sleep_hours:
            insights['sleep_hours_avg'] = sum(sleep_hours) / len(sleep_hours)
        
        # Tendance poids
        weights = [
            (date, w['weight'])
            for date, w in wellness.items()
            if w.get('weight', 0) > 0
        ]
        
        if len(weights) >= 2:
            weights.sort()
            insights['weight_trend'] = weights[-1][1] - weights[0][1]
        
        return insights
```

### **Tests à créer :** `tests/test_weekly_aggregator.py`

```python
"""
Tests for WeeklyAggregator.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest
from datetime import date
from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator


@pytest.fixture
def sample_week_data():
    """Données semaine pour tests."""
    return {
        'week': 'S073',
        'start_date': date(2025, 1, 6)
    }


def test_weekly_aggregator_initialization(sample_week_data):
    """Test initialisation WeeklyAggregator."""
    aggregator = WeeklyAggregator(
        week=sample_week_data['week'],
        start_date=sample_week_data['start_date']
    )
    
    assert aggregator.week == 'S073'
    assert aggregator.start_date == date(2025, 1, 6)
    assert aggregator.end_date == date(2025, 1, 12)


def test_compute_weekly_summary():
    """Test calcul summary hebdomadaire."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
    
    activities = [
        {'training_load': 45, 'moving_time': 3600, 'if': 1.2},
        {'training_load': 50, 'moving_time': 4200, 'if': 1.1},
    ]
    
    summary = aggregator._compute_weekly_summary(activities)
    
    assert summary['total_sessions'] == 2
    assert summary['total_tss'] == 95
    assert summary['avg_tss'] == 47.5


def test_process_workouts_detailed():
    """Test traitement workouts détaillés."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
    
    activities = [
        {
            'id': 'i123',
            'name': 'Sweet Spot',
            'training_load': 45,
            'if': 1.2,
            'start_date_local': '2025-01-06'
        }
    ]
    
    feedback = {
        'i123': {'rpe': 6, 'comments': 'Good session'}
    }
    
    workouts = aggregator._process_workouts_detailed(activities, feedback)
    
    assert len(workouts) == 1
    assert workouts[0]['tss'] == 45
    assert workouts[0]['feedback']['rpe'] == 6
```

---

## 📋 ÉTAPE 2 : CRÉER `analyzers/weekly_analyzer.py`

### **Fichier à créer :** `cyclisme_training_logs/analyzers/weekly_analyzer.py`

**Objectif :** Orchestrateur génération 6 reports hebdomadaires

### **Contenu complet :**

```python
"""
Weekly analyzer orchestrating 6 automated markdown reports.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Orchestrateur principal pour génération automatisée des 6 reports
hebdomadaires standards : workout_history, metrics_evolution,
training_learnings, protocol_adaptations, transition, bilan_final.

Examples:
    Generate all 6 reports::

        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer
        from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
        from datetime import date
        
        # Pipeline complet
        aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
        aggregation = aggregator.aggregate()
        
        # Générer reports
        analyzer = WeeklyAnalyzer(
            week="S073",
            weekly_data=aggregation.data['processed']
        )
        
        reports = analyzer.generate_all_reports()
        
        # 6 fichiers générés
        print(reports['workout_history'])
        print(reports['metrics_evolution'])
        print(reports['training_learnings'])

    Generate single report::

        # Générer seulement workout_history
        analyzer = WeeklyAnalyzer(week="S073", weekly_data=data)
        
        history = analyzer.generate_workout_history()
        print(history)

    Save reports to disk::

        from pathlib import Path
        
        # Sauvegarder tous reports
        reports = analyzer.generate_all_reports()
        output_dir = Path("~/training-logs/weekly-reports/S073")
        
        analyzer.save_reports(reports, output_dir)

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import logging

from cyclisme_training_logs.core.prompt_generator import PromptGenerator

logger = logging.getLogger(__name__)


class WeeklyAnalyzer:
    """
    Analyseur hebdomadaire générant 6 reports markdown.
    
    Reports générés :
    1. workout_history_sXXX.md - Chronologie détaillée séances
    2. metrics_evolution_sXXX.md - Évolution CTL/ATL/TSB
    3. training_learnings_sXXX.md - Enseignements techniques
    4. protocol_adaptations_sXXX.md - Ajustements protocoles
    5. transition_sXXX_sYYY.md - Recommandations semaine suivante
    6. bilan_final_sXXX.md - Synthèse globale
    """
    
    def __init__(
        self,
        week: str,
        weekly_data: Dict[str, Any],
        prompt_generator: Optional[PromptGenerator] = None
    ):
        """
        Initialiser analyzer.
        
        Args:
            week: Numéro semaine (S073)
            weekly_data: Données traitées par WeeklyAggregator
            prompt_generator: Generator prompts (créé si None)
        """
        self.week = week
        self.data = weekly_data
        self.prompt_generator = prompt_generator or PromptGenerator()
    
    def generate_all_reports(self) -> Dict[str, str]:
        """
        Générer les 6 reports complets.
        
        Returns:
            Dict avec clés : workout_history, metrics_evolution,
            training_learnings, protocol_adaptations, transition, bilan_final
        """
        logger.info(f"Generating all 6 reports for {self.week}")
        
        reports = {
            'workout_history': self.generate_workout_history(),
            'metrics_evolution': self.generate_metrics_evolution(),
            'training_learnings': self.generate_training_learnings(),
            'protocol_adaptations': self.generate_protocol_adaptations(),
            'transition': self.generate_transition(),
            'bilan_final': self.generate_bilan_final()
        }
        
        logger.info("All reports generated successfully")
        return reports
    
    def generate_workout_history(self) -> str:
        """
        Générer workout_history_sXXX.md.
        
        Format :
        # Historique Entraînements SXXX
        
        ## SXXX-01 (YYYY-MM-DD)
        **Durée:** XXmin | **TSS:** XX | **IF:** X.XX
        
        ### Métriques Pré-séance
        ...
        """
        workouts = self.data.get('workouts', [])
        
        lines = [
            f"# Historique Entraînements {self.week}\n",
            f"**Période :** {self._get_period()}\n",
            f"**Nombre séances :** {len(workouts)}\n"
        ]
        
        for workout in workouts:
            lines.append(f"\n## {self.week}-{workout['session_number']:02d} ({workout['date']})\n")
            
            # Métriques principales
            duration_min = workout['duration'] // 60
            lines.append(f"**Durée:** {duration_min}min | **TSS:** {workout['tss']} | **IF:** {workout.get('if', 0):.2f}\n")
            
            # Puissance
            if workout.get('normalized_power', 0) > 0:
                lines.append("\n### Puissance")
                lines.append(f"- Normalisée: {workout['normalized_power']}W")
                lines.append(f"- Moyenne: {workout.get('average_power', 0)}W\n")
            
            # FC
            if workout.get('average_hr', 0) > 0:
                lines.append("\n### Fréquence Cardiaque")
                lines.append(f"- Moyenne: {workout['average_hr']} bpm")
                lines.append(f"- Max: {workout.get('max_hr', 0)} bpm\n")
            
            # Feedback
            if 'feedback' in workout:
                feedback = workout['feedback']
                lines.append("\n### Feedback Athlète")
                
                if 'rpe' in feedback:
                    lines.append(f"- RPE: {feedback['rpe']}/10")
                
                if 'comments' in feedback:
                    lines.append(f"- Notes: {feedback['comments']}\n")
        
        return "\n".join(lines)
    
    def generate_metrics_evolution(self) -> str:
        """
        Générer metrics_evolution_sXXX.md.
        
        Format :
        # Évolution Métriques SXXX
        
        ## CTL/ATL/TSB Quotidien
        | Date | CTL | ATL | TSB |
        """
        metrics_evolution = self.data.get('metrics_evolution', {})
        daily = metrics_evolution.get('daily', [])
        trends = metrics_evolution.get('trends', {})
        
        lines = [
            f"# Évolution Métriques {self.week}\n",
            "## CTL/ATL/TSB Quotidien\n"
        ]
        
        if daily:
            # Table
            lines.append("| Date | CTL | ATL | TSB |")
            lines.append("|------|-----|-----|-----|")
            
            for day in daily:
                lines.append(
                    f"| {day['date']} | {day['ctl']:.1f} | "
                    f"{day['atl']:.1f} | {day['tsb']:.1f} |"
                )
            
            lines.append("")
        
        # Tendances
        if trends:
            lines.append("\n## Tendances Hebdomadaires\n")
            lines.append(f"- **Variation CTL :** {trends.get('ctl_change', 0):+.1f}")
            lines.append(f"- **Variation ATL :** {trends.get('atl_change', 0):+.1f}")
            lines.append(f"- **Variation TSB :** {trends.get('tsb_change', 0):+.1f}\n")
        
        # Wellness insights
        if 'wellness_insights' in self.data:
            insights = self.data['wellness_insights']
            lines.append("\n## Wellness\n")
            
            if insights.get('sleep_hours_avg', 0) > 0:
                lines.append(f"- **Sommeil moyen :** {insights['sleep_hours_avg']:.1f}h")
            
            if insights.get('weight_trend', 0) != 0:
                lines.append(f"- **Évolution poids :** {insights['weight_trend']:+.1f}kg\n")
        
        return "\n".join(lines)
    
    def generate_training_learnings(self) -> str:
        """
        Générer training_learnings_sXXX.md.
        
        Format :
        # Enseignements d'Entraînement SXXX
        
        ## Découvertes Majeures
        - Point 1
        - Point 2
        """
        learnings = self.data.get('learnings', [])
        
        lines = [
            f"# Enseignements d'Entraînement {self.week}\n",
            "## Découvertes Majeures\n"
        ]
        
        if learnings:
            for learning in learnings:
                lines.append(f"- {learning}")
        else:
            lines.append("*Aucun enseignement spécifique identifié*")
        
        lines.append("")
        
        # Patterns techniques (à enrichir avec AI analysis)
        lines.append("\n## Patterns Techniques\n")
        lines.append("*À compléter avec analyse IA détaillée*\n")
        
        return "\n".join(lines)
    
    def generate_protocol_adaptations(self) -> str:
        """
        Générer protocol_adaptations_sXXX.md.
        
        Format :
        # Adaptations Protocoles SXXX
        
        ## Ajustements Identifiés
        - Type: recovery
          Raison: TSB dropped
          Recommandation: Add recovery day
        """
        adaptations = self.data.get('protocol_adaptations', [])
        
        lines = [
            f"# Adaptations Protocoles {self.week}\n",
            "## Ajustements Identifiés\n"
        ]
        
        if adaptations:
            for adaptation in adaptations:
                lines.append(f"\n### {adaptation.get('type', 'Unknown').title()}")
                lines.append(f"- **Raison :** {adaptation.get('reason', 'N/A')}")
                lines.append(f"- **Recommandation :** {adaptation.get('recommendation', 'N/A')}\n")
        else:
            lines.append("*Aucune adaptation protocole nécessaire*\n")
        
        return "\n".join(lines)
    
    def generate_transition(self) -> str:
        """
        Générer transition_sXXX_sYYY.md.
        
        Format :
        # Transition SXXX → SYYY
        
        ## État Final SXXX
        - TSS total: XXX
        - TSB final: XX
        
        ## Recommandations SYYY
        - Focus 1
        - Focus 2
        """
        transition = self.data.get('transition', {})
        current_state = transition.get('current_state', {})
        recommendations = transition.get('recommendations', [])
        focus_areas = transition.get('focus_areas', [])
        
        # Calculer numéro semaine suivante
        week_num = int(self.week[1:]) if self.week.startswith('S') else 0
        next_week = f"S{week_num + 1:03d}"
        
        lines = [
            f"# Transition {self.week} → {next_week}\n",
            f"## État Final {self.week}\n"
        ]
        
        # État actuel
        lines.append(f"- **TSS total :** {current_state.get('total_tss', 0)}")
        lines.append(f"- **TSS moyen :** {current_state.get('avg_tss', 0):.1f}")
        lines.append(f"- **TSB final :** {current_state.get('final_tsb', 0):.1f}\n")
        
        # Recommandations
        lines.append(f"\n## Recommandations {next_week}\n")
        
        if recommendations:
            for rec in recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("- Continuer progression actuelle")
        
        lines.append("")
        
        # Focus areas
        if focus_areas:
            lines.append("\n## Points d'Attention\n")
            for focus in focus_areas:
                lines.append(f"- {focus}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_bilan_final(self) -> str:
        """
        Générer bilan_final_sXXX.md.
        
        Format :
        # Bilan Final SXXX
        
        ## Objectifs vs Réalisé
        ## Métriques Clés
        ## Conclusion
        """
        summary = self.data.get('summary', {})
        compliance = self.data.get('compliance', {})
        
        lines = [
            f"# Bilan Final {self.week}\n",
            "## Objectifs vs Réalisé\n"
        ]
        
        # Compliance
        if compliance:
            rate = compliance.get('rate', 0)
            lines.append(f"- **Compliance :** {rate:.1f}%")
            lines.append(f"- **Séances planifiées :** {compliance.get('planned_count', 0)}")
            lines.append(f"- **Séances exécutées :** {compliance.get('executed_count', 0)}\n")
        
        # Métriques clés
        lines.append("\n## Métriques Clés\n")
        lines.append(f"- **TSS total :** {summary.get('total_tss', 0)}")
        lines.append(f"- **TSS moyen :** {summary.get('avg_tss', 0):.1f}")
        lines.append(f"- **IF moyen :** {summary.get('avg_if', 0):.2f}\n")
        
        # Conclusion
        lines.append("\n## Conclusion\n")
        lines.append("*Semaine complétée avec succès.*\n")
        
        return "\n".join(lines)
    
    def save_reports(self, reports: Dict[str, str], output_dir: Path) -> None:
        """
        Sauvegarder reports sur disque.
        
        Args:
            reports: Dict reports générés
            output_dir: Répertoire destination
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for report_name, content in reports.items():
            filename = f"{report_name}_{self.week.lower()}.md"
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Saved {filename}")
    
    def _get_period(self) -> str:
        """Helper pour obtenir période formatée."""
        workouts = self.data.get('workouts', [])
        if not workouts:
            return "N/A"
        
        first_date = workouts[0].get('date', '')
        last_date = workouts[-1].get('date', '')
        
        return f"{first_date} → {last_date}"
```

### **Tests à créer :** `tests/test_weekly_analyzer.py`

```python
"""
Tests for WeeklyAnalyzer.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest
from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer


@pytest.fixture
def sample_weekly_data():
    """Données hebdomadaires pour tests."""
    return {
        'summary': {
            'total_tss': 320,
            'avg_tss': 45.7,
            'avg_if': 1.15
        },
        'workouts': [
            {
                'session_number': 1,
                'date': '2025-01-06',
                'tss': 45,
                'if': 1.2,
                'duration': 3600
            }
        ],
        'metrics_evolution': {
            'daily': [
                {'date': '2025-01-06', 'ctl': 60, 'atl': 58, 'tsb': 2}
            ],
            'trends': {
                'ctl_change': 2.5,
                'atl_change': 1.8,
                'tsb_change': 0.7
            }
        }
    }


def test_weekly_analyzer_initialization(sample_weekly_data):
    """Test initialisation WeeklyAnalyzer."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)
    
    assert analyzer.week == "S073"
    assert analyzer.data == sample_weekly_data


def test_generate_workout_history(sample_weekly_data):
    """Test génération workout_history."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)
    
    history = analyzer.generate_workout_history()
    
    assert "# Historique Entraînements S073" in history
    assert "S073-01" in history
    assert "TSS:** 45" in history


def test_generate_all_reports(sample_weekly_data):
    """Test génération complète 6 reports."""
    analyzer = WeeklyAnalyzer(week="S073", weekly_data=sample_weekly_data)
    
    reports = analyzer.generate_all_reports()
    
    assert len(reports) == 6
    assert 'workout_history' in reports
    assert 'metrics_evolution' in reports
    assert 'training_learnings' in reports
    assert 'protocol_adaptations' in reports
    assert 'transition' in reports
    assert 'bilan_final' in reports
```

---

## 📋 ÉTAPE 3 : CRÉER `workflows/workflow_weekly.py`

### **Fichier à créer :** `cyclisme_training_logs/workflows/workflow_weekly.py`

**Objectif :** CLI + orchestration complète workflow weekly

### **Contenu complet :**

```python
"""
Weekly analysis workflow CLI and orchestration.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Workflow complet analyse hebdomadaire automatisée. Orchestre :
WeeklyAggregator → WeeklyAnalyzer → 6 reports markdown.
Remplace weekly_analysis.py legacy.

Examples:
    Command-line usage::

        # Analyse semaine courante
        poetry run weekly-analysis --week current
        
        # Analyse semaine spécifique
        poetry run weekly-analysis --week S073 --start-date 2025-01-06
        
        # Avec AI analysis (clipboard)
        poetry run weekly-analysis --week S073 --ai-analysis

    Programmatic usage::

        from cyclisme_training_logs.workflows.workflow_weekly import run_weekly_analysis
        from datetime import date
        
        # Exécution programmatique
        reports = run_weekly_analysis(
            week="S073",
            start_date=date(2025, 1, 6),
            save_reports=True
        )
        
        print(f"Generated {len(reports)} reports")

    Integration with existing::

        # Compatible avec workflow actuel
        from cyclisme_training_logs.workflows.workflow_weekly import WeeklyWorkflow
        
        workflow = WeeklyWorkflow(week="S073", start_date=date(2025, 1, 6))
        workflow.run()

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)
"""

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer
from cyclisme_training_logs.config import DataRepoConfig

logger = logging.getLogger(__name__)


class WeeklyWorkflow:
    """
    Workflow complet analyse hebdomadaire.
    
    Pipeline :
    1. WeeklyAggregator - Collecte et agrégation données
    2. WeeklyAnalyzer - Génération 6 reports
    3. Save reports - Sauvegarde markdown
    4. Optional: AI analysis via clipboard
    """
    
    def __init__(
        self,
        week: str,
        start_date: date,
        config: Optional[DataRepoConfig] = None,
        ai_analysis: bool = False
    ):
        """
        Initialiser workflow.
        
        Args:
            week: Numéro semaine (S073)
            start_date: Date début (lundi)
            config: Configuration (créée si None)
            ai_analysis: Activer AI analysis via clipboard
        """
        self.week = week
        self.start_date = start_date
        self.config = config or DataRepoConfig()
        self.ai_analysis = ai_analysis
    
    def run(self) -> Dict[str, str]:
        """
        Exécuter workflow complet.
        
        Returns:
            Dict avec 6 reports générés
        """
        logger.info(f"Starting weekly workflow for {self.week}")
        
        # 1. Aggregation
        logger.info("Step 1/3: Aggregating weekly data")
        aggregator = WeeklyAggregator(
            week=self.week,
            start_date=self.start_date,
            data_dir=self.config.data_repo_path
        )
        
        aggregation = aggregator.aggregate()
        
        if not aggregation.success:
            logger.error(f"Aggregation failed: {aggregation.errors}")
            raise RuntimeError("Weekly aggregation failed")
        
        # 2. Analysis
        logger.info("Step 2/3: Generating reports")
        analyzer = WeeklyAnalyzer(
            week=self.week,
            weekly_data=aggregation.data['processed']
        )
        
        reports = analyzer.generate_all_reports()
        
        # 3. Save
        logger.info("Step 3/3: Saving reports")
        output_dir = self.config.data_repo_path / 'weekly-reports' / self.week
        analyzer.save_reports(reports, output_dir)
        
        logger.info(f"Weekly workflow completed: {len(reports)} reports saved")
        
        # 4. Optional: AI analysis
        if self.ai_analysis:
            self._trigger_ai_analysis(reports)
        
        return reports
    
    def _trigger_ai_analysis(self, reports: Dict[str, str]) -> None:
        """Trigger AI analysis via clipboard (optionnel)."""
        try:
            from cyclisme_training_logs.ai_providers.clipboard import copy_to_clipboard
            
            # Combiner prompts pour AI
            combined = "\n\n---\n\n".join([
                f"# {name.upper()}\n{content}"
                for name, content in reports.items()
            ])
            
            copy_to_clipboard(combined)
            logger.info("Reports copied to clipboard for AI analysis")
        except Exception as e:
            logger.warning(f"AI analysis clipboard failed: {e}")


def run_weekly_analysis(
    week: str,
    start_date: date,
    save_reports: bool = True,
    ai_analysis: bool = False
) -> Dict[str, str]:
    """
    Fonction utilitaire pour workflow weekly.
    
    Args:
        week: Numéro semaine (S073)
        start_date: Date début
        save_reports: Sauvegarder reports sur disque
        ai_analysis: Activer AI analysis
        
    Returns:
        Dict avec 6 reports générés
    """
    workflow = WeeklyWorkflow(
        week=week,
        start_date=start_date,
        ai_analysis=ai_analysis
    )
    
    return workflow.run()


def get_current_week_info() -> tuple[str, date]:
    """
    Calculer numéro semaine courante et date début.
    
    Returns:
        (week, start_date) tuple
    """
    today = date.today()
    
    # Trouver lundi de la semaine
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    
    # Calculer numéro semaine (simplification)
    week_number = monday.isocalendar()[1]
    week = f"S{week_number:03d}"
    
    return week, monday


def main():
    """Entry point CLI."""
    parser = argparse.ArgumentParser(
        description="Weekly analysis workflow - Generate 6 automated reports"
    )
    
    parser.add_argument(
        '--week',
        type=str,
        help='Week number (S073) or "current"',
        default='current'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date YYYY-MM-DD (Monday)',
        default=None
    )
    
    parser.add_argument(
        '--ai-analysis',
        action='store_true',
        help='Enable AI analysis via clipboard'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Déterminer semaine et date
    if args.week == 'current':
        week, start_date = get_current_week_info()
        logger.info(f"Current week detected: {week} (starting {start_date})")
    else:
        week = args.week
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        else:
            logger.error("--start-date required when using custom week")
            return 1
    
    # Exécuter workflow
    try:
        reports = run_weekly_analysis(
            week=week,
            start_date=start_date,
            ai_analysis=args.ai_analysis
        )
        
        print(f"\n✅ Weekly analysis completed for {week}")
        print(f"📊 Generated {len(reports)} reports:")
        for name in reports.keys():
            print(f"   - {name}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Weekly analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
```

### **Tests à créer :** `tests/test_workflow_weekly.py`

```python
"""
Tests for WeeklyWorkflow.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest
from datetime import date
from cyclisme_training_logs.workflows.workflow_weekly import (
    get_current_week_info,
    run_weekly_analysis
)


def test_get_current_week_info():
    """Test calcul semaine courante."""
    week, start_date = get_current_week_info()
    
    assert week.startswith('S')
    assert isinstance(start_date, date)
    assert start_date.weekday() == 0  # Lundi
```

---

## 📋 ÉTAPE 4 : DEPRECATE `weekly_analysis.py`

### **Fichier à modifier :** `cyclisme_training_logs/weekly_analysis.py`

**Objectif :** Marquer comme deprecated (Gartner E)

### **Modifications :**

```python
"""
Legacy weekly analysis script (DEPRECATED - use workflows/workflow_weekly.py).

GARTNER_TIME: E
STATUS: Deprecated
LAST_REVIEW: 2025-12-26
PRIORITY: P4
DEPRECATION_DATE: 2025-12-26
REMOVAL_DATE: 2026-01-26
REPLACEMENT: workflows/workflow_weekly.py
DOCSTRING: v2

⚠️  DEPRECATED - Ce script est remplacé par workflows/workflow_weekly.py
qui utilise l'infrastructure v2 (WeeklyAggregator + WeeklyAnalyzer).

Pour migration :

Old (deprecated)::

    python weekly_analysis.py --week S073

New (recommended)::

    poetry run weekly-analysis --week S073 --start-date 2025-01-06

Programmatic migration::

    # Old
    from cyclisme_training_logs.weekly_analysis import analyze_week
    result = analyze_week("S073")
    
    # New
    from cyclisme_training_logs.workflows.workflow_weekly import run_weekly_analysis
    from datetime import date
    reports = run_weekly_analysis("S073", date(2025, 1, 6))

Author: Stéphane Jouve
Created: 2024-XX-XX
Updated: 2025-12-26 (Marked as deprecated - Phase 2)
"""

import warnings

# Avertissement deprecation
warnings.warn(
    "weekly_analysis.py is deprecated and will be removed on 2026-01-26. "
    "Use workflows/workflow_weekly.py instead.",
    DeprecationWarning,
    stacklevel=2
)

# Code existant préservé pour compatibilité...
# [Garder le code existant intact]
```

---

## 📋 ÉTAPE 5 : SETUP CLI `pyproject.toml`

### **Fichier à modifier :** `pyproject.toml`

**Ajouter dans `[tool.poetry.scripts]` :**

```toml
[tool.poetry.scripts]
# ... scripts existants ...
weekly-analysis = "cyclisme_training_logs.workflows.workflow_weekly:main"
```

---

## ✅ CRITÈRES DE SUCCÈS

### **Fichiers Créés (3 nouveaux + tests)**
- [ ] `analyzers/weekly_aggregator.py` (~600 lignes) avec docstring v2 + tag I/P1
- [ ] `analyzers/weekly_analyzer.py` (~500 lignes) avec docstring v2 + tag I/P1
- [ ] `workflows/workflow_weekly.py` (~300 lignes) avec docstring v2 + tag I/P1
- [ ] `tests/test_weekly_aggregator.py` (8+ tests)
- [ ] `tests/test_weekly_analyzer.py` (8+ tests)
- [ ] `tests/test_workflow_weekly.py` (4+ tests)

### **Fichiers Modifiés**
- [ ] `weekly_analysis.py` → Gartner E (deprecated)
- [ ] `pyproject.toml` → CLI `weekly-analysis` ajouté

### **Fonctionnalités**
- [ ] CLI fonctionnel : `poetry run weekly-analysis --week S073 --start-date 2025-01-06`
- [ ] 6 reports générés automatiquement
- [ ] Integration infrastructure v2 (DataAggregator, PromptGenerator)
- [ ] Backward compatible (weekly_analysis.py fonctionne avec warning)

### **Tests**
- [ ] Tous tests passent : `poetry run pytest`
- [ ] Coverage ≥70% nouveaux fichiers
- [ ] Tests unitaires aggregator (8+)
- [ ] Tests unitaires analyzer (8+)
- [ ] Tests integration workflow (4+)

### **Validation**
- [ ] Gartner tags : `poetry run python scripts/validate_gartner_tags.py`
- [ ] 3 nouveaux fichiers I validés
- [ ] 1 fichier E (deprecated) validé
- [ ] HTML report généré

### **Documentation**
- [ ] Docstrings v2 complètes (3 nouveaux fichiers)
- [ ] Examples minimum 2 code blocks
- [ ] ARCHITECTURE.md mis à jour

### **Git**
- [ ] Commit descriptif
- [ ] Push to origin/main
- [ ] Tag version `v2.2.0-weekly-analysis-system`

---

## 📊 RÉSULTATS ATTENDUS

### **Avant Phase 2**
```
Valid files: 21/51 (41.2%)
Gartner I: 20 files
Gartner E: 0 files
CLI: Aucun weekly analysis automatisé
```

### **Après Phase 2**
```
Valid files: 24/51 (47%)
Gartner I: 23 files (+3 nouveaux)
Gartner E: 1 file (weekly_analysis.py deprecated)
CLI: poetry run weekly-analysis (fonctionnel)
6 reports automatisés: ✅
```

### **Impact Infrastructure**
```
✅ WeeklyAggregator extends DataAggregator
✅ WeeklyAnalyzer utilise PromptGenerator
✅ Workflow utilise TimelineInjector (injection chronologique)
✅ Integration complète infrastructure v2
```

---

## 🎯 WORKFLOW D'UTILISATION

### **Utilisateur - Analyse Semaine Courante**

```bash
# Semaine courante (auto-détection)
poetry run weekly-analysis --week current

# Résultat : 6 fichiers générés
~/training-logs/weekly-reports/S052/
├── workout_history_s052.md
├── metrics_evolution_s052.md
├── training_learnings_s052.md
├── protocol_adaptations_s052.md
├── transition_s052_s053.md
└── bilan_final_s052.md
```

### **Utilisateur - Analyse Semaine Spécifique**

```bash
# Semaine passée
poetry run weekly-analysis --week S073 --start-date 2025-01-06

# Avec AI analysis
poetry run weekly-analysis --week S073 --start-date 2025-01-06 --ai-analysis
```

### **Programmateur - Integration**

```python
from cyclisme_training_logs.workflows.workflow_weekly import run_weekly_analysis
from datetime import date

# Analyse automatisée
reports = run_weekly_analysis(
    week="S073",
    start_date=date(2025, 1, 6)
)

# Utiliser reports
for name, content in reports.items():
    print(f"Report: {name}")
    print(content[:200])  # Preview
```

---

## 📝 NOTES IMPORTANTES

### **Dépendances Phase 1**

**Ce prompt REQUIERT Phase 1 complétée :**
- ✅ `core/data_aggregator.py` → Base class WeeklyAggregator
- ✅ `core/prompt_generator.py` → Utilisé par WeeklyAnalyzer
- ✅ `core/timeline_injector.py` → Injection chronologique reports
- ✅ `analyzers/daily_aggregator.py` → Pattern référence

**Si Phase 1 non complétée :**
- ❌ Imports cassés (`from cyclisme_training_logs.core.data_aggregator`)
- ❌ Tests échouent
- ❌ CLI non fonctionnel

### **Migration Utilisateurs**

**Transition progressive :**
1. **Semaines 1-2** : Les 2 systèmes coexistent
   - weekly_analysis.py fonctionne (avec warning)
   - workflow_weekly.py nouveau système
2. **Semaines 3-4** : Migration utilisateurs
   - Documentation migration
   - Scripts migration automatique
3. **30 jours** : Suppression weekly_analysis.py
   - REMOVAL_DATE: 2026-01-26
   - Seulement workflow_weekly.py

### **AI Analysis Integration**

**Option clipboard préservée :**
- Flag `--ai-analysis` active clipboard
- Compatible workflow actuel
- Génère prompts pour Claude.ai
- Non bloquant si échec

---

## 🚀 ORDRE D'EXÉCUTION RECOMMANDÉ

### **Séquence Optimale**

**1. Création fichiers (90 min)**
- Créer `weekly_aggregator.py` (40 min)
- Créer `weekly_analyzer.py` (30 min)
- Créer `workflow_weekly.py` (20 min)

**2. Tests (45 min)**
- Créer `test_weekly_aggregator.py` (15 min)
- Créer `test_weekly_analyzer.py` (15 min)
- Créer `test_workflow_weekly.py` (15 min)

**3. Modifications (15 min)**
- Deprecate `weekly_analysis.py` (10 min)
- Update `pyproject.toml` (5 min)

**4. Validation (30 min)**
- Tests complets
- Validation Gartner tags
- Test CLI manuel
- HTML report

**5. Documentation (20 min)**
- Update ARCHITECTURE.md
- Git commit
- Tag version

---

## 🎁 BONUS : SCRIPT MIGRATION UTILISATEURS

### **Créer :** `scripts/migrate_weekly_analysis.py`

```python
"""Script migration weekly_analysis.py → workflow_weekly.py."""

import subprocess
import sys

def migrate():
    """Guide migration interactive."""
    print("🔄 Migration weekly_analysis.py → workflow_weekly.py")
    print()
    
    # Test nouveau système
    print("Testing new workflow...")
    result = subprocess.run(
        ["poetry", "run", "weekly-analysis", "--week", "current"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ New workflow functional!")
        print()
        print("Migration complete:")
        print("  Old: python weekly_analysis.py --week S073")
        print("  New: poetry run weekly-analysis --week S073 --start-date YYYY-MM-DD")
    else:
        print("❌ Migration failed")
        print(result.stderr)
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(migrate())
```

---

## 🎯 COMMIT MESSAGE TEMPLATE

```
feat(weekly): Phase 2 - Automated Weekly Analysis System

Implement complete weekly analysis automation with 6 reports:

New Infrastructure (3 files):
- analyzers/weekly_aggregator.py (I/P1) - Weekly data aggregation
- analyzers/weekly_analyzer.py (I/P1) - 6 reports orchestrator
- workflows/workflow_weekly.py (I/P1) - CLI + workflow

Features:
✅ CLI: poetry run weekly-analysis --week S073 --start-date YYYY-MM-DD
✅ 6 automated reports: workout_history, metrics_evolution, learnings, 
   protocol_adaptations, transition, bilan_final
✅ Integration v2 infrastructure (DataAggregator, PromptGenerator)
✅ AI analysis clipboard integration (optional --ai-analysis)

Legacy Deprecation:
⚠️  weekly_analysis.py marked deprecated (E/P4)
   REMOVAL_DATE: 2026-01-26
   REPLACEMENT: workflows/workflow_weekly.py

Tests:
✅ 20+ tests added (aggregator, analyzer, workflow)
✅ Coverage ≥70% new files
✅ All tests passing

Validation:
✅ 3 new files I/P1 (Gartner validation)
✅ 1 file E/P4 (deprecated)
✅ Valid files: 21 → 24 (47%)

Documentation:
✅ Docstrings v2 complete with Examples
✅ ARCHITECTURE.md updated
✅ Migration guide included
```

---

## 🎯 RÉSUMÉ MISSION

**Tu dois :**

1. ✅ Créer 3 fichiers core weekly analysis
2. ✅ Créer 3 fichiers tests complets
3. ✅ Modifier weekly_analysis.py (deprecate)
4. ✅ Update pyproject.toml (CLI)
5. ✅ Valider 6 reports générés
6. ✅ Tests 100% passing
7. ✅ Git commit + tag v2.2.0

**Temps estimé :** 2-3 heures

**Résultat attendu :**
- Weekly analysis 100% automatisé ✅
- 6 reports markdown générés ✅
- CLI fonctionnel ✅
- Infrastructure v2 exploitée ✅
- Legacy deprecated proprement ✅

---

**Prêt à exécuter ?** 🚀
