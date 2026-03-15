"""Tests for CLI entry point decorator."""

import pytest

from magma_cycling.utils.cli import cli_main


class TestCliMainSuccess:
    """Tests for successful exit scenarios."""

    def test_success_returns_none_exits_zero(self):
        """Function returning None exits with code 0."""

        @cli_main
        def my_cmd():
            pass

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 0

    def test_success_returns_zero_exits_zero(self):
        """Function returning 0 exits with code 0."""

        @cli_main
        def my_cmd():
            return 0

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 0

    def test_returns_nonzero_int(self):
        """Function returning non-zero int exits with that code."""

        @cli_main
        def my_cmd():
            return 42

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 42


class TestCliMainExceptions:
    """Tests for exception handling."""

    def test_exception_exits_one(self):
        """Unhandled exception exits with code 1."""

        @cli_main
        def my_cmd():
            raise ValueError("boom")

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 1

    def test_keyboard_interrupt_exits_130(self):
        """KeyboardInterrupt exits with code 130."""

        @cli_main
        def my_cmd():
            raise KeyboardInterrupt

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 130

    def test_system_exit_passthrough(self):
        """SystemExit is re-raised as-is."""

        @cli_main
        def my_cmd():
            raise SystemExit(99)

        with pytest.raises(SystemExit) as exc_info:
            my_cmd()
        assert exc_info.value.code == 99


class TestCliMainMetadata:
    """Tests for decorator metadata preservation."""

    def test_wrapped_function_name_preserved(self):
        """functools.wraps preserves __name__."""

        @cli_main
        def my_special_cmd():
            """My docstring."""

        assert my_special_cmd.__name__ == "my_special_cmd"
        assert my_special_cmd.__doc__ == "My docstring."


class TestCliMainArgsForwarding:
    """Tests for argument forwarding."""

    def test_args_forwarded(self):
        """Arguments are forwarded to the wrapped function."""
        received = {}

        @cli_main
        def my_cmd(a, b, key=None):
            received["a"] = a
            received["b"] = b
            received["key"] = key

        with pytest.raises(SystemExit):
            my_cmd(1, 2, key="val")

        assert received == {"a": 1, "b": 2, "key": "val"}
