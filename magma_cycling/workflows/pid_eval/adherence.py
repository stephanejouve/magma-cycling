"""Adherence data loading mixin for PID evaluation."""

import json
from datetime import date, datetime
from typing import Any


class AdherenceMixin:
    """Load workout adherence records from JSONL file."""

    def load_adherence_data(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Load adherence data for date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of adherence records
        """
        if not self.adherence_file.exists():
            print(f"⚠️  No adherence data at {self.adherence_file}")
            return []

        print(f"\n📥 Loading adherence data ({start_date} → {end_date})")

        records = []
        with open(self.adherence_file, encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()

                    if start_date <= record_date <= end_date:
                        records.append(record)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        print(f"   ✅ {len(records)} records loaded")
        return records
