"""Cycle metrics aggregation mixin for PID evaluation."""

from datetime import date
from typing import Any


class CycleMetricsAggregationMixin:
    """Orchestrate metrics calculation from all data sources."""

    def calculate_cycle_metrics(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Calculate all metrics needed for PID evaluation.

        Args:
            start_date: Cycle start
            end_date: Cycle end

        Returns:
            Dict with adherence_rate, avg_cardiovascular_coupling,
            tss_completion_rate, days_with_data, total_workouts
        """
        print(f"\n{'=' * 60}")
        print("📊 Calculating Cycle Metrics")
        print(f"{'=' * 60}")
        print(f"Period: {start_date} → {end_date}")

        # 1. Adherence (discipline)
        adherence_records = self.load_adherence_data(start_date, end_date)
        total_planned = sum(r["planned_workouts"] for r in adherence_records)
        total_completed = sum(r["completed_activities"] for r in adherence_records)
        adherence_rate = total_completed / total_planned if total_planned > 0 else 1.0

        # 2. Cardiovascular coupling (quality)
        coupling_values = self.extract_cardiovascular_coupling(start_date, end_date)
        avg_coupling = sum(coupling_values) / len(coupling_values) if coupling_values else 0.05

        # 3. TSS completion (capacity)
        tss_completion = self.calculate_tss_completion(start_date, end_date)

        metrics = {
            "adherence_rate": adherence_rate,
            "avg_cardiovascular_coupling": avg_coupling,
            "tss_completion_rate": tss_completion,
            "days_with_data": len(adherence_records),
            "total_workouts": total_completed,
        }

        print("\n📊 Metrics Summary:")
        print(f"   Adherence Rate: {adherence_rate * 100:.1f}% (discipline)")
        print(f"   Avg Cardiovascular Coupling: {avg_coupling * 100:.1f}% (quality)")
        print(f"   TSS Completion: {tss_completion * 100:.1f}% (capacity)")
        print(f"   Workouts: {total_completed} completed")
        print(f"   Days: {len(adherence_records)} with data")

        return metrics
