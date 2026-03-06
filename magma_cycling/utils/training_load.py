"""Training load metrics: ACWR, Monotony, Strain.

Computes acute/chronic workload ratio and training monotony/strain
from 28 days of activity data (Intervals.icu API).

References:
    - ACWR: Gabbett (2016) — 0.8-1.3 optimal, >1.5 danger
    - Monotony: Foster (1998) — >2.0 = elevated illness risk
    - Strain: Foster (1998) — >3500 associated with overtraining
"""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, stdev


def compute_training_load(activities_28d: list[dict]) -> dict:
    """Compute ACWR, Monotony, Strain from 28 days of activities.

    Args:
        activities_28d: List of activity dicts with 'start_date_local' and
            'icu_training_load' (TSS) from Intervals.icu API.

    Returns:
        Dict with acwr, monotony, strain, acute_load, chronic_load.
        Empty dict on failure.
    """
    if not activities_28d:
        return {}

    # Aggregate TSS per day over 28 days
    today = datetime.now().date()
    daily_tss: dict[str, float] = {}
    for i in range(28):
        d = (today - timedelta(days=27 - i)).isoformat()
        daily_tss[d] = 0.0

    for act in activities_28d:
        tss = act.get("icu_training_load")
        if tss is None:
            continue
        date_str = act.get("start_date_local", "")[:10]
        if date_str in daily_tss:
            daily_tss[date_str] += float(tss)

    # Sorted daily values (oldest first)
    sorted_days = sorted(daily_tss.keys())
    all_values = [daily_tss[d] for d in sorted_days]

    if len(all_values) < 7:
        return {}

    # Last 7 days = acute, all 28 = chronic
    acute_values = all_values[-7:]
    chronic_values = all_values

    acute_load = sum(acute_values) / 7
    chronic_load = sum(chronic_values) / 28

    # ACWR
    acwr = round(acute_load / chronic_load, 2) if chronic_load > 0 else 0.0

    # Monotony = mean(7d) / stdev(7d)
    acute_mean = mean(acute_values)
    acute_stdev = stdev(acute_values) if len(acute_values) > 1 else 0.0
    monotony = round(acute_mean / acute_stdev, 2) if acute_stdev > 0 else 0.0

    # Strain = weekly_load * monotony
    weekly_load = sum(acute_values)
    strain = round(weekly_load * monotony, 0)

    return {
        "acwr": acwr,
        "monotony": monotony,
        "strain": strain,
        "acute_load": round(acute_load, 1),
        "chronic_load": round(chronic_load, 1),
    }
