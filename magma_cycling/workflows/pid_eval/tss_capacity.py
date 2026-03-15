"""TSS capacity calculation mixin for PID evaluation."""

from datetime import date


class TSSCapacityMixin:
    """Calculate TSS completion rate from Intervals.icu API."""

    def calculate_tss_completion(self, start_date: date, end_date: date) -> float:
        """Calculate TSS completion rate from Intervals.icu.

        Compares planned TSS (events) vs realized TSS (activities).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            TSS completion rate (0.0 - 1.0)
        """
        print(f"\n📥 Calculating TSS completion ({start_date} → {end_date})")

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        try:
            # Get planned workouts
            events = self.client.get_events(oldest=start_str, newest=end_str)
            planned_workouts = [
                e
                for e in events
                if e.get("category") == "WORKOUT" and not e.get("name", "").startswith("[")
            ]

            # Get completed activities
            activities = self.client.get_activities(oldest=start_str, newest=end_str)

            # Calculate TSS
            planned_tss = sum(e.get("icu_training_load", 0) for e in planned_workouts)
            realized_tss = sum(a.get("icu_training_load", 0) for a in activities)

            completion_rate = realized_tss / planned_tss if planned_tss > 0 else 1.0

            print(f"   Planned TSS: {planned_tss:.0f}")
            print(f"   Realized TSS: {realized_tss:.0f}")
            print(f"   Completion: {completion_rate * 100:.1f}%")

            return completion_rate

        except Exception as e:
            print(f"   ⚠️  Error calculating TSS: {e}")
            return 1.0
