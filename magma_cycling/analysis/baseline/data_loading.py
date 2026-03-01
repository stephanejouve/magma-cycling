"""Data loading methods for BaselineAnalyzer."""

import json
import re
from datetime import datetime


class DataLoadingMixin:
    """Chargement données (fichiers + API)."""

    def load_adherence_data(self) -> None:
        """Load adherence data from workout_adherence.jsonl."""
        print("📥 Loading adherence data...")

        if not self.adherence_file.exists():
            print(f"   ⚠️  File not found: {self.adherence_file}")
            return

        seen_dates = {}
        with open(self.adherence_file, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()

                if self.start_date <= record_date <= self.end_date:
                    # Deduplicate: keep only most recent record per date
                    date_key = record["date"]
                    if date_key not in seen_dates:
                        seen_dates[date_key] = record
                    else:
                        # Keep record with most recent timestamp
                        existing_ts = seen_dates[date_key].get("timestamp", "")
                        current_ts = record.get("timestamp", "")
                        if current_ts > existing_ts:
                            seen_dates[date_key] = record

        self.adherence_data = list(seen_dates.values())
        self.adherence_data.sort(key=lambda x: x["date"])
        print(f"   ✅ Loaded {len(self.adherence_data)} records")

    def load_intervals_data(self) -> None:
        """Load data from Intervals.icu API."""
        print("\n📥 Loading Intervals.icu data...")

        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()

        # Wellness (TSB, CTL, ATL)
        try:
            self.wellness_data = self.client.get_wellness(start_str, end_str)
            print(f"   ✅ Wellness: {len(self.wellness_data)} days")
        except Exception as e:
            print(f"   ⚠️  Wellness error: {e}")

        # Activities
        try:
            self.activities_data = self.client.get_activities(start_str, end_str)
            print(f"   ✅ Activities: {len(self.activities_data)} records")
        except Exception as e:
            print(f"   ⚠️  Activities error: {e}")

        # Events (planned workouts)
        try:
            self.events_data = self.client.get_events(start_str, end_str)
            print(f"   ✅ Events: {len(self.events_data)} planned workouts")
        except Exception as e:
            print(f"   ⚠️  Events error: {e}")

    def parse_skipped_replaced_sessions(self) -> None:
        """Parse NOTE events for skipped/replaced/cancelled sessions.

        Intervals.icu creates NOTE events with special tags when sessions are
        cancelled/skipped/replaced via update-session script:
        - [SAUTÉE] = Skipped session
        - [REMPLACÉE] = Replaced session
        - [ANNULÉE] = Cancelled session
        """
        print("\n📥 Parsing skipped/replaced sessions...")

        if not self.events_data:
            print("   ⚠️  No events data loaded")
            return

        # Find NOTE events with status tags
        for event in self.events_data:
            if event.get("category") != "NOTE":
                continue

            name = event.get("name", "")
            description = event.get("description", "")
            date = event.get("start_date_local", "").split("T")[0]

            # Extract session info
            session_data = {
                "date": date,
                "name": name,
                "description": description,
                "reason": self._extract_reason(description),
            }

            # Categorize by tag
            if "[SAUTÉE]" in name:
                self.skipped_sessions.append(session_data)
            elif "[REMPLACÉE]" in name:
                self.replaced_sessions.append(session_data)
            elif "[ANNULÉE]" in name:
                self.cancelled_sessions.append(session_data)

        total_not_completed = (
            len(self.skipped_sessions) + len(self.replaced_sessions) + len(self.cancelled_sessions)
        )

        print(f"   ✅ Skipped: {len(self.skipped_sessions)}")
        print(f"   ✅ Replaced: {len(self.replaced_sessions)}")
        print(f"   ✅ Cancelled: {len(self.cancelled_sessions)}")
        print(f"   ✅ Total not-completed: {total_not_completed}")

    def _extract_reason(self, description: str) -> str:
        """Extract reason from NOTE description.

        Args:
            description: NOTE description text

        Returns:
            Reason string or "Non spécifiée"
        """
        if not description:
            return "Non spécifiée"

        # Look for "Raison: ..." pattern
        lines = description.split("\n")
        for line in lines:
            if line.startswith("Raison:"):
                return line.replace("Raison:", "").strip()

        return "Non spécifiée"

    def load_cardiovascular_coupling(self) -> None:
        """Extract cardiovascular coupling from workout_history files."""
        print("\n📥 Extracting cardiovascular coupling...")

        if not self.workout_history_dir.exists():
            print(f"   ⚠️  Directory not found: {self.workout_history_dir}")
            return

        patterns = [
            r"découplage\s+cardiovasculaire\s+\w+\s*\((\d+\.?\d*)\s*%\)",
            r"découplage\s+(\d+\.?\d*)\s*%",
        ]

        workout_files = sorted(self.workout_history_dir.glob("*/workout_history_*.md"))
        print(f"   📁 Found {len(workout_files)} weekly files")

        for workout_file in workout_files:
            with open(workout_file, encoding="utf-8") as f:
                content = f.read()

            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    coupling_pct = float(match.group(1))
                    self.cv_coupling_values.append(abs(coupling_pct) / 100.0)

        print(f"   ✅ Extracted {len(self.cv_coupling_values)} values")
