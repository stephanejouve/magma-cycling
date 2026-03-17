"""Tests for workflows.eow.upload module.

Tests UploadMixin : dry_run, validation, upload auto/manual, save planning JSON.
Utilise stub + mocks pour isoler les dépendances API.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from magma_cycling.workflows.eow.upload import UploadMixin


class StubEowWorkflow(UploadMixin):
    """Stub providing required attributes for UploadMixin methods."""

    def __init__(
        self,
        *,
        dry_run=False,
        workouts_file=None,
        week_next="S081",
        next_start_date=None,
        next_end_date=None,
        auto=False,
        planning_dir=None,
    ):
        self.dry_run = dry_run
        self.workouts_file = workouts_file
        self.week_next = week_next
        self.next_start_date = next_start_date or date(2026, 3, 16)
        self.next_end_date = next_end_date or date(2026, 3, 22)
        self.auto = auto
        self.planning_dir = planning_dir


VALID_WORKOUTS_CONTENT = """\
=== WORKOUT S081-01-END-RepriseLundi-V001 ===
Reprise Douce Lundi (60min, 45 TSS)
- Warmup: 15min Z1
- Main set: 30min Z2
- Cooldown: 15min Z1
=== FIN WORKOUT ===

=== WORKOUT S081-03-INT-Intervalles-V001 ===
Intervalles Mercredi (75min, 80 TSS)
- Warmup: 15min Z1-Z2
- Main set: 5x4min Z4 / 3min Z1
- Cooldown: 15min Z1
=== FIN WORKOUT ===
"""


class TestStep4ValidateWorkouts:
    """Tests for _step4_validate_workouts()."""

    def test_dry_run_returns_true(self):
        wf = StubEowWorkflow(dry_run=True)
        assert wf._step4_validate_workouts() is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_no_workouts_file_returns_false(self, mock_uploader_cls):
        wf = StubEowWorkflow(dry_run=False, workouts_file=None)
        assert wf._step4_validate_workouts() is False

    @patch("magma_cycling.workflows.eow.upload.UploadMixin._step4_validate_workouts")
    def test_validate_called(self, mock_validate):
        """Verify _step4 is callable and returns expected value."""
        mock_validate.return_value = True
        wf = StubEowWorkflow()
        assert wf._step4_validate_workouts() is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_valid_workouts_file_returns_true(self, mock_uploader_cls, tmp_path):
        """Test with valid workouts file that passes validation."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        mock_uploader = MagicMock()
        mock_uploader.parse_workouts_file.return_value = [{"name": "test"}]
        mock_uploader_cls.return_value = mock_uploader

        wf = StubEowWorkflow(dry_run=False, workouts_file=f, week_next="S081")
        result = wf._step4_validate_workouts()

        assert result is True

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_empty_parse_result_returns_false(self, mock_uploader_cls, tmp_path):
        """Test with workouts file that fails validation (empty parse)."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text("invalid content")

        mock_uploader = MagicMock()
        mock_uploader.parse_workouts_file.return_value = []
        mock_uploader_cls.return_value = mock_uploader

        wf = StubEowWorkflow(dry_run=False, workouts_file=f, week_next="S081")
        result = wf._step4_validate_workouts()

        assert result is False

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_exception_returns_false(self, mock_uploader_cls, tmp_path):
        """Test that exception during validation returns False."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text("content")

        mock_uploader_cls.side_effect = Exception("Import error")

        wf = StubEowWorkflow(dry_run=False, workouts_file=f, week_next="S081")
        result = wf._step4_validate_workouts()

        assert result is False


