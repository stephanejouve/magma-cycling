"""Non-regression tests: setup_withings.py must never print the raw OAuth URL.

Background
----------
On 2026-05-01, ``print(f"   URL: {auth_url}")`` at line 292 of
``setup_withings.py`` exposed the Withings preprod ``CLIENT_ID`` in the
Bash output of an automated session. Although ``CLIENT_ID`` alone is
semi-public (it appears in any OAuth flow's browser address bar), printing
it in stdout/log persistents was identified as a source-code-level pattern
to harden structurally. The fix routes every print of the URL through
``outillages.oauth.redact_url_secrets`` and writes the full URL to a
``chmod 600`` file (``~/.cache/magma-cycling/oauth_url.txt``) for the rare
case where the user must open it manually.

These tests are static checks on the source file. They will fail if a
future refactor reintroduces a raw ``print(... auth_url ...)`` without the
redaction helper.
"""

from __future__ import annotations

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "magma_cycling" / "scripts" / "setup_withings.py"


def test_imports_redact_url_secrets_from_outillages():
    """The hardened version must import the redaction helper."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "from outillages.oauth import redact_url_secrets" in src, (
        "setup_withings.py must import redact_url_secrets — regression of the "
        "2026-05-01 OAuth URL leak fix."
    )


def test_does_not_print_raw_auth_url_in_url_label():
    """The original line `print(f"   URL: {auth_url}")` is forbidden."""
    src = SCRIPT.read_text(encoding="utf-8")
    forbidden = 'print(f"   URL: {auth_url}")'
    assert forbidden not in src, (
        f"Forbidden pattern still present: {forbidden!r}. "
        "Use redact_url_secrets(auth_url) instead."
    )


def test_does_not_print_raw_auth_url_in_manual_visit_fallback():
    """The original fallback line printing the raw URL is forbidden."""
    src = SCRIPT.read_text(encoding="utf-8")
    forbidden = 'print(f"\\nPlease manually visit:\\n{auth_url}\\n")'
    assert forbidden not in src, (
        f"Forbidden pattern still present: {forbidden!r}. "
        "Use redact_url_secrets(auth_url) or the oauth_url_file pointer."
    )


def test_uses_redact_url_secrets_at_least_once():
    """Positive: redact_url_secrets must actually be called on auth_url."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert (
        "redact_url_secrets(auth_url)" in src
    ), "redact_url_secrets must be applied to auth_url before printing."


def test_full_url_written_to_user_cache_file():
    """Positive: the full URL is persisted to a user-cache file (chmod 600)."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'oauth_url_file = Path.home() / ".cache" / "magma-cycling" / "oauth_url.txt"' in src, (
        "Expected the full URL to be persisted to ~/.cache/magma-cycling/oauth_url.txt "
        "as a fallback for manual browser open."
    )
    assert (
        "oauth_url_file.chmod(0o600)" in src
    ), "Expected oauth_url_file.chmod(0o600) for owner-only readability."


def test_atexit_cleanup_registered():
    """Positive: an atexit handler must clean up the URL file at process exit."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert (
        "atexit.register" in src
    ), "Expected atexit.register(...) to clean up the oauth_url_file at process exit."
