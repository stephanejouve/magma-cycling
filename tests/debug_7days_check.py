#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cyclisme_training_logs.api.intervals_client import IntervalsClient  # noqa: E402
from cyclisme_training_logs.workflow_state import WorkflowState  # noqa: E402

athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
api_key = os.getenv("VITE_INTERVALS_API_KEY")

api = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
state = WorkflowState()

# 7 JOURS comme le workflow
oldest_date = datetime.now() - timedelta(days=7)
newest_date = datetime.now()

activities = api.get_activities(
    oldest=oldest_date.strftime("%Y-%m-%d"), newest=newest_date.strftime("%Y-%m-%d")
)

unanalyzed = state.get_unanalyzed_activities(activities)

print("📊 Période : 7 derniers jours")
print(f"   API retourne : {len(activities)} activités")
print(f"   Non analysées : {len(unanalyzed)} activités")
print()

for i, act in enumerate(unanalyzed[:10], 1):
    print(f"   {i}. {act.get('name')[:50]} ({act.get('start_date_local')})")
