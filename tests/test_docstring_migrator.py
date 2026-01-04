"""
Tests for docstring migration to Google Style.

Metadata:
    Created: 2025-12-27
    Author: Cyclisme Training Logs Team
    Category: TEST
    Status: Development
    Priority: P1
    Version: 1.0.0
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "maintenance"))

from migrate_docstrings import DocstringMetadata, DocstringMigrator  # noqa: E402


@pytest.fixture
def sample_old_docstring():
    """Sample file with old GARTNER_TIME format."""
    return '''"""

Configuration centrale pour séparation code/données

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0
DOCSTRING: v2

Module de configuration gérant la séparation entre code et données.
"""
from pathlib import Path

'''


@pytest.fixture
def temp_python_file(tmp_path, sample_old_docstring):
    """Create temporary Python file with old format."""
    test_file = tmp_path / "test_module.py"

    test_file.write_text(sample_old_docstring)
    return test_file


def test_parse_old_docstring(sample_old_docstring):
    """Test parsing of old GARTNER_TIME format."""
    migrator = DocstringMigrator(project_root=Path.cwd())

    metadata = migrator.parse_old_docstring(sample_old_docstring)

    assert metadata is not None
    assert metadata.category == "I"
    assert metadata.status == "Production"
    assert metadata.priority == "P0"
    assert metadata.version == "v2"


def test_generate_google_style():
    """Test Google Style docstring generation."""
    metadata = DocstringMetadata(
        category="CORE",
        status="Production",
        last_review="2025-12-27",
        priority="P0",
        version="1.0",
        description="Brief summary.\n\nExtended description.",
    )

    migrator = DocstringMigrator(project_root=Path.cwd())
    result = migrator.generate_google_style_docstring(metadata)

    assert "Brief summary." in result
    assert "Metadata:" in result
    assert "Created: 2025-12-27" in result
    assert "Category: CORE" in result
    assert "Priority: P0" in result


def test_migrate_file(temp_python_file):
    """Test file migration with backup."""
    migrator = DocstringMigrator(project_root=temp_python_file.parent, backup=True, dry_run=False)

    # Migrate
    result = migrator.migrate_file(temp_python_file)
    assert result is True

    # Verify backup created
    backup_file = temp_python_file.with_suffix(".py.bak")
    assert backup_file.exists()

    # Verify new content
    new_content = temp_python_file.read_text()
    assert "Metadata:" in new_content
    assert "GARTNER_TIME:" not in new_content


def test_dry_run_mode(temp_python_file):
    """Test dry-run mode doesn't modify files."""
    original_content = temp_python_file.read_text()

    migrator = DocstringMigrator(project_root=temp_python_file.parent, backup=False, dry_run=True)

    migrator.migrate_file(temp_python_file)

    # File should be unchanged
    assert temp_python_file.read_text() == original_content


def test_no_old_format(tmp_path):
    """Test file without old format is skipped."""
    test_file = tmp_path / "test_module.py"

    test_file.write_text('"""Already Google Style."""\n\nimport os')

    migrator = DocstringMigrator(project_root=tmp_path, backup=False, dry_run=False)

    result = migrator.migrate_file(test_file)
    assert result is False
    assert migrator.stats["skipped"] == 1
