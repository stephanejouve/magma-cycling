"""Validation mixin for WorkoutUploader."""

import re


class ValidationMixin:
    """Validation notation workouts."""

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
            if any(re.match(r"^\d+[mx]?\s", line) for line in lines_after):
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
        # Skip validation for rest days (REPOS, ReposComplet, etc.)
        # Match both formats: -REC-Repos* (old) and -REPOS (new)
        is_rest_day = re.search(r"(?i)(-REC-Repos|-REPOS)", workout_id)

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
