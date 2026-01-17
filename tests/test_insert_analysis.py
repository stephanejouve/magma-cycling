"""
Tests for insert_analysis module.

Tests insertion d'analyses IA dans workouts-history.md avec validation.

GARTNER_TIME: I
STATUS: Production
PRIORITY: P1
"""

from unittest.mock import Mock

import pytest

from cyclisme_training_logs.insert_analysis import (
    AnalysisParser,
    ClipboardReader,
    WorkoutHistoryManager,
)


class TestClipboardReader:
    """Tests for ClipboardReader class."""

    def test_read_clipboard_success(self, monkeypatch):
        """Should read content from pbpaste successfully."""
        mock_result = Mock(stdout="Test content from clipboard", returncode=0)
        mock_subprocess = Mock(return_value=mock_result)
        monkeypatch.setattr("subprocess.run", mock_subprocess)

        result = ClipboardReader.read_clipboard()

        assert result == "Test content from clipboard"
        mock_subprocess.assert_called_once_with(
            ["pbpaste"], capture_output=True, text=True, check=True
        )

    def test_read_clipboard_failure_handles_error(self, monkeypatch, capsys):
        """Should handle pbpaste errors gracefully."""
        mock_subprocess = Mock(side_effect=Exception("pbpaste not found"))
        monkeypatch.setattr("subprocess.run", mock_subprocess)

        result = ClipboardReader.read_clipboard()

        assert result is None
        captured = capsys.readouterr()
        assert "❌ Erreur lecture presse-papier" in captured.out


class TestAnalysisParser:
    """Tests for AnalysisParser markdown extraction."""

    def test_extract_markdown_block_clean_format(self):
        """Should extract text already starting with ###."""
        text = """### S076-04-END-EnduranceBase-V001
Date : 15/01/2026

#### Métriques Pré-séance
- CTL : 43
"""
        result = AnalysisParser.extract_markdown_block(text)

        assert result.startswith("### S076-04")
        assert "#### Métriques Pré-séance" in result
        assert "CTL : 43" in result

    def test_extract_markdown_block_from_code_block(self):
        """Should extract from ```markdown blocks."""
        text = """Here is the analysis:

```markdown
### S076-04-END-EnduranceBase-V001
Date : 15/01/2026

#### Exécution
- Durée : 49min
```

That's the result."""

        result = AnalysisParser.extract_markdown_block(text)

        assert result.startswith("### S076-04")
        assert "#### Exécution" in result
        assert "Durée : 49min" in result
        assert "Here is the analysis" not in result
        assert "That's the result" not in result

    def test_extract_markdown_block_without_markdown_fence(self):
        """Should extract from first ### line to end."""
        text = """Some preamble text

### S076-04-END-EnduranceBase-V001
Date : 15/01/2026

Content here"""

        result = AnalysisParser.extract_markdown_block(text)

        assert result.startswith("### S076-04")
        assert "Some preamble text" not in result

    def test_extract_markdown_block_returns_text_if_no_markers(self, capsys):
        """Should return original text with warning if no ### found."""
        text = "Plain text without markdown headers"

        result = AnalysisParser.extract_markdown_block(text)

        assert result == "Plain text without markdown headers"
        captured = capsys.readouterr()
        assert "⚠️  Impossible de détecter" in captured.out

    def test_detect_session_type_executed(self):
        """Should detect executed sessions with technical sections."""
        text = """### S076-04-END-EnduranceBase-V001
Date : 15/01/2026

#### Exécution
- Durée : 49min

#### Charge d'Entraînement
TSS : 31"""

        result = AnalysisParser.detect_session_type(text)

        assert result == "executed"

    def test_detect_session_type_rest(self):
        """Should detect rest days."""
        text = """### S076-07-REPOS
Date : 21/01/2026

Repos planifié hebdomadaire"""

        result = AnalysisParser.detect_session_type(text)

        assert result == "rest"

    def test_detect_session_type_cancelled(self):
        """Should detect cancelled sessions."""
        text = """### S076-03-INT-SweetSpot
Date : 14/01/2026

Séance annulée en raison de fatigue."""

        result = AnalysisParser.detect_session_type(text)

        assert result == "cancelled"

    def test_detect_session_type_rest_with_alternate_markers(self):
        """Should detect rest with alternate markers."""
        text_with_day_of_rest = "Jour de repos planifié"
        assert AnalysisParser.detect_session_type(text_with_day_of_rest) == "rest"

        text_with_rest_day = "Rest day scheduled"
        assert AnalysisParser.detect_session_type(text_with_rest_day) == "rest"

    def test_detect_session_type_unknown_format(self):
        """Should return unknown for unrecognized format."""
        text = "Some random text without markers"

        result = AnalysisParser.detect_session_type(text)

        assert result == "unknown"


class TestWorkoutHistoryManager:
    """Tests for WorkoutHistoryManager."""

    @pytest.fixture
    def sample_history_file(self, tmp_path):
        """Create sample workouts-history.md file."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(
            """### S076-02-END-EnduranceBase-V001
Date : 13/01/2026

#### Métriques Pré-séance
- CTL : 44

---

### S076-01-END-EnduranceLegere-V001
Date : 12/01/2026

#### Métriques Pré-séance
- CTL : 44

