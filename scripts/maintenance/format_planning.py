#!/usr/bin/env python3
"""
Format Planning - Reformate la sortie AI coach pour upload Intervals.icu.

Script de maintenance pour reformater les workouts générés par l'AI coach
dans le format standard requis par wu (upload-workouts).

Usage:
    # Depuis clipboard (sortie AI)
    python scripts/maintenance/format_planning.py --week-id S075

    # Depuis fichier
    python scripts/maintenance/format_planning.py --week-id S075 --input planning.md

    # Dry-run (affiche sans sauvegarder)
    python scripts/maintenance/format_planning.py --week-id S075 --dry-run

Examples:
    # Workflow complet
    wp --week-id S075 --start-date 2026-01-05
    # → Coller prompt dans AI coach
    # → Copier sortie AI dans clipboard
    python scripts/maintenance/format_planning.py --week-id S075
    wu --week-id S075 --start-date 2026-01-05

Metadata:
    Created: 2026-01-04
    Author: Claude Code
    Category: M (Maintenance)
    Status: Production
    Priority: P1
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


class WorkoutFormatter:
    """Format AI coach workouts for Intervals.icu upload."""

    def __init__(self, week_id: str):
        """Initialize formatter.

        Args:
            week_id: Week identifier (e.g., "S075")
        """
        self.week_id = week_id
        self.workouts: list[dict] = []

    def read_from_clipboard(self) -> str:
        """Read content from clipboard.

        Returns:
            Clipboard content as string
        """
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture clipboard: {e}")
            sys.exit(1)

    def read_from_file(self, filepath: Path) -> str:
        """Read content from file.

        Args:
            filepath: Path to input file

        Returns:
            File content as string
        """
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Erreur lecture fichier: {e}")
            sys.exit(1)

    def parse_workouts(self, content: str) -> list[dict]:
        """Parse workouts from AI coach output.

        Detects various formats and extracts workout information.

        Args:
            content: Raw AI output content

        Returns:
            List of workout dictionaries
        """
        workouts = []

        # Pattern 1: Markdown headers with workout names
        # ## S075-01 - Lundi 05/01/2026
        # **Type**: REC - Récupération Active
        pattern1 = r"##\s+(S\d{3}-\d{2}).*?\n(.*?)(?=\n##|\Z)"

        matches = re.findall(pattern1, content, re.DOTALL)

        for workout_id, workout_content in matches:
            # Extract workout details
            workout = self._extract_workout_details(workout_id, workout_content)
            if workout:
                workouts.append(workout)

        # If no matches with pattern1, try alternative patterns
        if not workouts:
            # Pattern 2: Already formatted with delimiters
            pattern2 = r"===\s*WORKOUT\s+(.*?)\s*===\n(.*?)\n===\s*FIN WORKOUT\s*==="
            matches = re.findall(pattern2, content, re.DOTALL)

            for workout_name, workout_content in matches:
                workout = {
                    "id": workout_name.strip(),
                    "name": workout_name.strip(),
                    "content": workout_content.strip(),
                }
                workouts.append(workout)

        return workouts

    def _extract_workout_details(self, workout_id: str, content: str) -> dict | None:
        """Extract workout details from content block.

        Args:
            workout_id: Workout identifier (e.g., "S075-01")
            content: Workout content block

        Returns:
            Workout dictionary or None
        """
        # Extract type and name
        type_match = re.search(r"\*\*Type\*\*:\s*(\w+)\s*-\s*(.*?)(?:\n|$)", content)
        name_match = re.search(r"\*\*Nom\*\*:\s*(.*?)(?:\n|$)", content)

        if not type_match or not name_match:
            return None

        workout_type = type_match.group(1)
        workout_desc = type_match.group(2).strip()
        workout_name = name_match.group(1).strip()

        # Build full workout name
        full_name = f"{workout_id}-{workout_type}-{workout_name}"

        # Extract structure section
        structure_match = re.search(r"###\s*Structure\s*\n(.*?)(?=###|\n##|\Z)", content, re.DOTALL)
        structure = structure_match.group(1).strip() if structure_match else "Structure non trouvée"

        # Extract other sections (TSS, duration, etc.)
        tss_match = re.search(r"TSS[^:]*:\s*(\d+)", content)
        duration_match = re.search(r"Durée[^:]*:\s*(\d+)\s*min", content)

        # Build description
        description_parts = [workout_desc, "", "Structure:", structure]

        if tss_match:
            description_parts.append(f"\nTSS: {tss_match.group(1)}")
        if duration_match:
            description_parts.append(f" | Durée: {duration_match.group(1)}min")

        return {
            "id": workout_id,
            "name": full_name,
            "content": "\n".join(description_parts),
        }

    def validate_notation(self, workout: dict) -> list[str]:
        """Validate workout notation standards.

        Args:
            workout: Workout dictionary

        Returns:
            List of validation warnings
        """
        warnings = []
        content = workout["content"]

        # Check for repetition notation
        # Should be: "Main set: 5x" not "5x [...]"
        if re.search(r"\d+x\s*\[", content):
            warnings.append(
                f"⚠️  {workout['id']}: Notation '5x [...]' détectée - "
                "devrait être 'Main set: 5x' puis éléments en dessous"
            )

        # Check for factorized power (should be explicit on each line)
        # Pattern: "- Main set @ 65% FTP:" without power on sub-lines
        main_set_match = re.search(r"-\s*\*?\*?Main set\*?\*?\s*@\s*\d+%", content)
        if main_set_match:
            # Check if sub-lines have explicit power
            lines_after = content[main_set_match.end() :].split("\n")[:5]
            if any(re.match(r"\s*-\s*\d+min.*(?<!\d%)", line) for line in lines_after):
                warnings.append(
                    f"⚠️  {workout['id']}: Puissance factorisée détectée - "
                    "chaque ligne doit avoir sa puissance explicite"
                )

        return warnings

    def format_for_upload(self, workouts: list[dict]) -> str:
        """Format workouts with proper delimiters for wu.

        Args:
            workouts: List of workout dictionaries

        Returns:
            Formatted content ready for upload
        """
        formatted_parts = []

        for workout in workouts:
            formatted_parts.append(f"=== WORKOUT {workout['name']} ===")
            formatted_parts.append(workout["content"])
            formatted_parts.append("=== FIN WORKOUT ===")
            formatted_parts.append("")  # Empty line between workouts

        return "\n".join(formatted_parts)

    def save_formatted(self, content: str, output_path: Path):
        """Save formatted content to file.

        Args:
            content: Formatted workout content
            output_path: Output file path
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"✅ Sauvegardé: {output_path}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            sys.exit(1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Reformater workouts AI coach pour upload Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Depuis clipboard (sortie AI)
  python scripts/maintenance/format_planning.py --week-id S075

  # Depuis fichier
  python scripts/maintenance/format_planning.py --week-id S075 --input planning.md

  # Dry-run (affiche sans sauvegarder)
  python scripts/maintenance/format_planning.py --week-id S075 --dry-run

