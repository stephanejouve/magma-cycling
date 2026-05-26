"""Per-run tracker for Mistral AI calls (PR3 iso-config AC3).

Appends one log line per call to ``data/intelligence/mistral_usage_YYYY-MM.log``
and posts a Talk alert if the per-run counter exceeds the runaway threshold.
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CALLS_PER_RUN = 50
ALERT_ROOM_TOKEN = "b276xzrb"  # Equipe Magma


class MistralUsageLogger:
    """Append-only logger for Mistral API calls, with runaway alerting."""

    def __init__(
        self,
        workflow_id: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialise the logger and create the per-month log directory."""
        self.workflow_id = workflow_id or os.environ.get("MAGMA_WORKFLOW_ID", "unknown")
        self.data_dir = data_dir or Path(os.environ.get("MAGMA_DATA_DIR", "data"))
        self.log_dir = self.data_dir / "intelligence"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.calls_this_run = 0
        self.alerted = False

    @property
    def log_file(self) -> Path:
        """Return the per-month append-only log file path."""
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.log_dir / f"mistral_usage_{month}.log"

    def log_call(self, *, n_tokens: int | None = None, status: str = "ok") -> None:
        """Append one call to the monthly log file, then check threshold."""
        ts = datetime.now(timezone.utc).isoformat()
        n_tokens_str = str(n_tokens) if n_tokens is not None else "?"
        line = f"{ts}\t{self.workflow_id}\t{n_tokens_str}\t{status}\n"
        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            logger.warning("mistral_usage log write failed: %s", e)
            return

        self.calls_this_run += 1
        if self.calls_this_run > MAX_CALLS_PER_RUN and not self.alerted:
            self._alert_runaway()
            self.alerted = True

    def _alert_runaway(self) -> None:
        """Best-effort Talk alert when the per-run counter exceeds threshold."""
        msg = (
            f"⚠️ Mistral usage runaway : workflow `{self.workflow_id}` "
            f"a dépassé {MAX_CALLS_PER_RUN} appels sur 1 run. "
            f"Voir log : {self.log_file}"
        )
        try:
            subprocess.run(
                [
                    "poetry",
                    "run",
                    "nc-talk",
                    "send",
                    msg,
                    "--room",
                    ALERT_ROOM_TOKEN,
                ],
                cwd=str(Path.home() / "Projects" / "outillages"),
                check=False,
                capture_output=True,
                timeout=15,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("mistral_usage Talk alert failed: %s", e)


_logger: MistralUsageLogger | None = None


def get_logger() -> MistralUsageLogger:
    """Return the process-wide logger, initialising lazily on first call."""
    global _logger
    if _logger is None:
        _logger = MistralUsageLogger()
    return _logger


def reset_logger(
    workflow_id: str | None = None, data_dir: Path | None = None
) -> MistralUsageLogger:
    """Replace the process-wide logger (counter reset)."""
    global _logger
    _logger = MistralUsageLogger(workflow_id=workflow_id, data_dir=data_dir)
    return _logger
