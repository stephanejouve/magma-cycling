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
from datetime import date, timedelta
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
    """Test calcul summary hebdomadaire avec champs ICU."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    # Utiliser champs Intervals.icu (icu_training_load, icu_intensity en %)
    activities = [
        {'icu_training_load': 45, 'moving_time': 3600, 'icu_intensity': 120, 'distance': 50},
        {'icu_training_load': 50, 'moving_time': 4200, 'icu_intensity': 110, 'distance': 55},
    ]

    summary = aggregator._compute_weekly_summary(activities)

    assert summary['total_sessions'] == 2
    assert summary['total_tss'] == 95
    assert summary['avg_tss'] == 47.5
    assert summary['total_distance'] == 105


def test_process_workouts_detailed():
    """Test traitement workouts détaillés avec champs ICU."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    # Utiliser champs Intervals.icu (icu_ prefix)
    activities = [
        {
            'id': 'i123',
            'name': 'Sweet Spot',
            'icu_training_load': 45,
            'icu_intensity': 120,  # 120% → 1.20 IF
            'start_date_local': '2025-01-06',
            'type': 'Ride',
            'moving_time': 3600,
            'icu_weighted_avg_watts': 180,
            'icu_average_watts': 175,
            'average_hr': 140,
            'max_hr': 165
        }
    ]

    feedback = {
        'i123': {'rpe': 6, 'comments': 'Good session'}
    }

    workouts = aggregator._process_workouts_detailed(activities, feedback)

    assert len(workouts) == 1
    assert workouts[0]['tss'] == 45
    assert workouts[0]['if'] == 1.20  # Normalized from 120%
    assert workouts[0]['normalized_power'] == 180
    assert workouts[0]['average_power'] == 175
    assert workouts[0]['feedback']['rpe'] == 6
    assert workouts[0]['session_number'] == 1


def test_process_metrics_evolution():
    """Test traitement metrics evolution."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    metrics_daily = [
        {'date': '2025-01-06', 'ctl': 60.0, 'atl': 58.0, 'tsb': 2.0},
        {'date': '2025-01-07', 'ctl': 61.5, 'atl': 59.2, 'tsb': 2.3},
        {'date': '2025-01-08', 'ctl': 62.5, 'atl': 60.0, 'tsb': 2.5}
    ]

    evolution = aggregator._process_metrics_evolution(metrics_daily)

    assert 'daily' in evolution
    assert 'trends' in evolution
    assert len(evolution['daily']) == 3
    assert abs(evolution['trends']['ctl_change'] - 2.5) < 0.1
    assert abs(evolution['trends']['tsb_change'] - 0.5) < 0.1


def test_extract_training_learnings():
    """Test extraction training learnings."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    activities = [
        {'training_load': 85, 'if': 1.1},
        {'training_load': 90, 'if': 1.15},
        {'training_load': 45, 'if': 0.8}
    ]

    feedback = {
        'a1': {'rpe': 2},
        'a2': {'rpe': 3}
    }

    learnings = aggregator._extract_training_learnings(activities, feedback)

    assert any('haute charge' in l for l in learnings)
    assert any('RPE faible' in l for l in learnings)


def test_identify_protocol_changes():
    """Test identification protocol changes."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    learnings = []
    metrics_evolution = {
        'trends': {
            'tsb_change': -12.5
        }
    }

    adaptations = aggregator._identify_protocol_changes(learnings, metrics_evolution)

    assert len(adaptations) == 1
    assert adaptations[0]['type'] == 'recovery'
    assert 'TSB dropped' in adaptations[0]['reason']


def test_prepare_transition_data():
    """Test preparation transition data."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    summary = {
        'total_tss': 320,
        'avg_tss': 45.7,
        'final_metrics': {'tsb': -18.5}
    }

    metrics_evolution = {'trends': {}}
    learnings = ['Learning 1', 'Learning 2', 'Learning 3', 'Learning 4']

    transition = aggregator._prepare_transition_data(summary, metrics_evolution, learnings)

    assert transition['current_state']['total_tss'] == 320
    assert transition['current_state']['final_tsb'] == -18.5
    assert len(transition['focus_areas']) == 3  # Top 3 learnings
    assert any('Recovery' in r for r in transition['recommendations'])


def test_analyze_wellness():
    """Test analysis wellness data."""
    aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))

    wellness = {
        '2025-01-06': {'sleep_quality': 8, 'sleep_hours': 7.5, 'weight': 84.0},
        '2025-01-07': {'sleep_quality': 7, 'sleep_hours': 7.0, 'weight': 83.8},
        '2025-01-08': {'sleep_quality': 9, 'sleep_hours': 8.0, 'weight': 83.9}
    }

    insights = aggregator._analyze_wellness(wellness)

    assert insights['sleep_quality_avg'] == 8.0
    assert abs(insights['sleep_hours_avg'] - 7.5) < 0.1
    assert abs(insights['weight_trend'] - (-0.1)) < 0.1
