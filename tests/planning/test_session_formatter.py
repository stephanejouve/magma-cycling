"""
Tests for session formatter utilities.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

from magma_cycling.planning.session_formatter import (
    format_remaining_sessions_compact,
)


class TestFormatRemainingSessionsCompact:
    """Test format_remaining_sessions_compact function."""

    def test_format_empty_sessions(self):
        """Test formatting empty sessions list."""
        result = format_remaining_sessions_compact([])

        assert result == ""

    def test_format_single_session(self):
        """Test formatting single session."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "EnduranceDouce",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "status": "planned",
            }
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "PLANNING RESTANT (1 séances)" in result
        assert "2026-03-05: S081-05-END-EnduranceDouce-V001 (50 TSS)" in result

    def test_format_multiple_sessions(self):
        """Test formatting multiple sessions."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "EnduranceDouce",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "status": "planned",
            },
            {
                "date": "2026-03-06",
                "session_id": "S081-06",
                "name": "Intervals",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "status": "planned",
            },
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "PLANNING RESTANT (2 séances)" in result
        assert "2026-03-05" in result
        assert "2026-03-06" in result
        assert "50 TSS" in result
        assert "70 TSS" in result

    def test_format_rest_day(self):
        """Test formatting rest day session."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "Repos",
                "type": "REST",
                "version": "V001",
                "tss_planned": 0,
                "status": "rest_day",
            }
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "2026-03-05: REPOS" in result

    def test_format_mixed_sessions(self):
        """Test formatting mix of regular and rest day sessions."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "EnduranceDouce",
                "type": "END",
                "version": "V001",
                "tss_planned": 50,
                "status": "planned",
            },
            {
                "date": "2026-03-06",
                "session_id": "S081-06",
                "name": "Repos",
                "type": "REST",
                "version": "V001",
                "tss_planned": 0,
                "status": "rest_day",
            },
            {
                "date": "2026-03-07",
                "session_id": "S081-07",
                "name": "Intervals",
                "type": "INT",
                "version": "V001",
                "tss_planned": 70,
                "status": "planned",
            },
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "PLANNING RESTANT (3 séances)" in result
        assert "2026-03-05: S081-05-END-EnduranceDouce-V001 (50 TSS)" in result
        assert "2026-03-06: REPOS" in result
        assert "2026-03-07: S081-07-INT-Intervals-V001 (70 TSS)" in result

    def test_format_session_without_version(self):
        """Test formatting session without version (uses default V001)."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "EnduranceDouce",
                "type": "END",
                "tss_planned": 50,
                "status": "planned",
                # No version field
            }
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "V001" in result  # Default version

    def test_format_session_without_tss(self):
        """Test formatting session without TSS (uses default 0)."""
        sessions = [
            {
                "date": "2026-03-05",
                "session_id": "S081-05",
                "name": "Recovery",
                "type": "END",
                "version": "V001",
                "status": "planned",
                # No tss_planned field
            }
        ]

        result = format_remaining_sessions_compact(sessions)

        assert "(0 TSS)" in result  # Default TSS
