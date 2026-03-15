"""Tests for analyzers.adherence_storage module.

Tests AdherenceStorage : save/load/query sessions, mesocycle stats, trend avec tmp_path.
"""

import pytest

from magma_cycling.analyzers.adherence_storage import AdherenceStorage


class TestAdherenceStorageInit:
    """Tests for initialization and data loading."""

    def test_init_with_custom_path(self, tmp_path):
        storage_file = tmp_path / "adherence.json"
        storage = AdherenceStorage(storage_file=storage_file)
        assert storage.storage_file == storage_file

    def test_init_creates_empty_data(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        assert storage.data["sessions"] == {}
        assert storage.data["last_updated"] is None

    def test_load_existing_data(self, tmp_path):
        storage_file = tmp_path / "adherence.json"
        storage_file.write_text(
            '{"sessions": {"S082_i123": {"activity_id": "i123"}}, "last_updated": "2026-03-01"}'
        )
        storage = AdherenceStorage(storage_file=storage_file)
        assert "S082_i123" in storage.data["sessions"]

    def test_load_corrupt_file(self, tmp_path):
        storage_file = tmp_path / "adherence.json"
        storage_file.write_text("not json {{{")
        storage = AdherenceStorage(storage_file=storage_file)
        assert storage.data["sessions"] == {}


class TestSaveSessionAdherence:
    """Tests for save_session_adherence()."""

    def test_save_session(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        adherence_data = {"tss_adherence": 0.95, "if_adherence": 0.98, "has_plan": True}
        storage.save_session_adherence("i123456", "S082", "2026-02-19", adherence_data)

        assert "S082_i123456" in storage.data["sessions"]
        session = storage.data["sessions"]["S082_i123456"]
        assert session["activity_id"] == "i123456"
        assert session["week_id"] == "S082"
        assert session["adherence"]["tss_adherence"] == 0.95

    def test_save_persists_to_file(self, tmp_path):
        storage_file = tmp_path / "adherence.json"
        storage = AdherenceStorage(storage_file=storage_file)
        storage.save_session_adherence("i123", "S082", "2026-02-19", {"tss_adherence": 0.9})

        # Reload from file
        storage2 = AdherenceStorage(storage_file=storage_file)
        assert "S082_i123" in storage2.data["sessions"]

    def test_save_multiple_sessions(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence("i001", "S082", "2026-02-19", {"tss_adherence": 0.9})
        storage.save_session_adherence("i002", "S082", "2026-02-20", {"tss_adherence": 0.85})
        storage.save_session_adherence("i003", "S083", "2026-02-26", {"tss_adherence": 0.95})

        assert len(storage.data["sessions"]) == 3


class TestGetSessionAdherence:
    """Tests for get_session_adherence()."""

    def test_get_existing_session(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence("i123", "S082", "2026-02-19", {"tss_adherence": 0.95})

        result = storage.get_session_adherence("i123", "S082")
        assert result is not None
        assert result["adherence"]["tss_adherence"] == 0.95

    def test_get_nonexistent_session(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        result = storage.get_session_adherence("i999", "S099")
        assert result is None


class TestGetMesocycleAdherence:
    """Tests for get_mesocycle_adherence()."""

    def test_get_mesocycle_data(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence("i001", "S077", "2026-01-06", {"tss_adherence": 0.9})
        storage.save_session_adherence("i002", "S078", "2026-01-13", {"tss_adherence": 0.85})
        storage.save_session_adherence("i003", "S079", "2026-01-20", {"tss_adherence": 0.95})
        storage.save_session_adherence("i004", "S080", "2026-01-27", {"tss_adherence": 0.88})

        result = storage.get_mesocycle_adherence(["S077", "S078", "S079"])
        assert len(result) == 3

    def test_sorted_by_date(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence("i002", "S078", "2026-01-13", {"tss_adherence": 0.85})
        storage.save_session_adherence("i001", "S077", "2026-01-06", {"tss_adherence": 0.9})

        result = storage.get_mesocycle_adherence(["S077", "S078"])
        assert result[0]["date"] == "2026-01-06"
        assert result[1]["date"] == "2026-01-13"

    def test_empty_mesocycle(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        result = storage.get_mesocycle_adherence(["S090", "S091"])
        assert result == []


class TestCalculateMesocycleStats:
    """Tests for calculate_mesocycle_stats()."""

    def test_stats_with_data(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence(
            "i001", "S077", "2026-01-06",
            {"tss_adherence": 0.90, "if_adherence": 0.95, "has_plan": True},
        )
        storage.save_session_adherence(
            "i002", "S078", "2026-01-13",
            {"tss_adherence": 0.80, "if_adherence": 0.90, "has_plan": True},
        )

        stats = storage.calculate_mesocycle_stats(["S077", "S078"])
        assert stats["sessions_count"] == 2
        assert stats["sessions_with_plan"] == 2
        assert stats["tss_adherence_avg"] == pytest.approx(0.85)
        assert stats["if_adherence_avg"] == pytest.approx(0.925)

    def test_stats_empty(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        stats = storage.calculate_mesocycle_stats(["S090"])
        assert stats["sessions_count"] == 0
        assert stats["tss_adherence_avg"] == 0

    def test_stats_sessions_without_plan(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence(
            "i001", "S077", "2026-01-06",
            {"tss_adherence": None, "has_plan": False},
        )

        stats = storage.calculate_mesocycle_stats(["S077"])
        assert stats["sessions_count"] == 1
        assert stats["sessions_with_plan"] == 0


class TestGetAdherenceTrend:
    """Tests for get_adherence_trend()."""

    def test_improving_trend(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        # Increasing TSS adherence over time
        for i, tss in enumerate([0.70, 0.75, 0.80, 0.85, 0.90]):
            storage.save_session_adherence(
                f"i{i:03d}", "S077", f"2026-01-{6 + i:02d}",
                {"tss_adherence": tss, "has_plan": True},
            )

        trend = storage.get_adherence_trend(["S077"])
        assert trend == "improving"

    def test_declining_trend(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        for i, tss in enumerate([0.95, 0.90, 0.85, 0.80, 0.70]):
            storage.save_session_adherence(
                f"i{i:03d}", "S077", f"2026-01-{6 + i:02d}",
                {"tss_adherence": tss, "has_plan": True},
            )

        trend = storage.get_adherence_trend(["S077"])
        assert trend == "declining"

    def test_insufficient_data(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        storage.save_session_adherence(
            "i001", "S077", "2026-01-06",
            {"tss_adherence": 0.90, "has_plan": True},
        )

        trend = storage.get_adherence_trend(["S077"])
        assert trend == "insufficient_data"

    def test_stable_trend(self, tmp_path):
        storage = AdherenceStorage(storage_file=tmp_path / "adherence.json")
        for i in range(5):
            storage.save_session_adherence(
                f"i{i:03d}", "S077", f"2026-01-{6 + i:02d}",
                {"tss_adherence": 0.90, "has_plan": True},
            )

        trend = storage.get_adherence_trend(["S077"])
        assert trend == "stable"
