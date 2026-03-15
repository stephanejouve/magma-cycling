#!/usr/bin/env python3
"""
Validate Intervals.icu workout format syntax and structure.

Valide syntaxe et structure workouts format Intervals.icu avant upload.
Vérifie cohérence durées, pourcentages FTP, format répétitions, et
génère warnings si problèmes détectés.

Examples:
    Validate workout syntax::

        from magma_cycling.intervals_format_validator import validate_workout

        workout_text = '''
        Warmup
        - 10m 50-75% 85rpm

        Main set 4x
        - 8m 90% 90rpm
        - 3m 65% 85rpm

        result = validate_workout(workout_text)

        if result.valid:
            print("✅ Valid Intervals.icu format")
        else:
            print(f"❌ Errors: {result.errors}")

    Check file before upload::

        from pathlib import Path

        # Valider fichier .txt avant conversion
        workout_file = Path("S073-01-workout.txt")

        result = validate_workout(workout_file.read_text())

        # Afficher warnings
        for warning in result.warnings:
            print(f"⚠️  {warning}")

    CLI validation::

        # Validate all workouts in directory
        poetry run validate-workouts --dir workouts/S073/

        # Validate single file
        poetry run validate-workouts --file S073-01-workout.txt

Author: Stéphane Jouve
Created: 2024-11-XX
Updated: 2025-12-26 (Standardization Prompt 3 Priority 2)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""
import re

from magma_cycling.utils.cli import cli_main


class IntervalsFormatValidator:
    """Validateur format Intervals.icu."""

    # Patterns validation
    REPETITION_PATTERN = r"^\s*(\d+)x\s*$"  # "3x" seul sur ligne
    SECTION_WITH_REP_PATTERN = r"^(.*?)\s+(\d+x)\s*$"  # "Main set 3x"
    INTERVAL_PATTERN = r"^\s*-\s+\d+[msh].*$"  # "- 10m 90% 85rpm"
    MARKDOWN_PATTERN = r"\*\*|###|`|__|~~"  # Markdown interdit
    INVALID_DURATION_PATTERN = r"\d+(?:min|sec|hr|hours?|mins|secs)\b"

    # Sections valides
    VALID_SECTIONS = ["Warmup", "Main set", "Cooldown", "Block"]
    SECTION_TITLE_PATTERN = re.compile(
        r"^(Warmup|Main\s+set|Cooldown|Block)(\s+\d+x)?\.?\s*$", re.IGNORECASE
    )

    def __init__(self):
        """Initialize intervals format validator."""
        self.errors = []

        self.warnings = []

    def validate_workout(self, workout_text: str) -> tuple[bool, list[str], list[str]]:
        """
        Validate un workout complet.

        Args:
            workout_text: Texte workout à valider

        Returns:
            Tuple (is_valid, errors, warnings).
        """
        self.errors = []

        self.warnings = []

        lines = workout_text.split("\n")

        # Check 1: Pas de markdown
        if re.search(self.MARKDOWN_PATTERN, workout_text):
            self.errors.append("Format contient du markdown (**, ###, etc.)")

        # Check 2: Structure blocs répétés
        self._check_repetition_format(lines)

        # Check 3: Format intervalles
        self._check_interval_format(lines)

        # Check 4: Structure minimale
        self._check_minimal_structure(lines)

        # Check 5: Warmup/Cooldown mono-bloc sans justification
        self._check_warmup_cooldown_ramp(lines)

        return (len(self.errors) == 0, self.errors, self.warnings)

    def _check_repetition_format(self, lines: list[str]):
        """
        Verify format blocs répétés.

        Format attendu:
            Main set 3x
            - 10m 90%

        Format INCORRECT:
            Main set
            - 3x 10m 90%

            Test capacité 3x  (si "Test capacité" n'est pas section valide)
        """
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Détecter répétition seule (ex: "3x")
            if re.match(self.REPETITION_PATTERN, stripped):
                self.errors.append(
                    f"Ligne {i + 1}: Répétition '{stripped}' seule. "
                    f"Doit être sur ligne section (ex: 'Main set 3x')"
                )

            # Détecter répétition dans intervalle (ex: "- 3x 10m 90%")
            if stripped.startswith("-") and re.search(r"\b\d+x\b", stripped):
                self.errors.append(
                    f"Ligne {i + 1}: Répétition dans intervalle '{stripped}'. "
                    f"Format incorrect. Utiliser 'Main set Nx' avant le bloc."
                )

            # Détecter section avec répétition
            match = re.match(self.SECTION_WITH_REP_PATTERN, stripped)
            if match:
                section_name = match.group(1).strip()
                repetition = match.group(2)

                # Vérifier si section valide
                is_valid_section = any(valid in section_name for valid in self.VALID_SECTIONS)

                if not is_valid_section:
                    self.warnings.append(
                        f"Ligne {i + 1}: Section '{section_name} {repetition}' "
                        f"non standard. Sections valides: {', '.join(self.VALID_SECTIONS)}"
                    )

    def _check_interval_format(self, lines: list[str]):
        """
        Verify format lignes intervalles.

        Format attendu: "- [durée] [intensité] [cadence]"
        Exemples: "- 10m 90% 85rpm", "- 5m ramp 50-65%"
        """
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Ignorer lignes vides et sections
            if not stripped or not stripped.startswith("-"):
                continue

            # Vérifier suffixes de durée invalides (min, sec, hr, etc.)
            invalid_match = re.search(self.INVALID_DURATION_PATTERN, stripped)
            if invalid_match:
                self.errors.append(
                    f"Ligne {i + 1}: Durée invalide '{invalid_match.group()}'. "
                    f"Utiliser s, m ou h (ex: 5m, 30s, 2h)"
                )

            # Vérifier format ramp (tiret obligatoire entre bornes)
            if re.search(r"\bramp\b", stripped, re.IGNORECASE):
                if not re.search(r"\bramp\s+\d+-\d+%", stripped, re.IGNORECASE):
                    self.errors.append(
                        f"Ligne {i + 1}: Format ramp invalide dans '{stripped}'. "
                        f"Format attendu: 'ramp XX-YY%' (ex: 'ramp 50-65%')"
                    )

            # Vérifier présence durée
            if not re.search(r"\d+[msh]", stripped):
                self.warnings.append(f"Ligne {i + 1}: Aucune durée détectée dans '{stripped}'")

    def _check_minimal_structure(self, lines: list[str]):
        """Verify presence of at least one interval line."""
        has_interval = any(re.match(self.INTERVAL_PATTERN, line) for line in lines)
        if not has_interval:
            self.errors.append(
                "Aucune ligne d'intervalle détectée "
                "(format attendu: '- Xm Y% Zrpm'). "
                "Le texte libre n'est pas un format workout valide."
            )

    def _parse_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Parse workout text into named sections."""
        sections = {}
        current = None
        for line in lines:
            stripped = line.strip()
            match = self.SECTION_TITLE_PATTERN.match(stripped)
            if match:
                current = match.group(1).strip().lower().replace(" ", "_")
                sections[current] = []
            elif current is not None:
                sections[current].append(stripped)
        return sections

    def _check_warmup_cooldown_ramp(self, lines: list[str]):
        """Detect mono-bloc warmup/cooldown without justification."""
        sections = self._parse_sections(lines)

        for section_key, label in [("warmup", "Warmup"), ("cooldown", "Cooldown")]:
            if section_key not in sections:
                continue
            section_lines = sections[section_key]

            interval_lines = [ln for ln in section_lines if re.match(self.INTERVAL_PATTERN, ln)]
            if len(interval_lines) != 1:
                continue

            has_justification = any(ln.startswith("\u2699\ufe0f") for ln in section_lines)
            if has_justification:
                continue

            intensity = ""
            pct_match = re.search(r"(\d+(?:-\d+)?%)", interval_lines[0])
            if pct_match:
                intensity = pct_match.group(1)

            if label == "Warmup":
                self.warnings.append(
                    f"{label} mono-bloc d\u00e9tect\u00e9 (1 palier \u00e0 {intensity}). "
                    f"Ramp progressive recommand\u00e9e (3 paliers min). "
                    f"Si intentionnel, ajouter une ligne \u2699\ufe0f avec la justification."
                )
            else:
                self.warnings.append(
                    f"{label} mono-bloc d\u00e9tect\u00e9 (1 palier \u00e0 {intensity}). "
                    f"Ramp descendante recommand\u00e9e. "
                    f"Si intentionnel, ajouter une ligne \u2699\ufe0f avec la justification."
                )

    def fix_warmup_cooldown(self, workout_text: str) -> str:
        """Replace mono-bloc warmup/cooldown with 3-step ramp."""
        lines = workout_text.split("\n")
        sections = self._parse_sections(lines)
        result = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            match = self.SECTION_TITLE_PATTERN.match(stripped)
            if match:
                section_key = match.group(1).strip().lower().replace(" ", "_")
                if section_key in ("warmup", "cooldown") and section_key in sections:
                    section_lines = sections[section_key]
                    intervals = [ln for ln in section_lines if re.match(self.INTERVAL_PATTERN, ln)]
                    has_just = any(ln.startswith("\u2699\ufe0f") for ln in section_lines)
                    if len(intervals) == 1 and not has_just:
                        result.append(lines[i])
                        ramp = self._generate_ramp(intervals[0], section_key == "cooldown")
                        # Skip original section content
                        i += 1
                        while i < len(lines):
                            s = lines[i].strip()
                            if self.SECTION_TITLE_PATTERN.match(s) or (
                                not s
                                and i + 1 < len(lines)
                                and self.SECTION_TITLE_PATTERN.match(lines[i + 1].strip())
                            ):
                                break
                            i += 1
                        for rl in ramp:
                            result.append(rl)
                        result.append("")
                        continue
            result.append(lines[i])
            i += 1
        return "\n".join(result)

    @staticmethod
    def _generate_ramp(interval_line: str, descending: bool) -> list[str]:
        """Generate a 3-step ramp from a mono-bloc interval line."""
        dur_match = re.search(r"(\d+)([msh])", interval_line)
        pct_match = re.search(r"(\d+)%", interval_line)
        rpm_match = re.search(r"(\d+)rpm", interval_line)

        total_dur = int(dur_match.group(1)) if dur_match else 15
        dur_unit = dur_match.group(2) if dur_match else "m"
        target_pct = int(pct_match.group(1)) if pct_match else 65
        rpm_str = f" {rpm_match.group(0)}" if rpm_match else ""

        d1 = total_dur // 3
        d2 = total_dur // 3
        d3 = total_dur - d1 - d2

        base_pct = min(50, target_pct - 10)
        mid_pct = (base_pct + target_pct) // 2

        if descending:
            return [
                f"- {d1}{dur_unit} {target_pct}%{rpm_str}",
                f"- {d2}{dur_unit} {mid_pct}%{rpm_str}",
                f"- {d3}{dur_unit} {base_pct}%{rpm_str}",
            ]
        return [
            f"- {d1}{dur_unit} {base_pct}%{rpm_str}",
            f"- {d2}{dur_unit} {mid_pct}%{rpm_str}",
            f"- {d3}{dur_unit} {target_pct}%{rpm_str}",
        ]

    def fix_repetition_format(self, workout_text: str) -> str:
        """
        Corriger automatiquement format répétitions.

        Transformations:
        - "Test capacité 3x" → "Main set 3x" (si pas section valide)
        - "- 3x 10m 90%" → Erreur (ne peut pas corriger automatiquement)
        """
        lines = workout_text.split("\n")

        corrected = []
        errors_found = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Détecter répétition dans intervalle
            if stripped.startswith("-") and re.search(r"\b(\d+)x\b", stripped):
                errors_found.append(
                    f"Ligne {i + 1}: Impossible de corriger automatiquement "
                    f"'{stripped}'. Restructurer manuellement."
                )
                corrected.append(line)
                continue

            # Détecter section non standard avec répétition
            match = re.match(self.SECTION_WITH_REP_PATTERN, stripped)
            if match:
                section_name = match.group(1).strip()
                repetition = match.group(2)

                # Si section non standard, remplacer par "Main set"
                is_valid_section = any(valid in section_name for valid in self.VALID_SECTIONS)

                if not is_valid_section:
                    corrected_line = f"Main set {repetition}"
                    corrected.append(corrected_line)
                    print(f"⚠️  Ligne {i + 1} corrigée: " f"'{stripped}' → '{corrected_line}'")
                    continue

            # Ligne OK
            corrected.append(line)

        if errors_found:
            print("\n❌ ERREURS NON CORRIGEABLES:")
            for error in errors_found:
                print(f"   {error}")

        return "\n".join(corrected)

    def generate_example_workouts(self) -> dict:
        """
        Generate exemples workouts corrects.

        Returns:
            Dict avec exemples valides.
        """
        return {
            "simple": """Warmup.

- 10m ramp 50-65% 85rpm

Main set
- 20m 75% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm.""",
            "repeated_block": """Warmup.

- 10m ramp 50-75% 85rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 75-50% 85rpm.""",
            "multiple_blocks": """Warmup.

- 15m ramp 50-75% 85-90rpm

Main set 2x
- 5m 110% 95rpm
- 3m 55% 85rpm

Block 3x
- 1m 120% 100rpm
- 2m 60% 85rpm

Cooldown
- 12m ramp 75-50% 85rpm.""",
        }


@cli_main
def main():
    """Test du validateur."""
    validator = IntervalsFormatValidator()

    # Test cas invalide 1
    print("=" * 70)
    print("TEST 1: Format incorrect (répétition dans intervalle)")
    print("=" * 70)

    invalid1 = """Warmup.

- 10m ramp 50-65%

Main set
- 3x 10m 90%
- 2m 60%

Cooldown
- 10m ramp 65-50%."""
    is_valid, errors, warnings = validator.validate_workout(invalid1)

    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    print()

    # Test cas invalide 2
    print("=" * 70)
    print("TEST 2: Format incorrect (section non standard avec répétition)")
    print("=" * 70)

    invalid2 = """Warmup.

- 10m ramp 50-65%

Test capacité 3x
- 5m 70-75%
- 3m 60%

Cooldown
- 10m ramp 65-50%."""
    is_valid, errors, warnings = validator.validate_workout(invalid2)

    print(f"Valid: {is_valid}")
    print(f"Warnings: {warnings}")

    print("\n🔧 CORRECTION AUTOMATIQUE:")
    corrected = validator.fix_repetition_format(invalid2)
    print(corrected)
    print()

    # Test cas valide
    print("=" * 70)
    print("TEST 3: Format correct")
    print("=" * 70)

    valid = """Warmup.

- 10m ramp 50-75% 85rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 75-50% 85rpm."""
    is_valid, errors, warnings = validator.validate_workout(valid)

    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    print()

    # Exemples
    print("=" * 70)
    print("EXEMPLES WORKOUTS VALIDES")
    print("=" * 70)
    examples = validator.generate_example_workouts()
    for name, workout in examples.items():
        print(f"\n### {name.upper()}:")
        print(workout)
        print()


if __name__ == "__main__":
    main()  # pragma: no cover
