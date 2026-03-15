"""Tests for planning.backup module.

Tests PlanningBackup : backup, restore, list, cleanup avec tmp_path.
"""

from magma_cycling.planning.backup import PlanningBackup


class TestBackupFile:
    """Tests for backup_file()."""

    def test_backup_creates_timestamped_copy(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        source = planning_dir / "week_planning_S081.json"
        source.write_text('{"week": "S081"}')

        backup = PlanningBackup(planning_dir=planning_dir)
        result = backup.backup_file(source)

        assert result is not None
        assert result.exists()
        assert "week_planning_S081" in result.name
        assert result.read_text() == '{"week": "S081"}'

    def test_backup_nonexistent_file_returns_none(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        backup = PlanningBackup(planning_dir=planning_dir)
        result = backup.backup_file(planning_dir / "missing.json")

        assert result is None

    def test_backup_dir_created_automatically(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        PlanningBackup(planning_dir=planning_dir)
        assert (planning_dir / "backups").exists()


class TestBackupWeekFiles:
    """Tests for backup_week_files()."""

    def test_backup_json_and_workouts(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S081.json").write_text('{"week": "S081"}')
        (planning_dir / "S081_workouts.txt").write_text("workout 1\nworkout 2")

        backup = PlanningBackup(planning_dir=planning_dir)
        result = backup.backup_week_files("S081")

        assert "json" in result
        assert "workouts" in result
        assert result["json"].exists()
        assert result["workouts"].exists()

    def test_backup_only_json(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        (planning_dir / "week_planning_S081.json").write_text('{"week": "S081"}')

        backup = PlanningBackup(planning_dir=planning_dir)
        result = backup.backup_week_files("S081")

        assert "json" in result
        assert "workouts" not in result

    def test_backup_no_files(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        backup = PlanningBackup(planning_dir=planning_dir)
        result = backup.backup_week_files("S999")

        assert result == {}


class TestListBackups:
    """Tests for list_backups()."""

    def test_list_all_backups(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        backup = PlanningBackup(planning_dir=planning_dir)

        # Create some backup files manually
        (backup.backup_dir / "week_planning_S081_20260220_100000.json").write_text("{}")
        (backup.backup_dir / "week_planning_S082_20260221_100000.json").write_text("{}")

        result = backup.list_backups()
        assert len(result) == 2

    def test_list_filtered_by_week(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        backup = PlanningBackup(planning_dir=planning_dir)

        (backup.backup_dir / "week_planning_S081_20260220_100000.json").write_text("{}")
        (backup.backup_dir / "week_planning_S082_20260221_100000.json").write_text("{}")

        result = backup.list_backups(week_id="S081")
        assert len(result) == 1
        assert "S081" in result[0].name


class TestRestoreBackup:
    """Tests for restore_backup()."""

    def test_restore_backup(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        # Create and backup a file
        source = planning_dir / "week_planning_S081.json"
        source.write_text('{"version": 1}')

        backup = PlanningBackup(planning_dir=planning_dir)
        backup_path = backup.backup_file(source)

        # Delete original so restore doesn't create conflicting backup
        source.unlink()

        # Restore
        restored = backup.restore_backup(backup_path)
        assert restored is not None
        assert restored.read_text() == '{"version": 1}'

    def test_restore_nonexistent_returns_none(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        backup = PlanningBackup(planning_dir=planning_dir)

        result = backup.restore_backup(planning_dir / "missing_backup.json")
        assert result is None

    def test_restore_dry_run(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        source = planning_dir / "week_planning_S081.json"
        source.write_text('{"version": 1}')

        backup = PlanningBackup(planning_dir=planning_dir)
        backup_path = backup.backup_file(source)

        source.write_text('{"version": 2}')
        restored = backup.restore_backup(backup_path, dry_run=True)

        assert restored is not None
        # Original should NOT be changed in dry_run
        assert source.read_text() == '{"version": 2}'


class TestCleanupOldBackups:
    """Tests for cleanup_old_backups()."""

    def test_cleanup_keeps_recent(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        backup = PlanningBackup(planning_dir=planning_dir)

        # Create 5 backups for same base file
        for i in range(5):
            name = f"week_planning_S081_20260220_{i:06d}.json"
            (backup.backup_dir / name).write_text("{}")

        deleted = backup.cleanup_old_backups(keep_count=2)
        assert deleted == 3

        remaining = backup.list_backups(week_id="S081")
        assert len(remaining) == 2

    def test_cleanup_zero_to_delete(self, tmp_path):
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        backup = PlanningBackup(planning_dir=planning_dir)

        (backup.backup_dir / "week_planning_S081_20260220_100000.json").write_text("{}")

        deleted = backup.cleanup_old_backups(keep_count=10)
        assert deleted == 0
