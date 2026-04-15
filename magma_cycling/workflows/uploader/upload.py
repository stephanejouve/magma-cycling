"""Upload mixin for WorkoutUploader."""

import re
from datetime import datetime, timedelta

from magma_cycling.utils.event_sync import (
    calculate_description_hash,
    compute_start_time,
    evaluate_sync,
)


def _find_matching_event(
    existing_events: list[dict], workout_name: str, suffix: str
) -> dict | None:
    """Find an existing WORKOUT event matching the given workout.

    For double sessions (suffix a/b), match by exact name.
    For single sessions, match by session_id prefix (SXXX-NN).

    Args:
        existing_events: List of remote events for the date.
        workout_name: Local workout name.
        suffix: Session suffix ("a", "b", or "").

    Returns:
        Matching remote event dict, or None.
    """
    session_id = "-".join(workout_name.split("-")[:2])

    for event in existing_events:
        if event.get("category") != "WORKOUT":
            continue
        event_name = event.get("name", "")
        if suffix:
            if event_name == workout_name:
                return event
        else:
            event_session_id = "-".join(event_name.split("-")[:2])
            if event_session_id == session_id:
                return event

    return None


# Regex pour détecter une ligne d'instruction d'intervalle Intervals.icu
# Pattern : - {durée}{unité} {intensité}% {cadence}rpm  (avec variantes ramp, plages)
_INTERVAL_LINE_RE = re.compile(r"^-\s+\d+[msh]\s+")  # tiret + durée (10m, 30s, 1h)


def sanitize_description(description: str) -> str:
    """Remplace les tirets non-intervalle par des bullets dans la description.

    Intervals.icu interprète toute ligne commençant par '-' comme un bloc
    d'intervalle structuré. Les lignes textuelles (Points clés, notes) qui
    utilisent des tirets comme puces de liste génèrent des barres parasites
    sur le graphique de puissance.
    """
    lines = description.split("\n")
    result = []
    in_interval_section = False

    for line in lines:
        stripped = line.strip()

        # Détecter les headers de section d'intervalles
        if re.match(r"(?i)^(warmup|main set|cooldown)", stripped):
            in_interval_section = True
            result.append(line)
            continue

        # Ligne vide ou nouveau header textuel → fin de section intervalle
        if not stripped or (
            stripped
            and not stripped.startswith("-")
            and not _INTERVAL_LINE_RE.match(stripped)
            and not in_interval_section
        ):
            if stripped and not re.match(r"(?i)^(warmup|main set|cooldown)", stripped):
                in_interval_section = False

        # Ligne avec tiret
        if stripped.startswith("- "):
            if in_interval_section and _INTERVAL_LINE_RE.match(stripped):
                # Vraie instruction d'intervalle — garder le tiret
                result.append(line)
            else:
                # Texte non-intervalle — remplacer par bullet
                result.append(line.replace("- ", "• ", 1))
                in_interval_section = False
        else:
            result.append(line)

    return "\n".join(result)


