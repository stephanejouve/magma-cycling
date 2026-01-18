#!/usr/bin/env python3
"""
Upload Zwift workout files (.zwo) to Intervals.icu calendar.

Upload fichiers workouts Zwift (.zwo) vers calendrier Intervals.icu.
Convertit format Zwift en format Intervals.icu et planifie séances
automatiquement.

Examples:
    Upload single workout::

        from cyclisme_training_logs.upload_workouts import upload_workout
        from pathlib import Path

        # Upload fichier .zwo
        workout_file = Path("S073-01-INT-SweetSpot-V001.zwo")

        result = upload_workout(
            workout_file,
            target_date="2025-01-06"
        )

        if result.success:
            print(f"Uploaded: {result.workout_id}")

    Batch upload week::

        from cyclisme_training_logs.upload_workouts import upload_week

        # Upload semaine complète
        week_dir = Path("workouts/S073-Semaine73")

        results = upload_week(
            week_dir,
            start_date="2025-01-06"
        )

        print(f"Uploaded {len(results)} workouts")

    CLI usage::

        # Command-line upload
        poetry run upload-workouts --week-id S073 --file S073-01-INT-SweetSpot-V001.zwo --date 2025-01-06

        # Upload entire week (start-date optional, calculated automatically)
        poetry run upload-workouts --week-id S073
        poetry run upload-workouts --week-id S073 --start-date 2025-01-06

Author: Stéphane Jouve
Created: 2024-10-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""
import argparse
import hashlib
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def calculate_week_start_date(week_id: str) -> datetime:
    """
    Calculate Monday start date from project week ID.

    Reads reference dates from .config.json with multi-season support (no hardcoded dates).

    Args:
        week_id: Week identifier (e.g., "S075")

    Returns:
        Datetime of Monday for that week

    Examples:
        >>> calculate_week_start_date("S075")
        datetime(2026, 1, 5, 0, 0)  # Season 2026
    """
    from cyclisme_training_logs.config import get_week_config

    # Load reference date and offset from config (multi-season aware)
    week_config = get_week_config()
    reference_date, weeks_offset = week_config.get_reference_for_week(week_id)

    # Convert to datetime
    reference_datetime = datetime.combine(reference_date, datetime.min.time())

    # Calculate target Monday
    target_monday = reference_datetime + timedelta(weeks=weeks_offset)

    # Validation: must be a Monday
    if target_monday.weekday() != 0:
        raise ValueError(f"Calculated date {target_monday} is not a Monday")

    return target_monday


def calculate_description_hash(description: str) -> str:
    """
    Calculate SHA256 hash of workout description for change detection.

    Args:
        description: Workout description text

    Returns:
        16-character hex hash of description (first 16 chars of SHA256)
    """
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:16]


class WorkoutUploader:
    """Upload des workouts vers Intervals.icu."""

    def __init__(self, week_number: str, start_date: datetime):
        """Initialize the workout uploader.

        Args:
            week_number: Week identifier (e.g., "S074")
            start_date: Start date of the week (Monday)
        """
        self.week_number = week_number

        self.start_date = start_date
        self.api = None
        self._init_api()

    def _init_api(self):
        """Initialize l'API Intervals.icu."""
        try:
            # Sprint R9.B - Use centralized client creation
            from cyclisme_training_logs.config import create_intervals_client

            self.api = create_intervals_client()
            print("✅ API Intervals.icu connectée")
        except Exception as e:
            print(f"❌ Erreur connexion API : {e}")
            sys.exit(1)

    def validate_workout_notation(self, workout: dict) -> list[str]:
        """Validate workout notation standards.

        Args:
            workout: Workout dictionary with 'name' and 'description' keys

        Returns:
            List of validation warnings
        """
        warnings = []
        content = workout["description"]
        workout_id = workout["name"]

        # Check for repetition notation
        # Should be: "Main set: Nx" not "Nx [...]"
        bad_rep = re.search(r"(\d+)x\s*\[", content)
        if bad_rep:
            rep_count = bad_rep.group(1)
            warnings.append(
                f"⚠️  {workout_id}: Notation '{rep_count}x [...]' détectée - "
                f"devrait être 'Main set: {rep_count}x' puis éléments en dessous"
            )

        # Check for factorized power (should be explicit on each line)
        main_set_match = re.search(r"-\s*\*?\*?Main set\*?\*?\s*@\s*\d+%", content)
        if main_set_match:
            # Check if sub-lines have explicit power
            lines_after = content[main_set_match.end() :].split("\n")[:5]
            if any(re.match(r"\s*-\s*\d+min.*(?<!\d%)", line) for line in lines_after):
                warnings.append(
                    f"⚠️  {workout_id}: Puissance factorisée détectée - "
                    "chaque ligne doit avoir sa puissance explicite"
                )

        # Validate warmup ramps (should be ascending)
        # Only look in the line containing "warmup" to avoid cross-section matches
        warmup_lines = [line for line in content.split("\n") if re.search(r"(?i)warmup", line)]
        for line in warmup_lines:
            warmup_ramp = re.search(r"ramp\s+(\d+)%\s*→\s*(\d+)%", line)
            if warmup_ramp:
                start_pct = int(warmup_ramp.group(1))
                end_pct = int(warmup_ramp.group(2))
                if start_pct >= end_pct:
                    warnings.append(
                        f"⚠️  {workout_id}: Warmup ramp devrait être ascendant "
                        f"({start_pct}% → {end_pct}%)"
                    )
                break  # Only check first warmup ramp

        # Validate cooldown ramps (should be descending)
        # Only look in the line containing "cooldown" to avoid cross-section matches
        cooldown_lines = [line for line in content.split("\n") if re.search(r"(?i)cooldown", line)]
        for line in cooldown_lines:
            cooldown_ramp = re.search(r"ramp\s+(\d+)%\s*→\s*(\d+)%", line)
            if cooldown_ramp:
                start_pct = int(cooldown_ramp.group(1))
                end_pct = int(cooldown_ramp.group(2))
                if start_pct <= end_pct:
                    warnings.append(
                        f"⚠️  {workout_id}: Cooldown ramp devrait être descendant "
                        f"({start_pct}% → {end_pct}%)"
                    )
                break  # Only check first cooldown ramp

        # Check ramp format (should include watts)
        ramps = re.findall(r"ramp\s+\d+%\s*→\s*\d+%", content)
        for ramp in ramps:
            ramp_line_match = re.search(rf"{re.escape(ramp)}[^\n]*", content)
            if ramp_line_match:
                ramp_line = ramp_line_match.group(0)
                if not re.search(r"\(\d+W\s*→\s*\d+W\)", ramp_line):
                    warnings.append(
                        f"⚠️  {workout_id}: Rampe sans watts explicites - "
                        f"devrait inclure (XXW→YYW)"
                    )
                    break  # Only warn once per workout

        # CRITICAL: Check for warmup/cooldown presence
        # Skip validation for rest days (REPOS)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        if not is_rest_day:
            # Look for section markers, not just word mentions
            has_warmup = re.search(
                r"(?i)(^|\n)\s*[-*#]?\s*(warmup|échauffement|warm-up)[\s:*]", content
            )
            has_cooldown = re.search(
                r"(?i)(^|\n)\s*[-*#]?\s*(cooldown|retour au calme|cool-down)[\s:*]", content
            )

            if not has_warmup:
                warnings.append(f"🚨 {workout_id}: WARMUP MANQUANT - séance incomplète")

            if not has_cooldown:
                warnings.append(f"🚨 {workout_id}: COOLDOWN MANQUANT - séance incomplète")

            # CRITICAL: Check for missing dashes before instructions
            # Parser Intervals.icu requires dashes to identify steps
            lines = content.split("\n")

            for i, line in enumerate(lines):
                # Check if this is a section header
                if re.search(r"(?i)(warmup|main set|cooldown)", line):
                    # Check next non-empty lines for missing dashes
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_line = lines[j].strip()

                        # Skip empty lines
                        if not next_line:
                            continue

                        # Stop if we hit another section
                        if re.search(r"(?i)(warmup|main set|cooldown)", next_line):
                            break

                        # Check if line looks like an instruction but has no dash
                        # Instruction pattern: starts with time (10m, 3x, etc)
                        if re.match(r"^\d+[mx]?\s", next_line):
                            if not next_line.startswith("-"):
                                warnings.append(
                                    f"🚨 {workout_id}: TIRET MANQUANT - instruction sans tiret: '{next_line[:40]}...'\n"
                                    f"   → Parser Intervals.icu nécessite '-' devant chaque instruction"
                                )
                                break  # One warning per section is enough

        return warnings

    def parse_workouts_file(self, filepath: Path) -> list[dict]:
        """Parse un fichier contenant les workouts."""
        print(f"\n📄 Lecture fichier : {filepath}")

        if not filepath.exists():
            print(f"❌ Fichier non trouvé : {filepath}")
            return []

        content = filepath.read_text(encoding="utf-8")
        pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
        matches = re.findall(pattern, content, re.DOTALL)

        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")

        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r"-(\d{2})-", workout_name)
            if not day_match:
                print(f"⚠️ Format invalide : {workout_name}")
                continue

            day_num = int(day_match.group(1))

            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(
                    f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)"
                )
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)

            # FIX: Extraire le nom descriptif (première ligne du contenu)
            workout_content.strip().split("\n")[0]

            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            # Et first_line comme description courte
            workout_display_name = workout_name.strip()

            workouts.append(
                {
                    "filename": workout_name.strip(),
                    "day": day_num,
                    "date": workout_date.strftime("%Y-%m-%d"),
                    "name": workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                    "description": workout_content.strip(),
                }
            )

            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")

        print(f"\n📊 Total : {len(workouts)} workout(s) détectés")

        # VALIDATION AUTOMATIQUE
        if workouts:
            print("\n🔍 Validation qualité notation...")
            all_warnings = []
            critical_warnings = []

            for workout in workouts:
                warnings = self.validate_workout_notation(workout)
                all_warnings.extend(warnings)
                # Séparer warnings critiques (warmup/cooldown manquants)
                critical_warnings.extend([w for w in warnings if "🚨" in w])

            if all_warnings:
                print()
                for warning in all_warnings:
                    print(f"  {warning}")
                print()

                if critical_warnings:
                    print("🚨 ERREURS CRITIQUES DÉTECTÉES - Upload BLOQUÉ")
                    print("   Des séances sont incomplètes ou mal formatées:")
                    print("   - Warmup/cooldown manquants")
                    print("   - Tirets manquants devant les instructions")
                    print("   → Utilisez format-planning pour corriger le format")
                    return []
            else:
                print("  ✅ Validation réussie - notation conforme")

        return workouts

    def parse_clipboard(self) -> list[dict]:
        """Parse les workouts depuis le presse-papier."""
        import subprocess

        print("\n📋 Lecture presse-papier...")

        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            content = result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return []

        pattern = r"=== WORKOUT (.*?) ===\n(.*?)\n=== FIN WORKOUT ==="
        matches = re.findall(pattern, content, re.DOTALL)

        # Mode single workout : utiliser date exacte
        single_workout_mode = len(matches) == 1
        if single_workout_mode:
            print("  ℹ️  Mode single workout détecté - utilisation date exacte")

        workouts = []
        for workout_name, workout_content in matches:
            day_match = re.search(r"-(\d{2})-", workout_name)
            if not day_match:
                continue

            day_num = int(day_match.group(1))

            # Si single workout, utiliser start_date directement
            if single_workout_mode:
                workout_date = self.start_date
                print(
                    f"  📌 Workout sera uploadé le {workout_date.strftime('%d/%m/%Y')} (date explicite)"
                )
            else:
                workout_date = self.start_date + timedelta(days=day_num - 1)

            # FIX: Extraire le nom descriptif (première ligne du contenu)
            workout_content.strip().split("\n")[0]

            # FIX: Utiliser workout_name (depuis délimiteur) comme nom principal
            workout_display_name = workout_name.strip()

            workouts.append(
                {
                    "filename": workout_name.strip(),
                    "day": day_num,
                    "date": workout_date.strftime("%Y-%m-%d"),
                    "name": workout_display_name,  # ← FIX: Utiliser le nom du délimiteur
                    "description": workout_content.strip(),
                }
            )

            print(f"  ✅ Jour {day_num:02d} ({workout_date.strftime('%d/%m')}) : {workout_name}")

        print(f"\n📊 Total : {len(workouts)} workout(s) dans le presse-papier")

        # VALIDATION AUTOMATIQUE
        if workouts:
            print("\n🔍 Validation qualité notation...")
            all_warnings = []
            critical_warnings = []

            for workout in workouts:
                warnings = self.validate_workout_notation(workout)
                all_warnings.extend(warnings)
                # Séparer warnings critiques (warmup/cooldown manquants)
                critical_warnings.extend([w for w in warnings if "🚨" in w])

            if all_warnings:
                print()
                for warning in all_warnings:
                    print(f"  {warning}")
                print()

                if critical_warnings:
                    print("🚨 ERREURS CRITIQUES DÉTECTÉES - Upload BLOQUÉ")
                    print("   Des séances sont incomplètes ou mal formatées:")
                    print("   - Warmup/cooldown manquants")
                    print("   - Tirets manquants devant les instructions")
                    print("   → Utilisez format-planning pour corriger le format")
                    return []
            else:
                print("  ✅ Validation réussie - notation conforme")

        return workouts

    def upload_workout(self, workout: dict) -> bool:
        """Upload un workout sur Intervals.icu."""
        try:
            # Déterminer l'heure de début selon le jour de la semaine
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            day_of_week = workout_date.weekday()  # 0=Lundi, 5=Samedi, 6=Dimanche

            # Samedi (5) → 09:00, autres jours → 17:00
            start_time = "09:00:00" if day_of_week == 5 else "17:00:00"

            event_data = {
                "category": "WORKOUT",
                "type": "VirtualRide",
                "name": workout["name"],
                "description": workout["description"],
                "start_date_local": f"{workout['date']}T{start_time}",
            }

            if self.api is None:
                print("  ❌ Erreur : API non initialisée")
                return False

            response = self.api.create_event(event_data)

            if response:
                # Store hash and event_id for sync tracking
                workout["description_hash"] = calculate_description_hash(workout["description"])
                workout["intervals_id"] = response.get("id")
                print(f"  ✅ Uploadé : {workout['name']} ({workout['date']})")
                return True
            else:
                print(f"  ❌ Échec : {workout['name']}")
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

        return stats


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(description="Uploader des workouts sur Intervals.icu")

    parser.add_argument(
        "--week-id", type=str, required=True, help="Numéro de semaine (format SXXX, ex: S072)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=False,
        help="Date de début - LUNDI pour semaine complète (optionnel, calculé automatiquement)",
    )
    parser.add_argument("--file", type=str, help="Fichier contenant les workouts")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans upload réel")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt (for automation)"
    )

    args = parser.parse_args()

    if not args.week_id.startswith("S") or len(args.week_id) != 4:
        print(f"❌ Format semaine invalide : {args.week_id}")
        sys.exit(1)

    # Calculate start date automatically if not provided
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Format date invalide : {args.start_date}")
            sys.exit(1)
    else:
        try:
            start_date = calculate_week_start_date(args.week_id)
            print(f"📅 Date calculée automatiquement : {start_date.strftime('%Y-%m-%d')}")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Impossible de calculer la date pour {args.week_id}: {e}")
            print("   Utilisez --start-date pour spécifier manuellement")
            sys.exit(1)

    uploader = WorkoutUploader(args.week_id, start_date)

    if args.file:
        workouts = uploader.parse_workouts_file(Path(args.file))
    else:
        workouts = uploader.parse_clipboard()

    if not workouts:
        print("\n❌ Aucun workout détecté")
        sys.exit(1)

    if not args.dry_run and not args.yes:
        print("\n⚠️  ATTENTION : Upload RÉEL sur Intervals.icu")
        print(f"   {len(workouts)} workout(s) seront créés pour {args.week_id}")
        response = input("\nContinuer ? (o/n) : ")
        if response.lower() != "o":
            print("❌ Upload annulé")
            sys.exit(0)

    stats = uploader.upload_all(workouts, dry_run=args.dry_run)

    if stats["failed"] > 0:
        sys.exit(1)
    else:
        print("\n✅ Upload terminé avec succès !")
        sys.exit(0)


if __name__ == "__main__":
    main()
