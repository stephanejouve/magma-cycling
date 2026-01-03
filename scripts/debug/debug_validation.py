#!/usr/bin/env python3
"""Debug is_valid_activity rejection"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.home() / "cyclisme-training-logs"))

from cyclisme_training_logs.sync_intervals import IntervalsAPI  # noqa: E402
from cyclisme_training_logs.workflow_state import WorkflowState  # noqa: E402


def main():
    # Init API
    athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
    api_key = os.getenv("VITE_INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Variables VITE_INTERVALS_* non définies")
        return

    api = IntervalsAPI(athlete_id, api_key)
    state = WorkflowState()

    print("🔍 Test validation activités août 2024\n")

    # Fetch 5 activités août
    activities = api.get_activities(oldest="2024-08-01", newest="2024-08-31")[:5]

    for i, activity in enumerate(activities, 1):
        activity_id = str(activity.get("id", ""))
        print(f"\n{'='*60}")
        print(f"Activité {i}/5: {activity_id}")
        print(f"{'='*60}")

        # Test AVANT enrichissement
        print("\n📊 DONNÉES BASIQUES (get_activities):")
        print(f"   moving_time: {activity.get('moving_time', 'ABSENT')}s")
        print(f"   icu_training_load (TSS): {activity.get('icu_training_load', 'ABSENT')}")
        print(f"   icu_average_watts: {activity.get('icu_average_watts', 'ABSENT')}")
        print(f"   average_watts: {activity.get('average_watts', 'ABSENT')}")

        valid_basic = state.is_valid_activity(activity)
        print(f"\n   ✅ is_valid_activity(basic)? {valid_basic}")

        # Enrichir
        try:
            detailed = api.get_activity(activity_id)

            print("\n📊 DONNÉES ENRICHIES (get_activity):")
            print(f"   moving_time: {detailed.get('moving_time', 'ABSENT')}s")
            print(f"   icu_training_load (TSS): {detailed.get('icu_training_load', 'ABSENT')}")
            print(f"   icu_average_watts: {detailed.get('icu_average_watts', 'ABSENT')}")
            print(f"   average_watts: {detailed.get('average_watts', 'ABSENT')}")

            valid_detailed = state.is_valid_activity(detailed)
            print(f"\n   ✅ is_valid_activity(detailed)? {valid_detailed}")

            # Debug détaillé si rejet
            if not valid_detailed:
                print("\n🔍 DEBUG REJET:")

                moving_time = detailed.get("moving_time", 0)
                print(f"   1. moving_time ({moving_time}s) >= 120s ? {moving_time >= 120}")

                tss = detailed.get("icu_training_load", 0)
                print(f"   2. icu_training_load ({tss}) > 0 ? {tss > 0}")

                watts = detailed.get("icu_average_watts") or detailed.get("average_watts")
                print(f"   3. power ({watts}) > 0 ? {watts is not None and watts > 0}")

        except Exception as e:
            print(f"\n❌ Erreur enrichissement: {e}")

    print("\n" + "=" * 60)
    print("FIN DEBUG")
    print("=" * 60)


if __name__ == "__main__":
    main()
