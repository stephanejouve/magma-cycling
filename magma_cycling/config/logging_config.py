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
    level: str | None = None, format_name: str | None = None, force: bool = False
) -> None:
    """Set up logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               If None, reads from LOG_LEVEL env var (default: INFO)
        format_name: Log format name (simple, detailed, json).
                     If None, reads from LOG_FORMAT env var (default: detailed)
        force: If True, reconfigure even if already setup

    Examples:
        >>> setup_logging()  # Use env vars
        >>> setup_logging(level="DEBUG")  # Override level
        >>> setup_logging(level="DEBUG", format_name="simple")
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


# Auto-setup logging when module is imported (can be overridden)
_auto_setup = os.getenv("DISABLE_AUTO_LOGGING_SETUP", "false").lower() not in ("true", "1", "yes")
if _auto_setup:
    setup_logging()
