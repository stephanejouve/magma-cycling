"""
Hot reload utility for production environments.

Automatically reloads Python modules that have been modified since last import,
preventing cache issues in long-running daemons or scheduled tasks.

Examples:
    Add at the start of your script::

        from cyclisme_training_logs.utils.hot_reload import hot_reload_if_needed

        if __name__ == "__main__":
            hot_reload_if_needed()
            main()

    Or use as decorator::

        from cyclisme_training_logs.utils.hot_reload import with_hot_reload

        @with_hot_reload
        def main():
            # Your code here
            pass

Author: Claude Code
Created: 2026-02-18
Category: Utility
Priority: P2
Status: Production
"""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def hot_reload_if_needed(
    package_name: str = "cyclisme_training_logs", verbose: bool = False
) -> list[str]:
    """
    Reload all modules in package if source files were modified.

    Compares file modification times with module load times to detect
    changes. Reloads modified modules using importlib.reload().

    Args:
        package_name: Python package to check for changes
        verbose: Print detailed reload information

    Returns:
        List of reloaded module names

    Examples:
        >>> reloaded = hot_reload_if_needed()
        >>> if reloaded:
        ...     print(f"Reloaded: {', '.join(reloaded)}")

    Notes:
        - Safe for production (no-op if no changes detected)
        - Cross-platform (works on Linux, macOS, Windows)
        - Only reloads modules already imported
    """
    reloaded_modules = []

    # Find all loaded modules from our package
    our_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith(package_name) and hasattr(module, "__file__")
    }

    if not our_modules:
        if verbose:
            logger.debug(f"No modules from {package_name} loaded yet")
        return []

    # Check each module for file changes
    for module_name, module in our_modules.items():
        try:
            module_file = Path(module.__file__)

            if not module_file.exists():
                continue

            # Get file modification time
            file_mtime = module_file.stat().st_mtime

            # Get module load time (stored when module was imported)
            # If not available, assume it needs reload
            module_mtime = getattr(module, "__mtime__", 0)

            if file_mtime > module_mtime:
                # File was modified after module was loaded
                if verbose:
                    logger.info(f"🔄 Reloading modified module: {module_name}")

                # Reload the module
                importlib.reload(module)

                # Store new modification time
                module.__mtime__ = file_mtime

                reloaded_modules.append(module_name)

        except (AttributeError, OSError) as e:
            if verbose:
                logger.debug(f"Skipping {module_name}: {e}")
            continue

    if reloaded_modules and not verbose:
        # Always log when modules are reloaded (important for debugging)
        logger.info(f"♻️  Hot-reloaded {len(reloaded_modules)} module(s)")

    return reloaded_modules


def with_hot_reload(func: Any) -> Any:
    """
    Decorator to hot-reload modules before function execution.

    Args:
        func: Function to wrap with hot-reload

    Returns:
        Wrapped function that hot-reloads before execution

    Examples:
        >>> @with_hot_reload
        ... def main():
        ...     print("Running with fresh code!")
    """

    def wrapper(*args, **kwargs):
        hot_reload_if_needed()
        return func(*args, **kwargs)

    return wrapper


def mark_modules_loaded(package_name: str = "cyclisme_training_logs") -> None:
    """
    Mark all currently loaded modules with their file modification time.

    Call this at startup to establish baseline for future hot-reload checks.

    Args:
        package_name: Python package to mark

    Examples:
        >>> mark_modules_loaded()
        >>> # Later calls to hot_reload_if_needed() will detect changes
    """
    our_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith(package_name) and hasattr(module, "__file__")
    }

    for module_name, module in our_modules.items():
        try:
            module_file = Path(module.__file__)
            if module_file.exists():
                module.__mtime__ = module_file.stat().st_mtime
        except (AttributeError, OSError):
            continue
