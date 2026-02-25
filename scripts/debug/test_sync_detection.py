#!/usr/bin/env python3
"""
Test script for bidirectional sync detection.

Tests intervals_sync.py ability to detect content modifications
via description hash comparison.
"""

import json
from datetime import date
from pathlib import Path

from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.planning.calendar import TrainingCalendar, WorkoutType
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync

# Load week planning with descriptions and hashes
week_planning_file = Path(Path.home() / "training-logs/data/week_planning/week_planning_S077.json")
workouts_file = Path.home() / "training-logs/data/week_planning/S077_workouts.txt"

with open(week_planning_file) as f:
    planning_data = json.load(f)

# Load workouts descriptions from file
workouts_text = workouts_file.read_text()
workout_blocks = {}
current_id = None
current_lines = []
inside_workout = False

for line in workouts_text.splitlines():
    if "=== WORKOUT" in line:
        # Extract ID (e.g., S077-02-INT-SweetSpot-V001)
        parts = line.split()
        if len(parts) >= 3:
            current_id = parts[2]
        current_lines = []
        inside_workout = True
    elif "=== FIN WORKOUT" in line:
        if current_id and current_lines:
            # Join and strip the full description
            workout_blocks[current_id] = "\n".join(current_lines).strip()
        current_id = None
        current_lines = []
        inside_workout = False
    elif inside_workout:
        # Keep all lines including blank ones for accurate reconstruction
        current_lines.append(line.rstrip())

# Create TrainingCalendar
profile = AthleteProfile.from_env()
calendar = TrainingCalendar(year=2026, athlete_profile=profile)

# Add sessions with descriptions
workout_type_map = {
    "END": WorkoutType.ENDURANCE,
    "INT": WorkoutType.TEMPO,  # Sweet Spot → TEMPO category
    "PDC": WorkoutType.RECOVERY,  # Technique → RECOVERY category
    "REC": WorkoutType.RECOVERY,
}

for session_data in planning_data["planned_sessions"]:
    session_date = date.fromisoformat(session_data["date"])
    workout_id = session_data["session_id"]

    # Skip rest days (Sunday is configured as rest day)
    if session_date.weekday() == 6:  # Sunday
        continue

    # Add session to calendar
    session = calendar.add_session(
        session_date=session_date,
        workout_type=workout_type_map.get(session_data["type"], WorkoutType.ENDURANCE),
        planned_tss=session_data["tss_planned"],
        duration_min=session_data["duration_min"],
    )

    # Add description and hash as dynamic attributes
    full_workout_id = (
        f"{workout_id}-{session_data['type']}-{session_data['name']}-{session_data['version']}"
    )
    session.description = workout_blocks.get(full_workout_id, session_data.get("description", ""))
    session.description_hash = session_data.get("description_hash")

# Test sync detection
print("=" * 80)
print("BIDIRECTIONAL SYNC TEST - S077 (2026-01-19 to 2026-01-25)")
print("=" * 80)

sync = IntervalsSync()
status = sync.get_sync_status(
    calendar=calendar, start_date=date(2026, 1, 19), end_date=date(2026, 1, 25)
)

print(f"\n{status.summary()}\n")

if status.diff.has_changes():
    print("🔍 DÉTAILS DES CHANGEMENTS:\n")

    if status.diff.removed_remote:
        print(f"🗑️  SUPPRIMÉS PAR COACH ({len(status.diff.removed_remote)}):")
        for workout in status.diff.removed_remote:
            print(f"  • {workout['date']}: {workout['name']}")
        print()

    if status.diff.added_remote:
        print(f"➕ AJOUTÉS PAR COACH ({len(status.diff.added_remote)}):")
        for workout in status.diff.added_remote:
            print(f"  • {workout['date']}: {workout['name']} (ID: {workout['id']})")
        print()

    if status.diff.modified_remote:
        print(f"✏️  MODIFIÉS PAR COACH ({len(status.diff.modified_remote)}):")
        for modification in status.diff.modified_remote:
            print(f"\n  📅 {modification['date']}")
            print(f"  Local:  {modification['local']['name']}")
            print(
                f"  Remote: {modification['remote']['name']} (ID: {modification['remote']['id']})"
            )
            print("\n  📝 Changements détectés:")
            diff_text = modification.get("diff", "N/A")
            for diff_line in diff_text.splitlines():
                print(f"     {diff_line}")
        print()

    if status.diff.moved_remote:
        print(f"🔄 DÉPLACÉS PAR COACH ({len(status.diff.moved_remote)}):")
        for workout in status.diff.moved_remote:
            print(f"  • {workout['name']}")
        print()
else:
    print("✅ Calendrier local et Intervals.icu sont SYNCHRONISÉS")
    print("   Aucune modification externe détectée.")

print("\n" + "=" * 80)
print("✅ Test terminé")
print("=" * 80)
