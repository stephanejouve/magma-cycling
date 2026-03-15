"""Evaluation logging mixin for PID evaluation."""

import json
from datetime import date, datetime
from typing import Any


class LoggingMixin:
    """Log evaluations and save intelligence state."""

    def log_evaluation(
        self,
        start_date: date,
        end_date: date,
        metrics: dict[str, Any],
        pid_result: dict[str, Any] | None = None,
    ) -> None:
        """Log evaluation to pid_evaluation.jsonl.

        Args:
            start_date: Cycle start
            end_date: Cycle end
            metrics: Cycle metrics
            pid_result: PID correction result (None if not cycle completion)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics": metrics,
            "pid_correction": pid_result,
            "learnings_count": len(self.intelligence.learnings),
            "patterns_count": len(self.intelligence.patterns),
        }

        if not self.dry_run:
            self.evaluation_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.evaluation_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            print(f"\n📝 Evaluation logged to {self.evaluation_log}")
        else:
            print("\n🔍 DRY-RUN: Skipping log save")

    def save_intelligence(self) -> None:
        """Save intelligence to file."""
        if not self.dry_run:
            self.intelligence_file.parent.mkdir(parents=True, exist_ok=True)
            self.intelligence.save_to_file(self.intelligence_file)
            print(f"💾 Intelligence saved to {self.intelligence_file}")
        else:
            print("🔍 DRY-RUN: Skipping intelligence save")
