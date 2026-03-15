"""Tests for CardiovascularQualityMixin."""

from datetime import date
from pathlib import Path

from magma_cycling.workflows.pid_eval.cardiovascular import CardiovascularQualityMixin


class StubCardio(CardiovascularQualityMixin):
    """Stub class to test CardiovascularQualityMixin in isolation."""

    def __init__(self, workouts_history):
        """Initialize stub with workouts_history path."""
        self.workouts_history = Path(workouts_history)


class TestExtractCardiovascularCoupling:
    """Tests for extract_cardiovascular_coupling."""

    def test_extracts_parenthesized_format(self, tmp_path):
        """Extracts 'decouplage cardiovasculaire excellent (1.6%)' format."""
        week_dir = tmp_path / "S073"
        week_dir.mkdir()
        (week_dir / "workout_history_S073.md").write_text(
            "Bon découplage cardiovasculaire excellent (1.6%)\n"
        )
        stub = StubCardio(tmp_path)
        values = stub.extract_cardiovascular_coupling(date(2026, 1, 1), date(2026, 12, 31))
        assert len(values) == 1
        assert abs(values[0] - 0.016) < 0.001

    def test_extracts_simple_format(self, tmp_path):
        """Extracts 'decouplage 4.1%' format."""
        week_dir = tmp_path / "S074"
        week_dir.mkdir()
        (week_dir / "workout_history_S074.md").write_text("Découplage 4.1%\n")
        stub = StubCardio(tmp_path)
        values = stub.extract_cardiovascular_coupling(date(2026, 1, 1), date(2026, 12, 31))
        assert len(values) >= 1
        assert any(abs(v - 0.041) < 0.001 for v in values)

    def test_no_files_returns_empty(self, tmp_path):
        """No workout files returns empty list."""
        stub = StubCardio(tmp_path)
        values = stub.extract_cardiovascular_coupling(date(2026, 1, 1), date(2026, 12, 31))
        assert values == []

    def test_missing_directory_returns_empty(self, tmp_path):
        """Missing workouts_history directory returns empty list."""
        stub = StubCardio(tmp_path / "nonexistent")
        values = stub.extract_cardiovascular_coupling(date(2026, 1, 1), date(2026, 12, 31))
        assert values == []

    def test_multiple_values_from_file(self, tmp_path):
        """Multiple coupling values extracted from single file."""
        week_dir = tmp_path / "S075"
        week_dir.mkdir()
        (week_dir / "workout_history_S075.md").write_text(
            "Découplage cardiovasculaire bon (3.5%)\n"
            "Découplage 7.2%\n"
            "Découplage cardiovasculaire excellent (2.1%)\n"
        )
        stub = StubCardio(tmp_path)
        values = stub.extract_cardiovascular_coupling(date(2026, 1, 1), date(2026, 12, 31))
        assert len(values) >= 3
