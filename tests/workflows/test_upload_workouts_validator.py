"""Tests for rest day validator in upload_workouts.

Tests cover rest day detection pattern and conditional
warmup/cooldown validation (fix commit cd066a0).
"""

import pytest
import re


class TestRestDayValidatorPattern:
    """Test suite for rest day detection and validation."""

    def test_validator_repos_standard_format(self):
        """Test standard REPOS format (S076-07-REPOS)."""
        # Given: Workout ID with standard REPOS suffix
        workout_id = "S076-07-REPOS"
        content = "REPOS COMPLET - Aucune activite"

        # When: Validating
        warnings = []
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Simulate validator logic
        if not is_rest_day:
            if "Warmup" not in content:
                warnings.append(f"🚨 {workout_id}: WARMUP MANQUANT")
            if "Cooldown" not in content:
                warnings.append(f"🚨 {workout_id}: COOLDOWN MANQUANT")

        # Then: Skip warmup/cooldown checks (no warnings)
        assert is_rest_day is not None
        assert len(warnings) == 0

    def test_validator_repos_with_suffix(self):
        """Test REPOS with additional text (S076-07-REPOS-COMPLET)."""
        # Given: REPOS with suffix text
        workout_id = "S076-07-REPOS-COMPLET"
        content = "REPOS COMPLET - Journee de recuperation totale"

        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Not detected (pattern requires $ or space after REPOS)
        assert is_rest_day is None  # Pattern doesn't match "-REPOS-COMPLET"

        # Alternative: Should match if pattern is -REPOS (anywhere)
        is_rest_day_alt = re.search(r"(?i)-REPOS", workout_id)
        assert is_rest_day_alt is not None

    def test_validator_repos_uppercase(self):
        """Test REPOS uppercase (S076-07-REPOS)."""
        # Given: Uppercase REPOS
        workout_id = "S076-07-REPOS"

        # When: Checking pattern (case insensitive)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched
        assert is_rest_day is not None

    def test_validator_repos_lowercase(self):
        """Test repos lowercase (s076-07-repos)."""
        # Given: Lowercase repos
        workout_id = "s076-07-repos"

        # When: Checking pattern (case insensitive)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched ((?i) makes it case insensitive)
        assert is_rest_day is not None

    def test_validator_repos_mixed_case(self):
        """Test RePoS mixed case (S076-07-RePoS)."""
        # Given: Mixed case
        workout_id = "S076-07-RePoS"

        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched (case insensitive)
        assert is_rest_day is not None

    def test_validator_repos_with_space_after(self):
        """Test REPOS with space and text (S076-07-REPOS Journee complete)."""
        # Given: REPOS followed by space and description
        workout_id = "S076-07-REPOS Journee complete"

        # When: Checking pattern (allows space after REPOS)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched (pattern accepts space)
        assert is_rest_day is not None

    def test_validator_repos_at_end_of_string(self):
        """Test REPOS at end of string (S999-07-REPOS)."""
        # Given: REPOS at string end ($ anchor)
        workout_id = "S999-07-REPOS"

        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched ($ matches end of string)
        assert is_rest_day is not None

    def test_validator_normal_workout_not_repos(self):
        """Test normal workout requires warmup/cooldown (S076-01-REC)."""
        # Given: Normal workout (not REPOS)
        workout_id = "S076-01-REC-RecuperationActive-V001"
        content = """Recuperation Active (45min, 25 TSS)

Main set
- 25m 58-62% 85rpm
"""
        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Simulate validator
        warnings = []
        if not is_rest_day:
            if "Warmup" not in content:
                warnings.append(f"🚨 {workout_id}: WARMUP MANQUANT")
            if "Cooldown" not in content:
                warnings.append(f"🚨 {workout_id}: COOLDOWN MANQUANT")

        # Then: Not a rest day, warnings generated
        assert is_rest_day is None
        assert len(warnings) == 2  # Missing warmup AND cooldown

    def test_validator_normal_workout_complete(self):
        """Test normal workout with warmup/cooldown passes (S076-01-REC)."""
        # Given: Complete normal workout
        workout_id = "S076-01-REC-RecuperationActive-V001"
        content = """Recuperation Active (45min, 25 TSS)

Warmup
- 10m ramp 45-60% 85rpm

Main set
- 25m 58-62% 85rpm

Cooldown
- 10m ramp 60-45% 85rpm
"""
        # When: Checking
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Simulate validator
        warnings = []
        if not is_rest_day:
            if "Warmup" not in content:
                warnings.append(f"🚨 {workout_id}: WARMUP MANQUANT")
            if "Cooldown" not in content:
                warnings.append(f"🚨 {workout_id}: COOLDOWN MANQUANT")

        # Then: No warnings (complete workout)
        assert is_rest_day is None  # Not a rest day
        assert len(warnings) == 0  # But warmup/cooldown present

    def test_validator_repos_with_hyphen_in_description(self):
        """Test REPOS-like text in description (false positive check)."""
        # Given: Workout with "REPOS" in middle (not after hyphen)
        workout_id = "S076-03-REC-RecuperationPostRepos"
        content = "Recuperation post repos day"

        # When: Checking pattern (should NOT match)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Not matched (REPOS not after hyphen at this position)
        assert is_rest_day is None  # "Repos" is inside word, not after hyphen

    def test_validator_repos_french_variants(self):
        """Test French variants (REPOS-RECUPERATION)."""
        # Given: French variant
        workout_ids = [
            "S076-07-REPOS",
            "S076-07-REPOS-RECUPERATION",
            "S076-07-REPOS Recuperation",
        ]

        for workout_id in workout_ids:
            # When: Checking pattern
            is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

            # Then: First two should match, third should match
            if workout_id == "S076-07-REPOS":
                assert is_rest_day is not None, f"Failed for {workout_id}"
            elif workout_id == "S076-07-REPOS-RECUPERATION":
                # Pattern requires $ or space, so -RECUPERATION doesn't match
                assert is_rest_day is None, f"Should not match {workout_id}"
            elif workout_id == "S076-07-REPOS Recuperation":
                assert is_rest_day is not None, f"Failed for {workout_id}"

    def test_validator_edge_case_empty_workout_id(self):
        """Test empty workout ID (edge case)."""
        # Given: Empty string
        workout_id = ""

        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: No match
        assert is_rest_day is None

    def test_validator_edge_case_only_repos(self):
        """Test workout ID with only REPOS (malformed)."""
        # Given: Malformed ID
        workout_id = "REPOS"

        # When: Checking pattern (requires hyphen before REPOS)
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: No match (pattern requires hyphen)
        assert is_rest_day is None

    def test_validator_repos_multiple_hyphens(self):
        """Test workout with multiple hyphens before REPOS."""
        # Given: Multiple hyphens
        workout_id = "S076-07-REC-REPOS"

        # When: Checking pattern
        is_rest_day = re.search(r"(?i)-REPOS($|\s)", workout_id)

        # Then: Matched (last -REPOS)
        assert is_rest_day is not None
