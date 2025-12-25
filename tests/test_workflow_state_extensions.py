#!/usr/bin/env python3
"""
Tests unitaires pour les extensions WorkflowState Phase 4

Tests:
- Tracking sessions spéciales documentées (repos/annulations/sautées)
- Persistence feedback athlète
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from cyclisme_training_logs.workflow_state import WorkflowState


class TestSpecialSessionsTracking:
    """Tests tracking sessions spéciales"""

    @pytest.fixture
    def temp_dir(self):
        """Créer répertoire temporaire pour tests"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def state(self, temp_dir):
        """Créer instance WorkflowState pour tests"""
        return WorkflowState(project_root=temp_dir)

    def test_mark_special_session_documented(self, state):
        """Test marking special session as documented"""
        # Marquer repos planifié
        state.mark_special_session_documented("S072-07", "rest", "2025-12-21")

        # Vérifier présence dans state
        assert 'documented_specials' in state.state
        key = "S072-07_2025-12-21"
        assert key in state.state['documented_specials']

        # Vérifier métadonnées
        entry = state.state['documented_specials'][key]
        assert entry['session_id'] == "S072-07"
        assert entry['type'] == "rest"
        assert entry['date'] == "2025-12-21"
        assert 'documented_at' in entry

    def test_is_special_session_documented(self, state):
        """Test checking if session is documented"""
        # Avant marking
        assert not state.is_special_session_documented("S072-07", "2025-12-21")

        # Après marking
        state.mark_special_session_documented("S072-07", "rest", "2025-12-21")
        assert state.is_special_session_documented("S072-07", "2025-12-21")

        # Autre session non documentée
        assert not state.is_special_session_documented("S072-05", "2025-12-19")

    def test_is_special_session_documented_empty_params(self, state):
        """Test with empty parameters"""
        assert not state.is_special_session_documented("", "2025-12-21")
        assert not state.is_special_session_documented("S072-07", "")
        assert not state.is_special_session_documented("", "")

    def test_mark_multiple_special_sessions(self, state):
        """Test marking multiple sessions"""
        sessions = [
            ("S072-07", "rest", "2025-12-21"),
            ("S072-05", "skipped", "2025-12-19"),
            ("S072-03", "cancelled", "2025-12-17")
        ]

        for session_id, session_type, date in sessions:
            state.mark_special_session_documented(session_id, session_type, date)

        # Vérifier toutes présentes
        for session_id, _, date in sessions:
            assert state.is_special_session_documented(session_id, date)

    def test_get_documented_specials(self, state):
        """Test retrieving all documented specials"""
        # Avant marking
        assert state.get_documented_specials() == {}

        # Marquer 2 sessions
        state.mark_special_session_documented("S072-07", "rest", "2025-12-21")
        state.mark_special_session_documented("S072-05", "skipped", "2025-12-19")

        # Récupérer toutes
        specials = state.get_documented_specials()
        assert len(specials) == 2
        assert "S072-07_2025-12-21" in specials
        assert "S072-05_2025-12-19" in specials

    def test_special_sessions_persistence(self, state, temp_dir):
        """Test persistence to JSON file"""
        # Marquer session
        state.mark_special_session_documented("S072-07", "rest", "2025-12-21")

        # Charger nouveau state depuis fichier
        state2 = WorkflowState(project_root=temp_dir)
        assert state2.is_special_session_documented("S072-07", "2025-12-21")


