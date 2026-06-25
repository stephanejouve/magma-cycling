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
        - ``N^ Text`` anchored cue, N = display duration in seconds
        - ``Text1. Text2. Text3.`` multiple cues spread across the step

        Plus minimal usage rules (sobriety, brevity, ASCII pure) and at
        least one positive + one negative example.

        Assertions use regex / structural patterns so the test does not
        break when the template wording is paraphrased (nit follow-up
        review #416 — string-match fragility).
        """
        import re

        template_file = _TEMPLATE_DIR / "peaks_methodology.md"
        content = template_file.read_text(encoding="utf-8")

        # Section header (case-insensitive; tolerates emoji prefix or none).
        assert re.search(r"^#+\s+.*Cues textuels intra-step", content, re.MULTILINE | re.IGNORECASE)

        # Grammar 1 — multi-cue example anywhere in the template:
        # at least one block line with ≥2 ``Text. Text.`` cues (cue may be
        # multiple words like ``Relache epaules.``) followed by the
        # duration / intensity / cadence tokens that the parser expects.
        multi_cue_re = re.compile(r"-\s+(?:\S[^.\n]*?\.\s+){2,}\d+m\s+\d+(?:-\d+)?%\s+\d+rpm")
        assert multi_cue_re.search(content), "Grammar 1 (Text. Text. Text. … rpm) missing"

        # Grammar 2 — anchored ``N^ Text`` example in a block line.
        anchored_re = re.compile(r"-\s+\d+\^\s+\S+.*?\d+m\s+\d+(?:-\d+)?%\s+\d+rpm")
        assert anchored_re.search(content), "Grammar 2 (N^ Text … rpm) missing"

        # NN^ must be described as a display duration (not an offset).
        assert re.search(r"dur[ée]e d'affichage", content, re.IGNORECASE)

        # At least one ✅ positive example and one ❌ negative example.
        assert "✅" in content
        assert "❌" in content

        # Sobriety / ASCII rules so the LLM doesn't spam cues or break parsing.
        # Use tolerant regex: number-of-cues cap + ASCII rule presence.
        assert re.search(r"\b[1-9]\b\s*cues?\b", content), "Cue-count cap missing"
        assert re.search(r"ASCII\s+pur", content, re.IGNORECASE)
