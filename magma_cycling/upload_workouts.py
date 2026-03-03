#!/usr/bin/env python3
"""
Upload Zwift workout files (.zwo) to Intervals.icu calendar.

Upload fichiers workouts Zwift (.zwo) vers calendrier Intervals.icu.
Convertit format Zwift en format Intervals.icu et planifie séances
automatiquement.

Examples:
    Upload single workout::

        from magma_cycling.upload_workouts import upload_workout
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

        from magma_cycling.upload_workouts import upload_week

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
import sys
from datetime import datetime
from pathlib import Path

from magma_cycling.workflows.uploader.parsing import ParsingMixin
from magma_cycling.workflows.uploader.upload import UploadMixin
from magma_cycling.workflows.uploader.validation import ValidationMixin


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
    from magma_cycling.config import get_week_config

    # Load reference date and offset from config (multi-season aware)
    week_config = get_week_config()
    reference_date, weeks_offset = week_config.get_reference_for_week(week_id)

    # Convert to datetime
    reference_datetime = datetime.combine(reference_date, datetime.min.time())

    # Calculate target Monday
    from datetime import timedelta

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


class WorkoutUploader(
    ValidationMixin,
    ParsingMixin,
    UploadMixin,
):
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
            from magma_cycling.config import create_intervals_client

            self.api = create_intervals_client()
            print("✅ API Intervals.icu connectée")
        except Exception as e:
            print(f"❌ Erreur connexion API : {e}")
            sys.exit(1)


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

    # 🔒 AUTOMATIC BACKUP before any upload
    if not args.dry_run:
        try:
            from magma_cycling.planning.backup import auto_backup

            backups = auto_backup(args.week_id)
            if backups:
                print("🔒 Backup créé:")
                for file_type, backup_path in backups.items():
                    print(f"   {file_type}: {backup_path.name}")
        except Exception as e:
            print(f"⚠️  Avertissement: backup échoué: {e}")
            print("   Continuer quand même...")

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