class TestFeedbackPersistence:
    """Tests persistence feedback athlète"""

    @pytest.fixture
    def temp_dir(self):
        """Créer répertoire temporaire pour tests"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def state(self, temp_dir):
        """Créer instance WorkflowState pour tests"""
        return WorkflowState(project_root=temp_dir)

    def test_save_session_feedback(self, state):
        """Test saving feedback"""
        feedback = {
            'rpe': 7,
            'comments': 'Felt strong',
            'sleep_quality': 8,
            'sleep_hours': 7.5
        }

        state.save_session_feedback("i123456", feedback)

        # Vérifier présence dans state
        assert 'feedbacks' in state.state
        assert 'i123456' in state.state['feedbacks']

        # Vérifier structure
        entry = state.state['feedbacks']['i123456']
        assert 'feedback' in entry
        assert 'timestamp' in entry
        assert entry['feedback'] == feedback

    def test_get_session_feedback(self, state):
        """Test retrieving feedback"""
        feedback = {'rpe': 8, 'comments': 'Excellent session'}

        # Avant save
        assert state.get_session_feedback("i123456") is None

        # Après save
        state.save_session_feedback("i123456", feedback)
        retrieved = state.get_session_feedback("i123456")

        assert retrieved is not None
        assert retrieved['feedback']['rpe'] == 8
        assert retrieved['feedback']['comments'] == 'Excellent session'
        assert 'timestamp' in retrieved

    def test_has_session_feedback(self, state):
        """Test checking feedback existence"""
        # Avant save
        assert not state.has_session_feedback("i123456")

        # Après save
        state.save_session_feedback("i123456", {'rpe': 7})
        assert state.has_session_feedback("i123456")

        # Autre activité
        assert not state.has_session_feedback("i999999")

    def test_save_multiple_feedbacks(self, state):
        """Test saving multiple feedbacks"""
        feedbacks = {
            "i123456": {'rpe': 7, 'comments': 'Good'},
            "i123457": {'rpe': 8, 'comments': 'Great'},
            "i123458": {'rpe': 6, 'comments': 'Tired'}
        }

        for activity_id, feedback in feedbacks.items():
            state.save_session_feedback(activity_id, feedback)

        # Vérifier toutes présentes
        for activity_id in feedbacks:
            assert state.has_session_feedback(activity_id)

    def test_feedback_persistence(self, state, temp_dir):
        """Test persistence to JSON file"""
        feedback = {'rpe': 9, 'comments': 'Amazing workout'}

        # Sauvegarder feedback
        state.save_session_feedback("i123456", feedback)

        # Charger nouveau state depuis fichier
        state2 = WorkflowState(project_root=temp_dir)
        retrieved = state2.get_session_feedback("i123456")

        assert retrieved is not None
        assert retrieved['feedback']['rpe'] == 9

    def test_update_existing_feedback(self, state):
        """Test updating feedback for same activity"""
        # Save initial
        state.save_session_feedback("i123456", {'rpe': 7, 'comments': 'OK'})

        # Update
        state.save_session_feedback("i123456", {'rpe': 8, 'comments': 'Better'})

        # Vérifier updated
        retrieved = state.get_session_feedback("i123456")
        assert retrieved['feedback']['rpe'] == 8
        assert retrieved['feedback']['comments'] == 'Better'


class TestBackwardCompatibility:
    """Tests compatibilité avec state files existants"""

    @pytest.fixture
    def temp_dir(self):
        """Créer répertoire temporaire pour tests"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    def test_load_old_state_file(self, temp_dir):
        """Test loading old state file without new fields"""
        # Créer ancien state file (sans documented_specials ni feedbacks)
        old_state = {
            "last_analyzed_activity_id": "i123456",
            "last_analyzed_date": "2025-12-20T10:00:00",
            "total_analyses": 5,
            "history": [
                {"activity_id": "i123456", "analyzed_at": "2025-12-20T10:00:00"}
            ]
        }

        state_file = temp_dir / ".workflow_state.json"
        with open(state_file, 'w') as f:
            json.dump(old_state, f)

        # Charger avec nouveau code
        state = WorkflowState(project_root=temp_dir)

        # Vérifier chargement OK
        assert state.get_last_analyzed_id() == "i123456"

        # Vérifier nouveaux champs accessibles (vides)
        assert state.get_documented_specials() == {}
        assert not state.has_session_feedback("i123456")

        # Vérifier écriture fonctionne
        state.mark_special_session_documented("S072-07", "rest", "2025-12-21")
        assert state.is_special_session_documented("S072-07", "2025-12-21")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
