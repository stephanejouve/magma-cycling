#!/usr/bin/env python3
"""
validate_templates.py - Valider tous les templates workout

Vérifie que les templates respectent le format Intervals.icu.
"""
import json
from pathlib import Path

from cyclisme_training_logs.intervals_format_validator import IntervalsFormatValidator


def main():
    """Command-line entry point for validating workout templates."""
    templates_dir = Path("data/workout_templates")
    validator = IntervalsFormatValidator()

    print("=" * 70)
    print("VALIDATION TEMPLATES WORKOUT")
    print("=" * 70)
    print()

    all_valid = True

    for template_file in sorted(templates_dir.glob("*.json")):
        print(f"📄 {template_file.name}")

        with open(template_file, encoding="utf-8") as f:
            template = json.load(f)

        # Extraire format Intervals.icu
        intervals_format = template.get("intervals_icu_format", "")

        # Valider
        is_valid, errors, warnings = validator.validate_workout(intervals_format)

        if is_valid and not warnings:
            print("   ✅ Valide")
        elif is_valid and warnings:
            print("   ⚠️  Valide avec avertissements:")
            for warning in warnings:
                print(f"      {warning}")
        else:
            print("   ❌ Erreurs:")
            for error in errors:
                print(f"      {error}")
            all_valid = False

        print()

    print("=" * 70)
    if all_valid:
        print("✅ TOUS LES TEMPLATES SONT VALIDES")
    else:
        print("❌ CERTAINS TEMPLATES ONT DES ERREURS")
    print("=" * 70)


if __name__ == "__main__":
    main()
