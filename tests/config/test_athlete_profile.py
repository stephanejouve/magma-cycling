"""Tests for athlete_profile module (Sprint R2)."""

import pytest

from cyclisme_training_logs.config.athlete_profile import AthleteProfile


class TestAthleteProfileFromEnv:
    """Tests for AthleteProfile.from_env() method."""

    def test_from_env_with_all_fields(self, monkeypatch):
        """Test loading profile with all environment variables set."""
        monkeypatch.setenv("ATHLETE_AGE", "54")
        monkeypatch.setenv("ATHLETE_CATEGORY", "master")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "exceptional")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "true")
        monkeypatch.setenv("ATHLETE_FTP", "240")
        monkeypatch.setenv("ATHLETE_WEIGHT", "72.5")

        profile = AthleteProfile.from_env()

        assert profile.age == 54
        assert profile.category == "master"
        assert profile.recovery_capacity == "exceptional"
        assert profile.sleep_dependent is True
        assert profile.ftp == 240
        assert profile.weight == 72.5

    def test_from_env_sleep_dependent_variations(self, monkeypatch):
        """Test boolean parsing for sleep_dependent."""
        base_env = {
            "ATHLETE_AGE": "54",
            "ATHLETE_CATEGORY": "master",
            "ATHLETE_RECOVERY_CAPACITY": "exceptional",
            "ATHLETE_FTP": "240",
            "ATHLETE_WEIGHT": "72.5",
        }

        # Test various true values
        for true_value in ["true", "True", "TRUE", "1", "yes", "on"]:
            for key, value in base_env.items():
                monkeypatch.setenv(key, value)
            monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", true_value)

            profile = AthleteProfile.from_env()
            assert profile.sleep_dependent is True

        # Test false values
        for false_value in ["false", "False", "FALSE", "0", "no", "off"]:
            for key, value in base_env.items():
                monkeypatch.setenv(key, value)
            monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", false_value)

            profile = AthleteProfile.from_env()
            assert profile.sleep_dependent is False

    def test_from_env_missing_age(self, monkeypatch):
        """Test error when ATHLETE_AGE is missing."""
        monkeypatch.delenv("ATHLETE_AGE", raising=False)  # Explicitly remove ATHLETE_AGE
        monkeypatch.setenv("ATHLETE_CATEGORY", "master")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "exceptional")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "true")
        monkeypatch.setenv("ATHLETE_FTP", "240")
        monkeypatch.setenv("ATHLETE_WEIGHT", "72.5")

        with pytest.raises(ValueError, match="ATHLETE_AGE.*required"):
            AthleteProfile.from_env()

    def test_from_env_invalid_category(self, monkeypatch):
        """Test error when category is invalid."""
        monkeypatch.setenv("ATHLETE_AGE", "54")
        monkeypatch.setenv("ATHLETE_CATEGORY", "invalid")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "exceptional")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "true")
        monkeypatch.setenv("ATHLETE_FTP", "240")
        monkeypatch.setenv("ATHLETE_WEIGHT", "72.5")

        with pytest.raises(ValueError):
            AthleteProfile.from_env()

    def test_from_env_invalid_age(self, monkeypatch):
        """Test error when age is invalid."""
        monkeypatch.setenv("ATHLETE_AGE", "150")  # Too old
        monkeypatch.setenv("ATHLETE_CATEGORY", "master")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "exceptional")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "true")
        monkeypatch.setenv("ATHLETE_FTP", "240")
        monkeypatch.setenv("ATHLETE_WEIGHT", "72.5")

        with pytest.raises(ValueError):
            AthleteProfile.from_env()


class TestAthleteProfileMethods:
    """Tests for AthleteProfile helper methods."""

    def test_is_master_athlete(self):
        """Test is_master_athlete method."""
        master = AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            weight=72.5,
        )
        assert master.is_master_athlete() is True

        senior = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            weight=70.0,
        )
        assert senior.is_master_athlete() is False

    def test_has_exceptional_recovery(self):
        """Test has_exceptional_recovery method."""
        exceptional = AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            weight=72.5,
        )
        assert exceptional.has_exceptional_recovery() is True

        normal = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            weight=70.0,
        )
        assert normal.has_exceptional_recovery() is False

    def test_get_power_to_weight_ratio(self):
        """Test power-to-weight ratio calculation."""
        profile = AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            weight=72.5,
        )

        ratio = profile.get_power_to_weight_ratio()
        assert ratio == pytest.approx(3.31, abs=0.01)

    def test_create_with_pydantic_validation(self):
        """Test Pydantic validation on direct creation."""
        # Valid creation
        profile = AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            weight=72.5,
        )
        assert profile.age == 54

        # Invalid age (negative)
        with pytest.raises(ValueError):
            AthleteProfile(
                age=-5,
                category="master",
                recovery_capacity="exceptional",
                sleep_dependent=True,
                ftp=240,
                weight=72.5,
            )

        # Invalid FTP (zero)
        with pytest.raises(ValueError):
            AthleteProfile(
                age=54,
                category="master",
                recovery_capacity="exceptional",
                sleep_dependent=True,
                ftp=0,
                weight=72.5,
            )
