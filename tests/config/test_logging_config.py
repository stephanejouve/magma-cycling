"""Tests for logging_config — non-regression on UTF-8 file handler."""

import logging
from pathlib import Path

import pytest

from magma_cycling.config.logging_config import setup_logging


@pytest.fixture
def reset_root_logger():
    """Reset root logger handlers after each test."""
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()


def test_rotating_file_handler_writes_utf8_on_windows_locales(tmp_path: Path, reset_root_logger):
    """Regression test for BT-Georges/BT-Max: RotatingFileHandler must write UTF-8.

    Previously the handler was created without explicit `encoding=`, which on
    Windows defaults to cp1252 and corrupts non-ASCII characters (em-dash,
    accented letters) silently. The log file then contains raw cp1252 bytes
    that look like mojibake when read with any UTF-8 reader.
    """
    log_file = tmp_path / "test.log"

    setup_logging(level="INFO", file_path=str(log_file), force=True)

    logger = logging.getLogger("test_utf8")
    logger.info("Workflow coach IA — procédure actée S018")
    logger.info("Kiné midi — données complètes")

    for h in logging.getLogger().handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "Workflow coach IA — procédure actée S018" in content
    assert "Kiné midi — données complètes" in content


def test_rotating_file_handler_replaces_undecodable_chars(tmp_path: Path, reset_root_logger):
    """`errors="replace"` ensures no UnicodeEncodeError crashes the logger
    if a string somehow contains chars unencodable in UTF-8 (extremely rare
    but the safety belt is the contract)."""
    log_file = tmp_path / "test.log"
    setup_logging(level="INFO", file_path=str(log_file), force=True)

    logger = logging.getLogger("test_replace")
    logger.info("emoji ok 🚴 sleep ok 🛌")

    for h in logging.getLogger().handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "emoji ok 🚴" in content
    assert "sleep ok 🛌" in content
