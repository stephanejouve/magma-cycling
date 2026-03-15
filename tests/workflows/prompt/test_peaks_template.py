"""Tests for peaks_methodology.md template loading."""

from magma_cycling.workflows.planner.prompt import _TEMPLATE_DIR


class TestPeaksTemplate:
    """Tests for the externalized Peaks methodology template."""

    def test_template_file_exists(self):
        """The peaks_methodology.md template file exists on disk."""
        template_file = _TEMPLATE_DIR / "peaks_methodology.md"
        assert template_file.exists()

    def test_template_loads(self):
        """The template loads and contains expected content."""
        template_file = _TEMPLATE_DIR / "peaks_methodology.md"
        content = template_file.read_text(encoding="utf-8")
        assert "MÉTHODOLOGIE PEAKS COACHING" in content
        assert "Hunter Allen" in content
        assert "{week_number}" in content