class TestStep5UploadWorkouts:
    """Tests for _step5_upload_workouts()."""

    def test_dry_run_returns_true(self):
        wf = StubEowWorkflow(dry_run=True)
        assert wf._step5_upload_workouts() is True

    def test_no_workouts_file_returns_false(self):
        wf = StubEowWorkflow(dry_run=False, workouts_file=None)
        assert wf._step5_upload_workouts() is False

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_auto_mode_success(self, mock_uploader_cls, tmp_path):
        """Test auto mode upload with all workouts succeeding."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        mock_uploader = MagicMock()
        mock_uploader.parse_workouts_file.return_value = [
            {"name": "w1"},
            {"name": "w2"},
        ]
        mock_uploader.upload_all.return_value = {
            "success": 2,
            "total": 2,
            "errors": [],
        }
        mock_uploader_cls.return_value = mock_uploader

        wf = StubEowWorkflow(
            dry_run=False,
            workouts_file=f,
            week_next="S081",
            auto=True,
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
        )
        result = wf._step5_upload_workouts()

        assert result is True
        mock_uploader.upload_all.assert_called_once()

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_auto_mode_partial_failure(self, mock_uploader_cls, tmp_path):
        """Test auto mode upload with some failures."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        mock_uploader = MagicMock()
        mock_uploader.parse_workouts_file.return_value = [{"name": "w1"}]
        mock_uploader.upload_all.return_value = {
            "success": 0,
            "total": 1,
            "errors": ["Upload failed"],
        }
        mock_uploader_cls.return_value = mock_uploader

        wf = StubEowWorkflow(
            dry_run=False,
            workouts_file=f,
            week_next="S081",
            auto=True,
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
        )
        result = wf._step5_upload_workouts()

        assert result is False

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_auto_mode_empty_parse(self, mock_uploader_cls, tmp_path):
        """Test auto mode when parse returns empty."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text("invalid")

        mock_uploader = MagicMock()
        mock_uploader.parse_workouts_file.return_value = []
        mock_uploader_cls.return_value = mock_uploader

        wf = StubEowWorkflow(
            dry_run=False,
            workouts_file=f,
            week_next="S081",
            auto=True,
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
        )
        result = wf._step5_upload_workouts()

        assert result is False

    @patch("magma_cycling.upload_workouts.WorkoutUploader")
    def test_auto_mode_exception(self, mock_uploader_cls, tmp_path):
        """Test auto mode when exception occurs."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text("content")

        mock_uploader_cls.side_effect = Exception("Connection error")

        wf = StubEowWorkflow(
            dry_run=False,
            workouts_file=f,
            week_next="S081",
            auto=True,
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
        )
        result = wf._step5_upload_workouts()

        assert result is False