class UploadMixin:
    """Upload vers Intervals.icu."""

    def upload_workout(self, workout: dict) -> bool:
        """Upload un workout sur Intervals.icu with duplicate detection."""
        try:
            # Build session_id for compute_start_time
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            workout_name = workout["name"]
            session_id = "-".join(workout_name.split("-")[:2])
            suffix = workout.get("suffix", "")
            if suffix:
                session_id_full = f"{session_id}{suffix}"
            else:
                session_id_full = session_id

            start_time = compute_start_time(workout_date, session_id_full)

            if self.api is None:
                print("  ❌ Erreur : API non initialisée")
                return False

            # Check for existing workout on this date (duplicate detection)
            existing_events = self.api.get_events(oldest=workout["date"], newest=workout["date"])
            existing_workout = _find_matching_event(existing_events, workout_name, suffix)

            event_data = {
                "category": "WORKOUT",
                "type": "VirtualRide",
                "name": workout["name"],
                "description": sanitize_description(workout["description"]),
                "start_date_local": f"{workout['date']}T{start_time}",
            }

            decision = evaluate_sync(event_data, existing_workout)
            new_hash = calculate_description_hash(workout["description"])

            if decision.action == "create":
                response = self.api.create_event(event_data)
                if response:
                    workout["description_hash"] = new_hash
                    workout["intervals_id"] = response.get("id")
                    print(f"  ✅ Créé : {workout['name']} ({workout['date']})")
                    return True
                else:
                    print(f"  ❌ Échec création : {workout['name']}")
                    return False

            elif decision.action == "skip":
                if "protected" in decision.reason:
                    activity_id = existing_workout.get("paired_activity_id")
                    print(
                        f"  🔒 Protégé (réalisé) : {workout['name']} ({workout['date']}) [Activity: {activity_id}]"
                    )
                    workout["description_hash"] = calculate_description_hash(
                        existing_workout.get("description", "")
                    )
                else:
                    print(f"  ⏭️  Ignoré (identique) : {workout['name']} ({workout['date']})")
                    workout["description_hash"] = new_hash
                workout["intervals_id"] = decision.existing_event_id
                return True

            else:  # update
                response = self.api.update_event(decision.existing_event_id, event_data)
                if response:
                    workout["description_hash"] = new_hash
                    workout["intervals_id"] = response.get("id")
                    print(f"  🔄 Mis à jour : {workout['name']} ({workout['date']})")
                    return True
                else:
                    print(f"  ❌ Échec mise à jour : {workout['name']}")
                    return False

        except Exception as e:
            print(f"  ❌ Erreur upload {workout['name']} : {e}")
            return False

    def upload_all(self, workouts: list[dict], dry_run: bool = False) -> dict:
        """Upload tous les workouts."""
        print("\n" + "=" * 70)

        print("📤 UPLOAD WORKOUTS VERS INTERVALS.ICU")
        print(f"Semaine : {self.week_number}")
        print(
            f"Période : {self.start_date.strftime('%d/%m/%Y')} → {(self.start_date + timedelta(days=6)).strftime('%d/%m/%Y')}"
        )
        print(f"Mode : {'DRY RUN (simulation)' if dry_run else 'RÉEL'}")
        print("=" * 70)

        stats = {"success": 0, "failed": 0}

        for workout in workouts:
            print(f"\n📅 Jour {workout['day']:02d} - {workout['date']}")
            print(f"   {workout['filename']}")

            # Handle rest days (REPOS) - create REST event instead of skipping
            if "REPOS" in workout["filename"].upper():
                if dry_run:
                    print("  🔍 DRY RUN - Jour de repos (REST event)")
                    stats["success"] += 1
                else:
                    try:
                        # Create REST event
                        event_data = {
                            "category": "NOTE",
                            "name": "Repos",
                            "description": workout.get("description", "Jour de repos complet"),
                            "start_date_local": f"{workout['date']}T06:00:00",
                        }

                        if self.api is None:
                            print("  ❌ Erreur : API non initialisée")
                            stats["failed"] += 1
                        else:
                            response = self.api.create_event(event_data)
                            if response:
                                print(f"  ✅ Jour de repos créé : {workout['date']}")
                                stats["success"] += 1
                            else:
                                print(f"  ❌ Échec création repos : {workout['date']}")
                                stats["failed"] += 1

                    except Exception as e:
                        print(f"  ❌ Erreur création repos : {e}")
                        stats["failed"] += 1
                continue

            if dry_run:
                print("  🔍 DRY RUN - Upload simulé")
                stats["success"] += 1
            else:
                if self.upload_workout(workout):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ")
        print("=" * 70)
        print(f"✅ Succès   : {stats['success']}")
        print(f"❌ Échecs   : {stats['failed']}")
        print(f"📝 Total    : {len(workouts)}")
        print("=" * 70)

        # Add total and errors for end_of_week.py compatibility
        stats["total"] = len(workouts)
        stats["errors"] = []
        return stats
