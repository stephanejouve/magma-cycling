"""Tests for reports.templates module.

Tests BilanFinalTemplate et WorkoutHistoryTemplate : structure, champs requis, guidelines.
"""

from magma_cycling.reports.templates import BilanFinalTemplate, WorkoutHistoryTemplate


class TestBilanFinalTemplate:
    """Tests for BilanFinalTemplate."""

    def test_report_type(self):
        assert BilanFinalTemplate.REPORT_TYPE == "bilan_final"

    def test_max_word_count(self):
        assert BilanFinalTemplate.MAX_WORD_COUNT == 1500

    def test_required_data_fields(self):
        fields = BilanFinalTemplate.get_required_data()
        assert isinstance(fields, list)
        assert "week_number" in fields
        assert "objectives" in fields
        assert "metrics_final" in fields

    def test_structure_has_sections(self):
        structure = BilanFinalTemplate.get_structure()
        assert "sections" in structure
        assert len(structure["sections"]) > 0
        assert "Métriques Finales" in structure["sections"]

    def test_structure_format(self):
        structure = BilanFinalTemplate.get_structure()
        assert structure["format"] == "markdown"
        assert structure["language"] == "fr"
        assert structure["max_length"] == 1500

    def test_format_guidelines(self):
        guidelines = BilanFinalTemplate.get_format_guidelines()
        assert guidelines["discoveries_max"] == 4
        assert guidelines["conclusion_sentences"] == 3
        assert "constraints" in guidelines
        assert len(guidelines["constraints"]) > 0


class TestWorkoutHistoryTemplate:
    """Tests for WorkoutHistoryTemplate."""

    def test_report_type(self):
        assert WorkoutHistoryTemplate.REPORT_TYPE == "workout_history"

    def test_max_word_count(self):
        assert WorkoutHistoryTemplate.MAX_WORD_COUNT == 2000

    def test_required_data_fields(self):
        fields = WorkoutHistoryTemplate.get_required_data()
        assert isinstance(fields, list)
        assert "week_number" in fields
        assert "activities" in fields
        assert "wellness_data" in fields

    def test_structure_has_sections(self):
        structure = WorkoutHistoryTemplate.get_structure()
        assert "sections" in structure
        assert "Chronologie Complète" in structure["sections"]

    def test_structure_format(self):
        structure = WorkoutHistoryTemplate.get_structure()
        assert structure["format"] == "markdown"
        assert structure["language"] == "fr"
        assert structure["max_length"] == 2000
        assert structure["style"] == "factual"

    def test_format_guidelines(self):
        guidelines = WorkoutHistoryTemplate.get_format_guidelines()
        assert "session_format" in guidelines
        assert "constraints" in guidelines
        assert any("2000" in c for c in guidelines["constraints"])
