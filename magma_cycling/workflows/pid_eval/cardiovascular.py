"""Cardiovascular coupling extraction mixin for PID evaluation."""

import re
from datetime import date


class CardiovascularQualityMixin:
    """Extract cardiovascular coupling from weekly workout history files."""

    def extract_cardiovascular_coupling(self, start_date: date, end_date: date) -> list[float]:
        """Extract cardiovascular coupling (decouplage) from weekly report files.

        Scans logs/weekly_reports/S0XX/workout_history_S0XX.md files for decouplage values.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of decouplage percentages (as decimals, e.g., 0.062 for 6.2%)
        """
        if not self.workouts_history.exists():
            print(f"⚠️  Weekly reports directory not found at {self.workouts_history}")
            return []

        print(f"\n📥 Extracting cardiovascular coupling ({start_date} → {end_date})")

        coupling_values = []

        # Regex patterns for decouplage extraction
        patterns = [
            r"découplage\s+cardiovasculaire\s+\w+\s*\((\d+\.?\d*)\s*%\)",
            r"découplage\s+(\d+\.?\d*)\s*%",
        ]

        # Scan all weekly workout history files
        workout_files = sorted(self.workouts_history.glob("*/workout_history_*.md"))
        print(f"   📁 Found {len(workout_files)} weekly files")

        for workout_file in workout_files:
            with open(workout_file, encoding="utf-8") as f:
                content = f.read()

            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    coupling_pct = float(match.group(1))
                    coupling_values.append(abs(coupling_pct) / 100.0)

        print(f"   ✅ {len(coupling_values)} cardiovascular coupling values extracted")
        return coupling_values
