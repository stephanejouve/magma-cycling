"""CLI entry point decorator — handles exceptions and exit codes."""

import functools
import sys
import traceback


def cli_main(func):
    """Decorator for CLI entry points — handles exceptions and exit codes."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            sys.exit(0 if result is None or result == 0 else result)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            sys.exit(130)
        except Exception:
            traceback.print_exc()
            sys.exit(1)

    return wrapper
