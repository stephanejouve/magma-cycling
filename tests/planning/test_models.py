"""Tests for planning models — version normalization."""

from datetime import date

import pytest
from pydantic import ValidationError

from magma_cycling.planning.models import Session


class TestVersionNormalization:
    """Test version field_validator normalizes double-V prefix."""

    def _make_session(self, version: str) -> Session:
        return Session(
            session_id="S087-01",
            session_date=date(2026, 4, 6),
            name="EnduranceDouce",
            session_type="END",
            tss_planned=50,
            duration_min=60,
            version=version,
        )

    def test_version_normalization_VV001(self):
        """VV001 (double-V bug) is silently fixed to V001."""
        session = self._make_session("VV001")
        assert session.version == "V001"

    def test_version_valid_V001(self):
        """V001 remains V001 — no mutation."""
        session = self._make_session("V001")
        assert session.version == "V001"

    def test_version_V002_unchanged(self):
        """V002 remains V002."""
        session = self._make_session("V002")
        assert session.version == "V002"

    def test_version_invalid_rejected(self):
        """Invalid version pattern is rejected by pydantic."""
        with pytest.raises(ValidationError):
            self._make_session("X001")


class TestSessionTypeEnum:
    """Session.session_type accepts only the unified enum (13 types)."""

    ALL_VALID_TYPES = [
        "END",
        "INT",
        "REC",
        "RACE",
        "TEC",
        "SS",
        "FTP",
        "SPR",
        "CLM",
        "TT",
        "TMP",
        "MIX",
        "VO2",
    ]

    def _make_session(self, session_type: str) -> Session:
        return Session(
            session_id="S087-01",
            session_date=date(2026, 4, 6),
            name="TestSession",
            session_type=session_type,
            tss_planned=50,
            duration_min=60,
        )

    @pytest.mark.parametrize("valid_type", ALL_VALID_TYPES)
    def test_all_valid_types_accepted(self, valid_type: str):
        """Each of the 11 unified enum types is accepted."""
        session = self._make_session(valid_type)
        assert session.session_type == valid_type

    @pytest.mark.parametrize("invalid_type", ["XYZ", "CAD", "ENDURO", "", "end"])
    def test_invalid_types_rejected(self, invalid_type: str):
        """Types outside the unified enum are rejected at Pydantic level.

        Regression : the TEC issue on S093-03 (2026-05-11) was caused by
        ``session_type: str`` being permissive. Now ``Literal[...]`` rejects
        anything not in the enum, providing the write-side guard rail
        requested in the bug report.
        """
        with pytest.raises(ValidationError):
            self._make_session(invalid_type)
