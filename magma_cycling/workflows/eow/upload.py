"""Workout validation, upload and planning JSON methods for EndOfWeekWorkflow."""

import re
import sys
from datetime import datetime

from magma_cycling.planning.audit_log import OperationStatus, OperationType, audit_log
from magma_cycling.planning.models import WeeklyPlan


class UploadMixin:
    """Validation, upload vers Intervals.icu et sauvegarde planning JSON."""

    def _step4_validate_workouts(self) -> bool:
        """Step 4: Validate workouts notation with format-planning logic."""
        print("\n" + "=" * 80)
        print("🔍 STEP 4/7: Validation Notation Workouts")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation validation")
            return True

        try:
            # Use upload-workouts validation (already integrated)
            # Parse workouts to validate
            from magma_cycling.upload_workouts import WorkoutUploader

            # Create temporary uploader for validation only
            dummy_date = datetime.now()
            uploader = WorkoutUploader(self.week_next, dummy_date)

            if self.workouts_file:
                workouts = uploader.parse_workouts_file(self.workouts_file)
            else:
                print("  ❌ Pas de fichier workouts à valider")
                return False

            # Validation is already done in parse_workouts_file
            if not workouts:
                print("  ❌ Validation échouée - workouts incomplets ou mal formatés")
                print("  💡 Utilisez format-planning pour corriger")
                return False

            print("  ✅ Validation réussie")
            return True

        except Exception as e:
            print(f"  ❌ Erreur validation : {e}")
            return False

    def _step5_upload_workouts(self) -> bool:
        """Step 5: Upload workouts to Intervals.icu."""
        print("\n" + "=" * 80)
        print("📤 STEP 5/7: Upload Workouts vers Intervals.icu")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation upload")
            return True

        if not self.workouts_file:
            print("  ❌ Pas de fichier workouts à uploader")
            return False

        try:
            print(
                f"  📅 Semaine : {self.week_next} "
                f"({self.next_start_date.strftime('%d/%m/%Y')} → "
                f"{self.next_end_date.strftime('%d/%m/%Y')})"
            )
            print()

            if self.auto:
                # Auto mode: call upload programmatically
                print("  🤖 Mode automatique - Upload programmatique")
                print(f"  📁 Fichier : {self.workouts_file}")
                print()

                from magma_cycling.upload_workouts import WorkoutUploader

                uploader = WorkoutUploader(self.week_next, self.next_start_date)
                workouts = uploader.parse_workouts_file(self.workouts_file)

                if not workouts:
                    print("  ❌ Erreur parsing workouts")
                    return False

                print(f"  📊 {len(workouts)} workouts à uploader")
                print()

                # Upload all workouts
                result = uploader.upload_all(workouts, dry_run=False)

                print()
                print(f"  ✅ Upload réussi : {result['success']}/{result['total']}")
                if result["errors"]:
                    print(f"  ⚠️  Erreurs : {len(result['errors'])}")
                    for error in result["errors"]:
                        print(f"     • {error}")

                return result["success"] == result["total"]
            else:
                # Manual mode: prompt user to upload manually
                print("  ⚠️  Upload RÉEL vers Intervals.icu")
                print(f"  📁 Fichier : {self.workouts_file}")
                print()
                response = input("  Confirmer upload ? (o/n) : ")
                if response.lower() != "o":
                    print("  ⚠️  Upload annulé")
                    return False

                print()
                print("  💡 Exécutez manuellement:")
                print(
                    f"     poetry run upload-workouts --week-id {self.week_next} "
                    f"--start-date {self.next_start_date.strftime('%Y-%m-%d')} "
                    f"--file {self.workouts_file}"
                )
                print()

                response = input("  Upload effectué avec succès ? (o/n) : ")
                return response.lower() == "o"

        except Exception as e:
            print(f"  ❌ Erreur upload : {e}")
            return False

    def _step5b_save_planning_json(self):
        """Step 5b: Save planning JSON with real uploaded workout data."""
        print("\n" + "=" * 80)
        print("💾 STEP 5b/7: Sauvegarde Planning JSON")
        print("=" * 80)
        print()

        try:
            if not self.workouts_file:
                print("  ⚠️  Pas de fichier workouts - JSON template déjà créé")
                return

            # Import dependencies
            from magma_cycling.api.intervals_client import IntervalsClient
            from magma_cycling.config import get_intervals_config

            # Parse workouts file to extract metadata
            print("  📄 Parsing fichier workouts...")
            workouts_text = self.workouts_file.read_text(encoding="utf-8")

            workout_metadata = {}
            for match in re.finditer(
                r"=== WORKOUT (S\d+-\d+-\w+-\w+-V\d+) ===\s*\n\s*(.+?)\((\d+)min, (\d+) TSS\)",
                workouts_text,
            ):
                workout_id = match.group(1)
                name_desc = match.group(2).strip()
                duration = int(match.group(3))
                tss = int(match.group(4))
                workout_metadata[workout_id] = {
                    "name_full": name_desc,
                    "duration_min": duration,
                    "tss_planned": tss,
                }

            # Recalculate durations from blocks (source of truth)
            from magma_cycling.workout_parser import calculate_workout_duration

            body_pattern = r"=== WORKOUT (S\d+-\d+-\w+-\w+-V\d+) ===\n(.*?)\n=== FIN WORKOUT ==="
            for body_match in re.finditer(body_pattern, workouts_text, re.DOTALL):
                wid = body_match.group(1)
                if wid in workout_metadata:
                    calculated = calculate_workout_duration(body_match.group(2).strip())
                    if calculated is not None:
                        workout_metadata[wid]["duration_min"] = calculated

            print(f"     ✓ {len(workout_metadata)} workouts parsés")

            # Get uploaded events from Intervals.icu
            print("  🌐 Récupération events Intervals.icu...")
            config = get_intervals_config()
            client = IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)

            events = client.get_events(
                oldest=self.next_start_date.isoformat(),
                newest=self.next_end_date.isoformat(),
            )

            workouts = [
                e
                for e in events
                if e.get("category") == "WORKOUT" and e.get("name", "").startswith(self.week_next)
            ]
            workouts_sorted = sorted(workouts, key=lambda x: x.get("start_date_local", ""))

            print(f"     ✓ {len(workouts_sorted)} workouts uploadés")

            # Build planning data structure
            planning_data = {
                "week_id": self.week_next,
                "start_date": self.next_start_date.isoformat(),
                "end_date": self.next_end_date.isoformat(),
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": 1,
                "athlete_id": config.athlete_id,
                "tss_target": 0,
                "source": "eow",
                "planned_sessions": [],
            }

            tss_total = 0

            for workout in workouts_sorted:
                workout_name = workout.get("name", "")
                # Parse: S079-01-END-RepriseDouceLundi-V001
                match = re.match(r"(S\d+-\d+)-(\w+)-(.+?)-(V\d+)", workout_name)
                if not match:
                    print(f"     ⚠️  Format invalide: {workout_name}")
                    continue

                session_id = match.group(1)  # S079-01
                workout_type = match.group(2)  # END
                workout_name_part = match.group(3)  # RepriseDouceLundi
                version = match.group(4)  # V001

                # Get metadata from parsing
                meta = workout_metadata.get(workout_name, {})
                tss = meta.get("tss_planned", 0)
                duration = meta.get("duration_min", 0)
                description = meta.get("name_full", workout_name_part)

                tss_total += tss

                workout_date = workout.get("start_date_local", "").split("T")[0]

                session = {
                    "session_id": session_id,
                    "session_date": workout_date,
                    "name": workout_name_part,
                    "session_type": workout_type,
                    "version": version,
                    "tss_planned": tss,
                    "duration_min": duration,
                    "description": description,
                    "status": "pending",
                    "intervals_id": workout.get("id"),
                    "description_hash": None,
                }
                planning_data["planned_sessions"].append(session)

            planning_data["tss_target"] = tss_total

            # Create planning via WeeklyPlan model
            json_file = self.planning_dir / f"week_planning_{self.week_next}.json"

            # Validate and create planning object
            plan = WeeklyPlan(**planning_data)
            plan.to_json(json_file)

            # Audit log for CREATE operation
            audit_log.log_operation(
                operation=OperationType.CREATE,
                week_id=self.week_next,
                status=OperationStatus.SUCCESS,
                tool="end-of-week",
                description=f"Created planning for {self.week_next} ({len(planning_data['planned_sessions'])} sessions, {tss_total} TSS)",
                requested_by="end-of-week-workflow",
            )

            print()
            print(f"  ✅ Planning JSON créé: {json_file}")
            print(f"     • {len(planning_data['planned_sessions'])} sessions")
            print(f"     • TSS total: {tss_total}")

        except Exception as e:
            print(f"  ⚠️  Erreur sauvegarde JSON (non bloquant): {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Non-blocking: continue workflow even if JSON save fails
