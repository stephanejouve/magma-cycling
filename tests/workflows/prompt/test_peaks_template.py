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

    def test_template_documents_textevent_cue_grammars(self):
        """WS-A: the template teaches both Intervals.icu native cue syntaxes.

        Two forms must be documented so the Coach AI LLM emits them by
        design (see PR #414 workout-parser fix for the parser side):
        - ``NN^ Text`` anchored cue with explicit offset/duration
        - ``Text1. Text2. Text3.`` multiple cues spread across the step

        Plus minimal usage rules (sobriety, brevity, ASCII pure) and at
        least one positive + one negative example.
        """
        template_file = _TEMPLATE_DIR / "peaks_methodology.md"
        content = template_file.read_text(encoding="utf-8")
        # Both grammars present
        assert "NN^" in content
        assert "Text1. Text2. Text3." in content
        # Section header anchor
        assert "Cues textuels intra-step" in content
        # At least one positive example with the multi-cue form
        assert "Engage. Cadence stable. Respire. 10m 90% 92rpm" in content
        # At least one negative example marked with ❌
        assert "❌" in content and "5^Engage" in content  # missing space after ^
        # Sobriety / ASCII rules so LLM doesn't spam cues or break parsing
        assert "ASCII pur" in content
        assert "4 cues" in content  # sobriety cap
