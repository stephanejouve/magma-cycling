"""
Tests pour DuplicateDetector

GARTNER_TIME: T
STATUS: Testing
LAST_REVIEW: 2025-12-27
PRIORITY: P1
DOCSTRING: v2

Tests unitaires pour le module duplicate_detector qui détecte et supprime
les doublons dans workouts-history.md en mode paranoid.

Author: Claude Code
Created: 2025-12-27
Updated: 2025-12-27 (Initial test suite)
"""
from pathlib import Path

import pytest

from cyclisme_training_logs.core.duplicate_detector import (
    DuplicateDetectedError,
    DuplicateDetector,
    check_and_handle_duplicates,
)


@pytest.fixture
def sample_history_with_duplicates(tmp_path):
    """Crée un fichier test avec doublons"""
    history = tmp_path / "workouts-history.md"

    content = """### S073-01-END-Test
Date : 22/12/2025

#### Exécution
Test 1

---

### S073-02-INT-Test
Date : 23/12/2025

#### Exécution
Test 2

---

### S073-01-END-Test
Date : 22/12/2025

#### Exécution
Test 1 DOUBLON

---
"""
    history.write_text(content)

    return history


@pytest.fixture
def sample_history_no_duplicates(tmp_path):
    """Crée un fichier test sans doublons"""
    history = tmp_path / "workouts-history.md"

    content = """### S073-01-END-Test
Date : 22/12/2025

#### Exécution
Test 1

---

### S073-02-INT-Test
Date : 23/12/2025

#### Exécution
Test 2

---
"""
    history.write_text(content)

    return history


def test_detect_duplicates(sample_history_with_duplicates):
    """Test détection basique"""
    detector = DuplicateDetector(sample_history_with_duplicates)

    duplicates = detector.quick_scan()

    assert len(duplicates) == 1
    assert duplicates[0]["id"] == "S073-01-END-Test"
    assert duplicates[0]["first_line"] == 1
    assert duplicates[0]["duplicate_line"] == 17


def test_no_duplicates_found(sample_history_no_duplicates):
    """Test avec fichier sans doublons"""
    detector = DuplicateDetector(sample_history_no_duplicates)

    duplicates = detector.quick_scan()

    assert len(duplicates) == 0


def test_check_window_limitation(sample_history_with_duplicates):
    """Test limitation du window"""
    # Window=1 ne devrait voir que la première entrée

    detector = DuplicateDetector(sample_history_with_duplicates, check_window=1)
    duplicates = detector.quick_scan()

    assert len(duplicates) == 0  # Pas de doublon dans la fenêtre


def test_auto_fix(sample_history_with_duplicates):
    """Test suppression automatique"""
    check_and_handle_duplicates(sample_history_with_duplicates, auto_fix=True)

    # Vérifier que doublon supprimé
    detector = DuplicateDetector(sample_history_with_duplicates)
    duplicates = detector.quick_scan()

    assert len(duplicates) == 0

    # Vérifier que première occurrence reste
    content = sample_history_with_duplicates.read_text()
    assert "S073-01-END-Test" in content
    assert "Test 1 DOUBLON" not in content


def test_fail_fast_mode(sample_history_with_duplicates):
    """Test mode fail-fast"""
    with pytest.raises(DuplicateDetectedError) as exc_info:
        check_and_handle_duplicates(sample_history_with_duplicates, auto_fix=False)

    # Vérifier que l'exception contient les bons duplicates
    assert len(exc_info.value.duplicates) == 1
    assert exc_info.value.duplicates[0]["id"] == "S073-01-END-Test"


def test_no_action_when_no_duplicates(sample_history_no_duplicates):
    """Test qu'aucune action n'est prise si pas de doublons"""
    original_content = sample_history_no_duplicates.read_text()

    # Mode fail-fast - ne devrait pas lever d'exception
    check_and_handle_duplicates(sample_history_no_duplicates, auto_fix=False)

    # Vérifier que le contenu n'a pas changé
    assert sample_history_no_duplicates.read_text() == original_content


def test_nonexistent_file():
    """Test avec fichier qui n'existe pas"""
    detector = DuplicateDetector(Path("/nonexistent/file.md"))

    duplicates = detector.quick_scan()

    assert len(duplicates) == 0


def test_find_entry_bounds(sample_history_with_duplicates):
    """Test recherche des bornes d'une entrée"""
    detector = DuplicateDetector(sample_history_with_duplicates)

    lines = sample_history_with_duplicates.read_text().split("\n")

    # Première entrée (ligne 0)
    start, end = detector.find_entry_bounds(0, lines)
    assert start == 0
    assert end > 0  # Devrait inclure plusieurs lignes

    # Vérifier que ça s'arrête avant la prochaine entrée
    next_entry = None
    for i in range(start + 1, len(lines)):
        if detector.pattern.match(lines[i]):
            next_entry = i
            break

    if next_entry:
        assert end < next_entry


def test_remove_multiple_duplicates(tmp_path):
    """Test suppression de plusieurs doublons"""
    history = tmp_path / "workouts-history.md"

    content = """### S073-01
Test 1

---

### S073-02
Test 2

---

### S073-01
Test 1 DUP

---

### S073-02
Test 2 DUP

---
"""
    history.write_text(content)

    # Auto-fix
    check_and_handle_duplicates(history, auto_fix=True)

    # Vérifier que tous les doublons sont supprimés
    detector = DuplicateDetector(history)
    duplicates = detector.quick_scan()
    assert len(duplicates) == 0

    # Vérifier que les originaux restent
    content_after = history.read_text()
    assert "S073-01" in content_after
    assert "S073-02" in content_after
    assert "DUP" not in content_after