class TestStep5bSavePlanningJson:
    """Tests for _step5b_save_planning_json()."""

    def test_no_workouts_file_returns_early(self):
        """Test that no workouts file skips JSON save gracefully."""
        wf = StubEowWorkflow(workouts_file=None)
        # Should not raise
        wf._step5b_save_planning_json()

    @patch("magma_cycling.workflows.eow.upload.audit_log")
    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.api.intervals_client.IntervalsClient")
    def test_save_planning_json_creates_file(
        self, mock_client_cls, mock_config, mock_audit, tmp_path
    ):
        """Test full planning JSON creation flow."""
        # Setup workouts file
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        # Mock config
        config = MagicMock()
        config.athlete_id = "iXXXXXX"
        config.api_key = "fake_key"
        mock_config.return_value = config

        # Mock client with matching events
        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "name": "S081-01-END-RepriseLundi-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-16T08:00:00",
            },
            {
                "id": 200,
                "name": "S081-03-INT-Intervalles-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-18T08:00:00",
            },
        ]
        mock_client_cls.return_value = mock_client

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
            planning_dir=planning_dir,
        )
        wf._step5b_save_planning_json()

        # Verify JSON file created
        json_file = planning_dir / "week_planning_S081.json"
        assert json_file.exists()

        # Verify audit log called
        mock_audit.log_operation.assert_called_once()

    @patch("magma_cycling.workflows.eow.upload.audit_log")
    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.api.intervals_client.IntervalsClient")
    def test_save_planning_json_session_count(
        self, mock_client_cls, mock_config, mock_audit, tmp_path
    ):
        """Test that correct number of sessions are saved."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        config = MagicMock()
        config.athlete_id = "iXXXXXX"
        config.api_key = "fake_key"
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "name": "S081-01-END-RepriseLundi-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-16T08:00:00",
            },
            {
                "id": 200,
                "name": "S081-03-INT-Intervalles-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-18T08:00:00",
            },
        ]
        mock_client_cls.return_value = mock_client

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
            planning_dir=planning_dir,
        )
        wf._step5b_save_planning_json()

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(planning_dir / "week_planning_S081.json")
        assert len(plan.planned_sessions) == 2
        assert plan.planned_sessions[0].session_id == "S081-01"
        assert plan.planned_sessions[1].session_id == "S081-03"

    @patch("magma_cycling.workflows.eow.upload.audit_log")
    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.api.intervals_client.IntervalsClient")
    def test_save_planning_json_tss_total(self, mock_client_cls, mock_config, mock_audit, tmp_path):
        """Test that TSS total is correctly calculated."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        config = MagicMock()
        config.athlete_id = "iXXXXXX"
        config.api_key = "fake_key"
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "name": "S081-01-END-RepriseLundi-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-16T08:00:00",
            },
            {
                "id": 200,
                "name": "S081-03-INT-Intervalles-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-18T08:00:00",
            },
        ]
        mock_client_cls.return_value = mock_client

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
            planning_dir=planning_dir,
        )
        wf._step5b_save_planning_json()

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(planning_dir / "week_planning_S081.json")
        # 45 + 80 = 125 TSS from workout metadata
        assert plan.tss_target == 125

    @patch("magma_cycling.config.get_intervals_config")
    def test_save_planning_json_exception_non_blocking(self, mock_config, tmp_path):
        """Test that exception in _step5b is non-blocking."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        mock_config.side_effect = Exception("Config not available")

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            planning_dir=tmp_path,
        )
        # Should not raise
        wf._step5b_save_planning_json()

    @patch("magma_cycling.workflows.eow.upload.audit_log")
    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.api.intervals_client.IntervalsClient")
    def test_save_filters_non_workout_events(
        self, mock_client_cls, mock_config, mock_audit, tmp_path
    ):
        """Test that non-WORKOUT events are filtered out."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        config = MagicMock()
        config.athlete_id = "iXXXXXX"
        config.api_key = "fake_key"
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "name": "S081-01-END-RepriseLundi-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-03-16T08:00:00",
            },
            {
                "id": 300,
                "name": "[ANNULÉE] S081-02 Cancelled",
                "category": "NOTE",
                "start_date_local": "2026-03-17T08:00:00",
            },
            {
                "id": 400,
                "name": "Other event",
                "category": "WORKOUT",
                "start_date_local": "2026-03-19T08:00:00",
            },
        ]
        mock_client_cls.return_value = mock_client

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
            planning_dir=planning_dir,
        )
        wf._step5b_save_planning_json()

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(planning_dir / "week_planning_S081.json")
        # Only 1 event: S081 WORKOUT. NOTE is filtered, "Other event" doesn't start with S081
        assert len(plan.planned_sessions) == 1

    @patch("magma_cycling.workflows.eow.upload.audit_log")
    @patch("magma_cycling.config.get_intervals_config")
    @patch("magma_cycling.api.intervals_client.IntervalsClient")
    def test_save_skips_invalid_workout_names(
        self, mock_client_cls, mock_config, mock_audit, tmp_path
    ):
        """Test that workouts with invalid name format are skipped."""
        f = tmp_path / "S081_workouts.txt"
        f.write_text(VALID_WORKOUTS_CONTENT)

        config = MagicMock()
        config.athlete_id = "iXXXXXX"
        config.api_key = "fake_key"
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.get_events.return_value = [
            {
                "id": 100,
                "name": "S081-InvalidFormat",
                "category": "WORKOUT",
                "start_date_local": "2026-03-16T08:00:00",
            },
        ]
        mock_client_cls.return_value = mock_client

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        wf = StubEowWorkflow(
            workouts_file=f,
            week_next="S081",
            next_start_date=date(2026, 3, 16),
            next_end_date=date(2026, 3, 22),
            planning_dir=planning_dir,
        )
        wf._step5b_save_planning_json()

        from magma_cycling.planning.models import WeeklyPlan

        plan = WeeklyPlan.from_json(planning_dir / "week_planning_S081.json")
        assert len(plan.planned_sessions) == 0