---
"""
        )
        return history_file

    @pytest.mark.skip(reason="Mocking get_data_config inside __init__ is complex")
    def test_init_with_default_config(self, monkeypatch, tmp_path):
        """Should initialize with config from get_data_config."""
        # Note: Tested indirectly through other tests
        pass

    def test_init_with_explicit_logs_dir(self, tmp_path):
        """Should initialize with explicit logs_dir path."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        history_file = logs_dir / "workouts-history.md"
        history_file.touch()

        manager = WorkoutHistoryManager(logs_dir=logs_dir)

        assert manager.history_file == history_file

    def test_insert_analysis_from_text(self, tmp_path, sample_history_file):
        """Should insert analysis from provided text."""
        logs_dir = sample_history_file.parent

        # Use logs_dir parameter to avoid mocking
        manager = WorkoutHistoryManager(logs_dir=logs_dir, yes_confirm=True)

        analysis_text = """### S076-04-END-EnduranceProgressive-V001
Date : 15/01/2026

#### Métriques Pré-séance
- CTL : 43

---
"""

        result = manager.insert_analysis(analysis_text)

        assert result is True

        # Verify insertion happened
        content = sample_history_file.read_text()
        assert "S076-04-END-EnduranceProgressive-V001" in content
        assert "15/01/2026" in content

    def test_read_history_returns_content(self, tmp_path, sample_history_file, monkeypatch):
        """Should read existing history file content."""
        mock_config = Mock()
        mock_config.workouts_history_path = sample_history_file
        mock_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.get_data_config", lambda: mock_config
        )

        manager = WorkoutHistoryManager()
        content = manager.read_history()

        assert content is not None
        assert "S076-02-END-EnduranceBase-V001" in content
        assert "S076-01-END-EnduranceLegere-V001" in content

    def test_read_history_returns_none_if_missing(self, tmp_path, capsys):
        """Should return None if history file doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        manager = WorkoutHistoryManager(logs_dir=nonexistent_dir)
        content = manager.read_history()

        assert content is None
        captured = capsys.readouterr()
        assert "❌" in captured.out

    def test_check_duplicate_detects_existing_entry(
        self, tmp_path, sample_history_file, monkeypatch
    ):
        """Should detect duplicate session in history."""
        mock_config = Mock()
        mock_config.workouts_history_path = sample_history_file
        mock_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.get_data_config", lambda: mock_config
        )

        manager = WorkoutHistoryManager()
        content = sample_history_file.read_text()

        # Try to insert same session that already exists
        analysis_text = """### S076-02-END-EnduranceBase-V001
Date : 13/01/2026

Content
"""

        is_duplicate = manager.check_duplicate(content, analysis_text)

        assert is_duplicate is True

    def test_check_duplicate_returns_false_for_new_entry(
        self, tmp_path, sample_history_file, monkeypatch
    ):
        """Should return False for new session."""
        mock_config = Mock()
        mock_config.workouts_history_path = sample_history_file
        mock_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.get_data_config", lambda: mock_config
        )

        manager = WorkoutHistoryManager()
        content = sample_history_file.read_text()

        # New session
        analysis_text = """### S076-04-END-NewWorkout-V001
Date : 15/01/2026

Content
"""

        is_duplicate = manager.check_duplicate(content, analysis_text)

        assert is_duplicate is False


class TestCLIIntegration:
    """Tests for CLI argument parsing and main function."""

    def test_main_with_dry_run_flag(self, tmp_path, monkeypatch, capsys):
        """Should execute in dry-run mode when flag provided."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text("### Existing entry\n")

        mock_config = Mock()
        mock_config.workouts_history_path = history_file
        mock_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.get_data_config", lambda: mock_config
        )

        # Mock clipboard
        mock_clipboard = "### Test\nDate : 15/01/2026\n"
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.ClipboardReader.read_clipboard",
            lambda: mock_clipboard,
        )

        # Mock sys.argv
        monkeypatch.setattr("sys.argv", ["insert-analysis", "--dry-run", "--yes"])

        # Import and run main - expect SystemExit(0) on success
        from cyclisme_training_logs.insert_analysis import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0  # Successful dry-run exits with 0

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out or "🧪" in captured.out

    def test_main_with_file_argument(self, tmp_path, monkeypatch, capsys):
        """Should read analysis from file when --file provided."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text("### Existing entry\n")

        analysis_file = tmp_path / "analysis.md"
        analysis_file.write_text(
            """### S076-04-END-Test
Date : 15/01/2026

Content

---
"""
        )

        mock_config = Mock()
        mock_config.workouts_history_path = history_file
        mock_config.data_repo_path = tmp_path
        monkeypatch.setattr(
            "cyclisme_training_logs.insert_analysis.get_data_config", lambda: mock_config
        )

        monkeypatch.setattr(
            "sys.argv", ["insert-analysis", "--file", str(analysis_file), "--yes", "--dry-run"]
        )

        from cyclisme_training_logs.insert_analysis import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Should have processed file
        assert str(analysis_file) in captured.out or "S076-04" in captured.out


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parser_handles_malformed_markdown(self):
        """Should handle malformed markdown gracefully."""
        malformed = "## Wrong level header\n\nNo proper structure"

        result = AnalysisParser.extract_markdown_block(malformed)

        # Should return original with warning
        assert result == malformed

    def test_parser_handles_empty_text(self):
        """Should handle empty text."""
        result = AnalysisParser.extract_markdown_block("")

        assert result == ""

    def test_detect_session_type_handles_mixed_markers(self):
        """Should prioritize most specific marker."""
        # Has both rest and cancelled markers
        text = "Séance annulée - repos forcé"

        result = AnalysisParser.detect_session_type(text)

        # "annulée" should take priority (cancelled is more specific)
        assert result == "cancelled"

    def test_clipboard_reader_handles_unicode(self, monkeypatch):
        """Should handle unicode content from clipboard."""
        unicode_content = "Analyse: ✅ Séance réussie 🚴"
        mock_result = Mock(stdout=unicode_content, returncode=0)
        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_result)

        result = ClipboardReader.read_clipboard()

        assert result == unicode_content
        assert "✅" in result
        assert "🚴" in result
