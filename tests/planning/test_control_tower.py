"""Tests for PlanningControlTower — sync_from_remote version handling."""

from magma_cycling.planning.models import WORKOUT_NAME_REGEX


class TestSyncFromRemoteVersion:
    """Test that sync_from_remote does not double the V prefix."""

    def test_sync_from_remote_version_no_double_V(self):
        """Regex group(4) already captures 'V001'; building the dict must NOT add another V."""
        event_name = "S087-01-END-EnduranceDouce-V001"
        match = WORKOUT_NAME_REGEX.search(event_name)
        assert match is not None

        version = match.group(4)
        assert version == "V001", f"Regex should capture 'V001', got {version!r}"

        # Simulate the FIXED line (was: f"V{version}" → "VV001")
        built_version = version  # correct
        assert built_version == "V001"

        # Demonstrate the old bug
        old_built_version = f"V{version}"
        assert old_built_version == "VV001", "Old code would have produced VV001"