Workflow complet:
  1. wp --week-id S075 --start-date 2026-01-05
  2. Coller prompt dans AI coach
  3. Copier sortie AI dans clipboard
  4. python scripts/maintenance/format_planning.py --week-id S075
  5. wu --week-id S075 --start-date 2026-01-05
        """,
    )

    parser.add_argument(
        "--week-id",
        type=str,
        required=True,
        help="ID de la semaine (format SXXX, ex: S075)",
    )

    parser.add_argument(
        "--input",
        type=Path,
        help="Fichier d'entrée (si non spécifié, lit depuis clipboard)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Fichier de sortie (défaut: /tmp/{week_id}_workouts_formatted.txt)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (affiche sans sauvegarder)",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validation uniquement (pas de reformatage)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mode verbose (affiche détails)",
    )

    return parser.parse_args()


def main():
    """Point d'entrée du script."""
    args = parse_args()

    print("=" * 70)
    print(f"🔧 FORMAT PLANNING - {args.week_id}")
    print("=" * 70)
    print()

    # Initialize formatter
    formatter = WorkoutFormatter(args.week_id)

    # Read input
    if args.input:
        print(f"📄 Lecture depuis fichier: {args.input}")
        content = formatter.read_from_file(args.input)
    else:
        print("📋 Lecture depuis clipboard...")
        content = formatter.read_from_clipboard()

    print(f"   ✅ {len(content)} caractères lus")
    print()

    # Parse workouts
    print("🔍 Parsing workouts...")
    workouts = formatter.parse_workouts(content)

    if not workouts:
        print("❌ Aucun workout détecté dans le contenu")
        print()
        print("💡 Format attendu:")
        print("   ## S075-01 - Lundi 05/01/2026")
        print("   **Type**: REC - Récupération Active")
        print("   **Nom**: ReposActifZ1-V001")
        print("   ### Structure")
        print("   ...")
        return 1

    print(f"   ✅ {len(workouts)} workout(s) détecté(s)")
    print()

    # Display workouts found
    for i, workout in enumerate(workouts, 1):
        print(f"  {i}. {workout['name']}")

    print()

    # Validate notation
    print("✓ Validation notation...")
    all_warnings = []

    for workout in workouts:
        warnings = formatter.validate_notation(workout)
        all_warnings.extend(warnings)

    if all_warnings:
        print()
        for warning in all_warnings:
            print(f"  {warning}")
        print()
    else:
        print("   ✅ Notation conforme")
        print()

    if args.validate_only:
        print("✅ Validation terminée")
        return 0 if not all_warnings else 1

    # Format for upload
    print("📝 Formatage pour upload...")
    formatted_content = formatter.format_for_upload(workouts)
    print("   ✅ Formatage terminé")
    print()

    # Dry-run mode
    if args.dry_run:
        print("🔍 DRY-RUN - Aperçu du contenu formaté:")
        print("=" * 70)
        print(formatted_content[:500])
        if len(formatted_content) > 500:
            print(f"\n... ({len(formatted_content) - 500} caractères supplémentaires)")
        print("=" * 70)
        print()
        print("💡 Relancez sans --dry-run pour sauvegarder")
        return 0

    # Save formatted content
    output_path = args.output or Path(f"/tmp/{args.week_id}_workouts_formatted.txt")

    formatter.save_formatted(formatted_content, output_path)

    # Summary
    print()
    print("=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print()
    print(f"✅ Workouts formatés : {len(workouts)}")
    if all_warnings:
        print(f"⚠️  Avertissements   : {len(all_warnings)}")
    print(f"📄 Fichier généré   : {output_path}")
    print()

    print("💡 Prochaines étapes:")
    print(f"   wu --week-id {args.week_id} --start-date YYYY-MM-DD --file {output_path}")
    print()
    print("=" * 70)

    return 0 if not all_warnings else 1


if __name__ == "__main__":
    sys.exit(main())
