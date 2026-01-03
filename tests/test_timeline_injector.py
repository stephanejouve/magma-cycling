"""
Tests for TimelineInjector chronological injection.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

from datetime import date
from pathlib import Path

import pytest

from cyclisme_training_logs.core.timeline_injector import TimelineInjector


@pytest.fixture
def sample_history_file(tmp_path):
    """Créer fichier history temporaire pour tests."""
    history = tmp_path / "workouts-history.md"
    content = """# Historique Entraînements

### S073-01 (2025-01-06)
**Durée:** 55min | **TSS:** 40

### S073-03 (2025-01-08)
**Durée:** 45min | **TSS:** 35

### S073-05 (2025-01-10)
**Durée:** 60min | **TSS:** 50
"""
    history.write_text(content)
    return history


def test_extract_date_from_entry(tmp_path):
    """Test extraction date depuis entrée workout."""
    # Créer un fichier temporaire pour initialiser l'injecteur
    temp_file = tmp_path / "temp.md"
    temp_file.write_text("# Test")

    injector = TimelineInjector(temp_file)

    entry = "### S073-02 (2025-01-07)\n**Durée:** 50min"
    extracted = injector.extract_date_from_entry(entry)

    assert extracted == date(2025, 1, 7)


def test_chronological_injection_middle(sample_history_file):
    """Test injection au milieu de l'historique."""
    injector = TimelineInjector(sample_history_file)

    new_entry = """### S073-02 (2025-01-07)
**Durée:** 50min | **TSS:** 42"""

    result = injector.inject_chronologically(new_entry, date(2025, 1, 7))

    assert result.success

    # Vérifier ordre chronologique
    content = sample_history_file.read_text()
    assert content.index("S073-01") < content.index("S073-02")
    assert content.index("S073-02") < content.index("S073-03")


def test_duplicate_detection(sample_history_file):
    """Test détection duplicates."""
    injector = TimelineInjector(sample_history_file, check_duplicates=True)

    duplicate_entry = """### S073-01 (2025-01-06)
**Durée:** 55min | **TSS:** 40"""

    result = injector.inject_chronologically(duplicate_entry, date(2025, 1, 6))

    assert not result.success
    assert result.duplicate_found


def test_injection_without_date_extraction(sample_history_file):
    """Test injection avec extraction automatique de date."""
    injector = TimelineInjector(sample_history_file)

    new_entry = """### S073-04 (2025-01-09)
**Durée:** 65min | **TSS:** 48"""

    # Date automatiquement extraite
    result = injector.inject_chronologically(new_entry)

    assert result.success
    assert result.line_number is not None


def test_file_not_found():
    """Test gestion fichier inexistant."""
    with pytest.raises(FileNotFoundError):
        TimelineInjector(Path("/nonexistent/file.md"))


def test_inject_multiple_entries(sample_history_file):
    """Test injection multiple entrées."""
    injector = TimelineInjector(sample_history_file)

    entries = [
        ("### S073-02 (2025-01-07)\n**Durée:** 50min", date(2025, 1, 7)),
        ("### S073-04 (2025-01-09)\n**Durée:** 65min", date(2025, 1, 9)),
    ]

    results = injector.inject_multiple(entries)

    assert len(results) == 2
    assert all(r.success for r in results)

    # Vérifier ordre chronologique complet
    content = sample_history_file.read_text()
    positions = {
        "S073-01": content.index("S073-01"),
        "S073-02": content.index("S073-02"),
        "S073-03": content.index("S073-03"),
        "S073-04": content.index("S073-04"),
        "S073-05": content.index("S073-05"),
    }

    assert (
        positions["S073-01"]
        < positions["S073-02"]
        < positions["S073-03"]
        < positions["S073-04"]
        < positions["S073-05"]
    )
