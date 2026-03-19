"""Tests for validate_naming_convention module.

Tests NamingValidator : validation regex noms de répertoires/fichiers weekly_reports.
"""

import json
from unittest.mock import patch

import pytest

from magma_cycling.validate_naming_convention import NamingValidator, main


class TestValidateDirectoryName:
    """Tests for validate_directory_name()."""

    def test_valid_directory_uppercase(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("S001")
        assert result["valid"] is True
        assert result["issues"] == []

    def test_valid_directory_high_number(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("S999")
        assert result["valid"] is True

    def test_lowercase_directory_detected(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("s001")
        assert result["valid"] is False
        assert any("Minuscule" in i for i in result["issues"])

    def test_invalid_format(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("Week01")
        assert result["valid"] is False
        assert any("Format invalide" in i for i in result["issues"])

    def test_too_few_digits(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("S01")
        assert result["valid"] is False

    def test_too_many_digits(self):
        validator = NamingValidator()
        result = validator.validate_directory_name("S0001")
        assert result["valid"] is False


class TestValidateFileName:
    """Tests for validate_file_name()."""

    def test_valid_file_name(self):
        validator = NamingValidator()
        result = validator.validate_file_name("bilan_hebdomadaire_S072.md", "S072")
        assert result["valid"] is True

    def test_valid_file_with_two_weeks(self):
        validator = NamingValidator()
        result = validator.validate_file_name("bilan_S072_S073.md", "S072")
        assert result["valid"] is True

    def test_lowercase_week_number(self):
        validator = NamingValidator()
        result = validator.validate_file_name("bilan_hebdomadaire_s072.md", "s072")
        assert result["valid"] is False
        assert any("Minuscule" in i for i in result["issues"])

    def test_invalid_format(self):
        validator = NamingValidator()
        result = validator.validate_file_name("README.md", "S072")
        assert result["valid"] is False

    def test_result_includes_parent(self):
        validator = NamingValidator()
        result = validator.validate_file_name("bilan_S072.md", "S072")
        assert result["parent"] == "S072"


class TestValidateStructure:
    """Tests for validate_structure() with tmp_path."""

    def test_missing_weekly_dir(self, tmp_path):
        validator = NamingValidator(project_root=str(tmp_path))
        assert validator.validate_structure() is False

    def test_valid_structure(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_hebdomadaire_S072.md").write_text("# Bilan")
        (weekly / "S073").mkdir()
        (weekly / "S073" / "bilan_hebdomadaire_S073.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        assert validator.validate_structure() is True
        assert len(validator.issues) == 0

    def test_detects_lowercase_dir(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "s072").mkdir()

        validator = NamingValidator(project_root=str(tmp_path))
        assert validator.validate_structure() is False
        assert len(validator.issues) == 1
        assert validator.issues[0]["type"] == "directory"

    def test_detects_lowercase_file(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_s072.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        assert validator.validate_structure() is False
        assert len(validator.issues) == 1
        assert validator.issues[0]["type"] == "file"

    def test_ignores_non_directories(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "readme.txt").write_text("info")

        validator = NamingValidator(project_root=str(tmp_path))
        assert validator.validate_structure() is True


class TestGetJsonReport:
    """Tests for get_json_report()."""

    def test_json_report_valid_structure(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        report = json.loads(validator.get_json_report())
        assert report["valid"] is True
        assert report["stats"]["directories"] == 1
        assert report["stats"]["files"] == 1
        assert report["stats"]["issues"] == 0

    def test_json_report_with_issues(self, tmp_path):
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "s001").mkdir()

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        report = json.loads(validator.get_json_report())
        assert report["valid"] is False
        assert report["stats"]["issues"] == 1

    def test_json_report_missing_dir(self, tmp_path):
        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        report = json.loads(validator.get_json_report())
        assert report["stats"]["directories"] == 0


class TestPrintReport:
    """Tests for print_report() output."""

    def test_print_report_no_issues(self, tmp_path, capsys):
        """Test report output when structure is valid."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        validator.print_report()

        output = capsys.readouterr().out
        assert "VALIDATION CONVENTIONS NOMMAGE" in output
        assert "TOUS CONFORME" in output
        assert "Répertoires : 1" in output
        assert "Fichiers .md : 1" in output

    def test_print_report_with_dir_issues(self, tmp_path, capsys):
        """Test report output with directory naming issues."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "s001").mkdir()

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        validator.print_report()

        output = capsys.readouterr().out
        assert "1 PROBLÈME(S) DÉTECTÉ(S)" in output
        assert "Répertoires (1)" in output
        assert "s001" in output

    def test_print_report_with_file_issues(self, tmp_path, capsys):
        """Test report output with file naming issues."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_s072.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        validator.print_report()

        output = capsys.readouterr().out
        assert "1 PROBLÈME(S) DÉTECTÉ(S)" in output
        assert "Fichiers (1)" in output
        assert "S072/bilan_s072.md" in output

    def test_print_report_missing_dir(self, tmp_path, capsys):
        """Test report output when weekly_reports directory is missing."""
        validator = NamingValidator(project_root=str(tmp_path))
        validator.print_report()

        output = capsys.readouterr().out
        assert "Répertoire non trouvé" in output

    def test_print_report_verbose(self, tmp_path, capsys):
        """Test verbose report lists all conforming files."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        validator = NamingValidator(project_root=str(tmp_path))
        validator.validate_structure()
        validator.print_report(verbose=True)

        output = capsys.readouterr().out
        assert "Détail structure conforme" in output
        assert "S072/" in output
        assert "bilan_S072.md" in output


class TestMain:
    """Tests for main() CLI entry point."""

    def test_main_valid_structure(self, tmp_path):
        """Test main with valid structure exits 0."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        with patch("sys.argv", ["prog", "--project-root", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_invalid_structure_exits_1(self, tmp_path):
        """Test main with invalid structure exits 1."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "s001").mkdir()

        with patch("sys.argv", ["prog", "--project-root", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_json_output(self, tmp_path, capsys):
        """Test main with --json flag produces JSON output."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        with patch("sys.argv", ["prog", "--project-root", str(tmp_path), "--json"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        output = capsys.readouterr().out
        report = json.loads(output)
        assert report["valid"] is True

    def test_main_verbose_flag(self, tmp_path):
        """Test main with --verbose flag exits successfully."""
        weekly = tmp_path / "logs" / "weekly_reports"
        weekly.mkdir(parents=True)
        (weekly / "S072").mkdir()
        (weekly / "S072" / "bilan_S072.md").write_text("# Bilan")

        with patch("sys.argv", ["prog", "--project-root", str(tmp_path), "--verbose"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
