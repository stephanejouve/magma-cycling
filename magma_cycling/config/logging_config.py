"""Logging configuration for magma-cycling.

Provides centralized logging setup with environment variable control.

Usage:
    from magma_cycling.config.logging_config import setup_logging, get_logger

    # Setup logging once at application start
    setup_logging()

    # Get logger in any module
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

Environment Variables:
    LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
    LOG_FORMAT: simple, detailed, json (default: detailed)

Examples:
    # Debug mode
    LOG_LEVEL=DEBUG poetry run backfill-intelligence ...

    # Production (quiet)
    LOG_LEVEL=WARNING poetry run workflow-coach

    # JSON logs (for log aggregation)
    LOG_FORMAT=json LOG_LEVEL=INFO poetry run weekly-analysis
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log level mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Log format templates
LOG_FORMATS = {
    "simple": "%(levelname)s: %(message)s",
    "detailed": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "json": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
}


def setup_logging(
    level: str | None = None,
    format_name: str | None = None,
    force: bool = False,
    file_path: str | None = None,
    max_bytes: int = 5_242_880,
    backup_count: int = 3,
) -> None:
    """Set up logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               If None, reads from LOG_LEVEL env var (default: INFO)
        format_name: Log format name (simple, detailed, json).
                     If None, reads from LOG_FORMAT env var (default: detailed)
        force: If True, reconfigure even if already setup
        file_path: Path for a RotatingFileHandler. If None, no file logging.
        max_bytes: Max file size before rotation (default: 5 MB).
        backup_count: Number of backup files to keep (default: 3).

    Examples:
        >>> setup_logging()  # Use env vars
        >>> setup_logging(level="DEBUG")  # Override level
        >>> setup_logging(file_path="/tmp/app.log")  # Add file logging
    """
    # Get configuration

    log_level_name = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format_name = format_name or os.getenv("LOG_FORMAT", "detailed").lower()

    # Validate level
    if log_level_name not in LOG_LEVELS:
        print(f"Invalid LOG_LEVEL '{log_level_name}', using INFO", file=sys.stderr)
        log_level_name = "INFO"

    # Validate format
    if log_format_name not in LOG_FORMATS:
        print(f"Invalid LOG_FORMAT '{log_format_name}', using detailed", file=sys.stderr)
        log_format_name = "detailed"

    log_level = LOG_LEVELS[log_level_name]
    log_format = LOG_FORMATS[log_format_name]

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=force,
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Add file handler if requested
    if file_path:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(file_path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
        logging.getLogger().addHandler(file_handler)

    # Log configuration (only at DEBUG level)
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured: level={log_level_name}, format={log_format_name}")


def get_logger(name: str) -> logging.Logger:
    """Get logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting analysis")
        >>> logger.debug("Detailed debug info")
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """Change log level at runtime.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR)

    Examples:
        >>> set_log_level("DEBUG")  # Enable debug logs
        >>> set_log_level("WARNING")  # Quiet mode
    """
    level_name = level.upper()

    if level_name not in LOG_LEVELS:
        raise ValueError(f"Invalid log level: {level}. Must be one of {list(LOG_LEVELS.keys())}")

    logging.getLogger().setLevel(LOG_LEVELS[level_name])
    logger = get_logger(__name__)
    logger.debug(f"Log level changed to {level_name}")


_MCP_LOG_DEFAULT = "~/.local/share/magma-cycling/mcp-server.log"


def setup_mcp_logging() -> str | None:
    """Configure logging for the MCP server with file output.

    Reads configuration from environment variables:
        MCP_LOG_FILE: Log file path (empty string to disable, default: ~/.local/share/...)
        MCP_LOG_LEVEL: Log level (fallback: LOG_LEVEL, default: INFO)
        MCP_LOG_MAX_BYTES: Max file size before rotation (default: 5 MB)
        MCP_LOG_BACKUP_COUNT: Number of backup files (default: 3)

    Returns:
        Path to the log file, or None if file logging is disabled.
    """
    log_file = os.getenv("MCP_LOG_FILE", _MCP_LOG_DEFAULT)
    if log_file == "":
        setup_logging(force=True)
        return None

    log_file = os.path.expanduser(log_file)
    log_level = os.getenv("MCP_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
    max_bytes = int(os.getenv("MCP_LOG_MAX_BYTES", "5242880"))
    backup_count = int(os.getenv("MCP_LOG_BACKUP_COUNT", "3"))

    setup_logging(
        level=log_level,
        force=True,
        file_path=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    return log_file


# Auto-setup logging when module is imported (can be overridden)
_auto_setup = os.getenv("DISABLE_AUTO_LOGGING_SETUP", "false").lower() not in ("true", "1", "yes")
if _auto_setup:
    setup_logging()
