"""Upload mixin for WorkoutUploader."""

import hashlib
from datetime import datetime, timedelta


def _calculate_description_hash(description: str) -> str:
    """Calculate SHA256 hash of workout description for change detection."""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:16]


class UploadMixin:
    """Upload vers Intervals.icu."""

    def upload_workout(self, workout: dict) -> bool:
        """Upload un workout sur Intervals.icu with duplicate detection."""
        try:
            # Déterminer l'heure de début selon le jour de la semaine et le suffixe
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            day_of_week = workout_date.weekday()  # 0=Lundi, 5=Samedi, 6=Dimanche
            suffix = workout.get("suffix", "")

            # Gestion double séance (a/b)
            if suffix == "a":
                start_time = "09:00:00"  # Matin
            elif suffix == "b":
                start_time = "15:00:00"  # Après-midi
            else:
                # Samedi (5) → 09:00, autres jours → 17:00
                start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

            if self.api is None:
                print("  ❌ Erreur : API non initialisée")
                return False

            # Check for existing workout on this date (duplicate detection)
            existing_events = self.api.get_events(oldest=workout["date"], newest=workout["date"])

            # Look for existing WORKOUT on same date
            # Pour doubles séances (a/b), matcher le nom exact
            # Pour séances simples, matcher le préfixe semaine+jour (ex: S081-05)
            workout_name = workout["name"]
            session_id = "-".join(workout_name.split("-")[:2])  # Ex: S081-06a → S081-06a

            existing_workout = None
            for event in existing_events:
                if event.get("category") == "WORKOUT":
                    event_name = event.get("name", "")
                    # Matcher le nom exact pour les doubles séances
                    if suffix:
                        if event_name == workout_name:
                            existing_workout = event
                            break
                    else:
                        # Pour séances simples, matcher le session_id (SXXX-NN)
                        event_session_id = "-".join(event_name.split("-")[:2])
                        if event_session_id == session_id:
                            existing_workout = event
                            break

            event_data = {
                "category": "WORKOUT",
                "type": "VirtualRide",
                "name": workout["name"],
                "description": workout["description"],
                "start_date_local": f"{workout['date']}T{start_time}",
            }

            # Calculate hash for comparison
            new_hash = _calculate_description_hash(workout["description"])

            if existing_workout:
                # PROTECTION: Ne jamais écraser un workout déjà réalisé
                if existing_workout.get("paired_activity_id"):
                    activity_id = existing_workout.get("paired_activity_id")
                    print(
                        f"  🔒 Protégé (réalisé) : {workout['name']} ({workout['date']}) [Activity: {activity_id}]"
                    )
                    workout["description_hash"] = _calculate_description_hash(
                        existing_workout.get("description", "")
                    )
                    workout["intervals_id"] = existing_workout.get("id")
                    return True

                existing_hash = _calculate_description_hash(existing_workout.get("description", ""))

                if existing_hash == new_hash:
                    # Identical content - skip
                    print(f"  ⏭️  Ignoré (identique) : {workout['name']} ({workout['date']})")
                    workout["description_hash"] = new_hash
                    workout["intervals_id"] = existing_workout.get("id")
                    return True
                else:
                    # Different content - update
                    response = self.api.update_event(existing_workout.get("id"), event_data)
                    if response:
                        workout["description_hash"] = new_hash
                        workout["intervals_id"] = response.get("id")
                        print(f"  🔄 Mis à jour : {workout['name']} ({workout['date']})")
                        return True
                    else:
                        print(f"  ❌ Échec mise à jour : {workout['name']}")
                        return False
            else:
                # No existing workout - create new
                response = self.api.create_event(event_data)

                if response:
                    # Store hash and event_id for sync tracking
                    workout["description_hash"] = new_hash
                    workout["intervals_id"] = response.get("id")
                    print(f"  ✅ Créé : {workout['name']} ({workout['date']})")
                    return True
                else:
                    print(f"  ❌ Échec création : {workout['name']}")
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
