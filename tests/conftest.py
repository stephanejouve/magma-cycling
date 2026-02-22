"""
Pytest configuration.

Tests use TRAINING_DATA_REPO environment variable pointing to test-data/ directory.
No global mocks - test-data/ contains all required files for testing.
"""

import os
from pathlib import Path

import pytest

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Set up test environment."""
    # Ensure TRAINING_DATA_REPO points to test-data directory
    repo_root = Path(__file__).parent.parent
    test_data = repo_root / "test-data"

    if not test_data.exists():
        pytest.exit(f"test-data directory not found at {test_data}")

    # Set environment variable for all tests
    os.environ["TRAINING_DATA_REPO"] = str(test_data)
    os.environ["DATA_REPO_PATH"] = str(test_data)
