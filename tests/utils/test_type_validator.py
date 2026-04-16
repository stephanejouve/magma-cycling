"""Tests for semantic type ↔ content validator."""

from magma_cycling.utils.type_validator import TypeValidation, validate_session_type


class TestRecovery:
    """REC sessions: low TSS, no intensity keywords."""

    def test_valid_rec(self):
        result = validate_session_type("REC", "Repos complet", tss=0)
        assert result.valid is True

    def test_rec_high_tss(self):
        result = validate_session_type("REC", "Récup facile Z1", tss=55)
        assert result.valid is False
        assert any("TSS=55" in w for w in result.warnings)

    def test_rec_with_intensity_keywords(self):
        result = validate_session_type("REC", "3x12min à 90% FTP intervalles", tss=0)
        assert result.valid is False
        assert result.suggested_type == "INT"

    def test_rec_with_ftp_keyword(self):
        result = validate_session_type("REC", "Maintien FTP steady state", tss=30)
        assert result.valid is False


class TestEndurance:
    """END sessions: no structured intervals."""

    def test_valid_end(self):
        result = validate_session_type("END", "Endurance Z2 2h 75rpm", tss=70)
        assert result.valid is True

    def test_end_with_intervals(self):
        result = validate_session_type("END", "2x20min sweet spot", tss=75)
        assert result.valid is False
        assert result.suggested_type == "INT"

    def test_end_no_intervals(self):
        result = validate_session_type("END", "Long ride Z2 steady cadence", tss=80)
        assert result.valid is True


class TestIntensity:
    """INT/VO2/MAP/FRC sessions: should have intensity markers."""

    def test_valid_int(self):
        result = validate_session_type("INT", "4x8min @ 95% FTP", tss=70)
        assert result.valid is True

    def test_int_low_tss_no_keywords(self):
        result = validate_session_type("INT", "Easy spinning", tss=20)
        assert result.valid is False
        assert result.suggested_type == "REC"

    def test_int_with_keywords_low_tss(self):
        """INT with intensity keywords but low TSS should pass (keywords present)."""
        result = validate_session_type("INT", "Neuromuscular sprint efforts", tss=25)
        assert result.valid is True

    def test_vo2_valid(self):
        result = validate_session_type("VO2", "5x4min VO2max 110% FTP", tss=80)
        assert result.valid is True

    def test_map_low_tss_no_keywords(self):
        result = validate_session_type("MAP", "Easy ride", tss=15)
        assert result.valid is False

    def test_frc_valid(self):
        result = validate_session_type("FRC", "6x30s force sprint max", tss=50)
        assert result.valid is True


class TestOtherTypes:
    """Types not explicitly covered should always pass."""

    def test_unknown_type(self):
        result = validate_session_type("RACE", "Race day 100km", tss=150)
        assert result.valid is True

    def test_tempo_type(self):
        result = validate_session_type("TMP", "Tempo steady 88%", tss=65)
        assert result.valid is True


class TestEdgeCases:
    def test_none_tss(self):
        result = validate_session_type("REC", "Repos", tss=None)
        assert result.valid is True

    def test_empty_description(self):
        result = validate_session_type("INT", "", tss=0)
        assert result.valid is False

    def test_dataclass_structure(self):
        result = validate_session_type("REC", "test", tss=0)
        assert isinstance(result, TypeValidation)
        assert isinstance(result.warnings, list)
