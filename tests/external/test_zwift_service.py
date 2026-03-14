"""Tests unitaires pour ZwiftService (façade)."""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.external.zwift_collections import KNOWN_COLLECTIONS
from magma_cycling.external.zwift_models import (
    SegmentType,
    WorkoutMatch,
    WorkoutSearchCriteria,
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)
from magma_cycling.external.zwift_service import PopulateResult, ZwiftService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_cache(tmp_path):
    """Provide a temporary cache database path."""
    return tmp_path / "test_zwift.db"


@pytest.fixture()
def service(tmp_cache):
    """ZwiftService with a temp cache."""
    return ZwiftService(cache_db_path=tmp_cache)


def _make_workout(name="Test", tss=50, category=ZwiftCategory.FTP):
    """Helper to build a minimal ZwiftWorkout."""
    return ZwiftWorkout(
        name=name,
        category=category,
        duration_minutes=30,
        tss=tss,
        url=f"https://whatsonzwift.com/workouts/test/{name.lower().replace(' ', '-')}",
        description=f"Test workout {name}",
        segments=[
            ZwiftWorkoutSegment(
                segment_type=SegmentType.STEADY,
                duration_seconds=1800,
                power_low=80,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Tests — Seed
# ---------------------------------------------------------------------------


class TestSeed:
    """Tests pour seed_collection / list_seed_collections."""

    def test_seed_all(self, service):
        """Seed toutes les collections et vérifie le compteur."""
        count = service.seed_collection(None)
        assert count > 0

    def test_seed_specific_collection(self, service):
        """Seed une collection spécifique."""
        collections = service.list_seed_collections()
        first_name = next(iter(collections))
        count = service.seed_collection(first_name)
        assert count == len(collections[first_name])

    def test_seed_unknown_collection_raises(self, service):
        """KeyError si la collection n'existe pas."""
        with pytest.raises(KeyError, match="not found"):
            service.seed_collection("inexistant-xyz")

    def test_list_seed_collections(self, service):
        """Retourne un dict non vide de collections."""
        collections = service.list_seed_collections()
        assert isinstance(collections, dict)
        assert len(collections) > 0
        for name, workouts in collections.items():
            assert isinstance(name, str)
            assert all(isinstance(w, ZwiftWorkout) for w in workouts)


# ---------------------------------------------------------------------------
# Tests — Search
# ---------------------------------------------------------------------------


class TestSearch:
    """Tests pour search_workouts / mark_workout_used."""

    def test_search_returns_list(self, service):
        """search_workouts retourne une liste (même vide)."""
        criteria = WorkoutSearchCriteria(session_type="FTP", tss_target=56, tss_tolerance=15)
        result = service.search_workouts(criteria)
        assert isinstance(result, list)

    def test_search_after_seed(self, service):
        """Après seed, on trouve des résultats."""
        service.seed_collection(None)
        criteria = WorkoutSearchCriteria(session_type="FTP", tss_target=56, tss_tolerance=30)
        result = service.search_workouts(criteria)
        assert len(result) > 0
        assert all(isinstance(m, WorkoutMatch) for m in result)

    def test_mark_workout_used(self, service):
        """mark_workout_used ne lève pas d'exception."""
        workout = _make_workout()
        service._client._save_workout_to_cache(workout)
        service.mark_workout_used(workout, "2026-03-01")


# ---------------------------------------------------------------------------
# Tests — Populate (mocked HTTP)
# ---------------------------------------------------------------------------

LISTING_HTML = """
<html><body>
  <a href="/workouts/test-col/workout-1">Workout 1</a>
</body></html>
"""

WORKOUT_HTML = """
<html><body><article>
  <header><h1>Workout 1</h1></header>
  <p><strong>Duration:</strong> 30m</p>
  <p><strong>Stress Score:</strong> 42</p>
  <section>
    <div class="textbar">10min @ 85rpm, 75% FTP</div>
  </section>
</article></body></html>
"""


class TestPopulate:
    """Tests pour populate_collection / populate_collections."""

    def test_populate_single_collection(self, service):
        """Populate une collection avec HTTP mocké."""
        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        workout_resp = MagicMock()
        workout_resp.text = WORKOUT_HTML
        workout_resp.raise_for_status = MagicMock()

        with patch.object(service._session, "get", side_effect=[listing_resp, workout_resp]):
            result = service.populate_collection("test-col")

        assert isinstance(result, PopulateResult)
        assert result.collection == "test-col"
        assert result.total_found == 1
        assert result.cached_count == 1
        assert result.errors == []

    def test_populate_dry_run(self, service):
        """En dry-run, aucun workout n'est sauvé en cache."""
        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        workout_resp = MagicMock()
        workout_resp.text = WORKOUT_HTML
        workout_resp.raise_for_status = MagicMock()

        with patch.object(service._session, "get", side_effect=[listing_resp, workout_resp]):
            result = service.populate_collection("test-col", dry_run=True)

        assert result.cached_count == 1  # counted but not saved
        stats = service.get_cache_stats()
        assert stats["total_workouts"] == 0

    def test_populate_network_error(self, service):
        """Erreur réseau reportée dans errors."""
        import requests

        with patch.object(
            service._session,
            "get",
            side_effect=requests.RequestException("connection refused"),
        ):
            result = service.populate_collection("bad-slug")

        assert result.total_found == 0
        assert len(result.errors) == 1
        assert "connection refused" in result.errors[0]

    def test_populate_collections(self, service):
        """populate_collections traite plusieurs slugs."""
        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        workout_resp = MagicMock()
        workout_resp.text = WORKOUT_HTML
        workout_resp.raise_for_status = MagicMock()

        with patch.object(
            service._session,
            "get",
            side_effect=[listing_resp, workout_resp, listing_resp, workout_resp],
        ):
            results = service.populate_collections(["col-a", "col-b"])

        assert len(results) == 2
        assert all(isinstance(r, PopulateResult) for r in results.values())

    def test_populate_with_callback(self, service):
        """Le callback on_workout est appelé pour chaque workout."""
        listing_resp = MagicMock()
        listing_resp.text = LISTING_HTML
        listing_resp.raise_for_status = MagicMock()

        workout_resp = MagicMock()
        workout_resp.text = WORKOUT_HTML
        workout_resp.raise_for_status = MagicMock()

        callback = MagicMock()

        with patch.object(service._session, "get", side_effect=[listing_resp, workout_resp]):
            service.populate_collection("test-col", on_workout=callback)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == 1  # index
        assert args[1] == 1  # total


# ---------------------------------------------------------------------------
# Tests — Stats & utilities
# ---------------------------------------------------------------------------


class TestUtilities:
    """Tests pour get_cache_stats, create_sample_workout, etc."""

    def test_cache_stats_empty(self, service):
        """Stats sur cache vide."""
        stats = service.get_cache_stats()
        assert stats["total_workouts"] == 0
        assert isinstance(stats["by_category"], dict)

    def test_cache_stats_after_seed(self, service):
        """Stats après seeding."""
        service.seed_collection(None)
        stats = service.get_cache_stats()
        assert stats["total_workouts"] > 0

    def test_create_sample_workout(self, service):
        """Crée un workout sample valide."""
        workout = service.create_sample_workout()
        assert isinstance(workout, ZwiftWorkout)
        assert workout.name == "Flat Out Fast"
        assert len(workout.segments) > 0

    def test_to_intervals_format(self, service):
        """Conversion en format Intervals.icu."""
        workout = service.create_sample_workout()
        text = service.to_intervals_format(workout)
        assert "Flat Out Fast" in text
        assert "TSS" in text

    def test_validate_wahoo_valid(self, service):
        """Validation Wahoo sur un workout correct."""
        workout = service.create_sample_workout()
        text = workout.to_intervals_description()
        is_valid, issues = service.validate_wahoo(text)
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_get_known_collections(self, service):
        """Retourne une copie du registre."""
        collections = service.get_known_collections()
        assert collections == KNOWN_COLLECTIONS
        # Vérifie que c'est une copie
        collections["new-key"] = "test"
        assert "new-key" not in service.get_known_collections()
