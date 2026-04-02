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
