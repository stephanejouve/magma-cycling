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
            age=52,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            ftp_target=260,
            weight=72.5,
        )
        assert master.is_master_athlete() is True

        senior = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            ftp_target=300,
            weight=70.0,
        )
        assert senior.is_master_athlete() is False

    def test_has_exceptional_recovery(self):
        """Test has_exceptional_recovery method."""
        exceptional = AthleteProfile(
            age=52,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            ftp_target=260,
            weight=72.5,
        )
        assert exceptional.has_exceptional_recovery() is True

        normal = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            ftp_target=300,
            weight=70.0,
        )
        assert normal.has_exceptional_recovery() is False

    def test_get_power_to_weight_ratio(self):
        """Test power-to-weight ratio calculation."""
        profile = AthleteProfile(
            age=52,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            ftp_target=260,
            weight=72.5,
        )

        ratio = profile.get_power_to_weight_ratio()
        assert ratio == pytest.approx(3.31, abs=0.01)

    def test_create_with_pydantic_validation(self):
        """Test Pydantic validation on direct creation."""
        # Valid creation

        profile = AthleteProfile(
            age=52,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=240,
            ftp_target=260,
            weight=72.5,
        )
        assert profile.age == 52

        # Invalid age (negative)
        with pytest.raises(ValueError):
            AthleteProfile(
                age=-5,
                category="master",
                recovery_capacity="exceptional",
                sleep_dependent=True,
                ftp=240,
                ftp_target=260,
                weight=72.5,
            )

        # Invalid FTP (zero)
        with pytest.raises(ValueError):
            AthleteProfile(
                age=52,
                category="master",
                recovery_capacity="exceptional",
                sleep_dependent=True,
                ftp=0,
                ftp_target=260,
                weight=72.5,
            )


class TestAthleteProfileBiomechanics:
    """Tests for biomechanics fields (Grappe integration)."""

    def test_default_biomechanics_fields(self):
        """Test default values for biomechanics fields."""
        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            ftp_target=300,
            weight=70.0,
        )

        assert profile.profil_fibres == "mixte"
        assert profile.cadence_offset == 0

    def test_profil_fibres_explosif(self):
        """Test explosif fiber profile."""
        profile = AthleteProfile(
            age=28,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=320,
            ftp_target=340,
            weight=68.0,
            profil_fibres="explosif",
        )

        assert profile.profil_fibres == "explosif"

    def test_profil_fibres_endurant(self):
        """Test endurant fiber profile."""
        profile = AthleteProfile(
            age=42,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=250,
            ftp_target=270,
            weight=73.0,
            profil_fibres="endurant",
        )

        assert profile.profil_fibres == "endurant"

    def test_invalid_profil_fibres(self):
        """Test invalid fiber profile."""
        with pytest.raises(ValueError):
            AthleteProfile(
                age=35,
                category="senior",
                recovery_capacity="normal",
                sleep_dependent=False,
                ftp=280,
                ftp_target=300,
                weight=70.0,
                profil_fibres="invalid",  # type: ignore
            )

    def test_cadence_offset_positive(self):
        """Test positive cadence offset."""
        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            ftp_target=300,
            weight=70.0,
            cadence_offset=10,
        )

        assert profile.cadence_offset == 10

    def test_cadence_offset_negative(self):
        """Test negative cadence offset."""
        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            ftp_target=300,
            weight=70.0,
            cadence_offset=-5,
        )

        assert profile.cadence_offset == -5

    def test_cadence_offset_out_of_range_high(self):
        """Test cadence offset too high."""
        with pytest.raises(ValueError):
            AthleteProfile(
                age=35,
                category="senior",
                recovery_capacity="normal",
                sleep_dependent=False,
                ftp=280,
                ftp_target=300,
                weight=70.0,
                cadence_offset=20,  # Above max 15
            )

    def test_cadence_offset_out_of_range_low(self):
        """Test cadence offset too low."""
        with pytest.raises(ValueError):
            AthleteProfile(
                age=35,
                category="senior",
                recovery_capacity="normal",
                sleep_dependent=False,
                ftp=280,
                ftp_target=300,
                weight=70.0,
                cadence_offset=-20,  # Below min -15
            )

    def test_from_env_with_biomechanics_fields(self, monkeypatch):
        """Test loading profile with biomechanics fields from env."""
        monkeypatch.setenv("ATHLETE_AGE", "35")
        monkeypatch.setenv("ATHLETE_CATEGORY", "senior")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "normal")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "false")
        monkeypatch.setenv("ATHLETE_FTP", "280")
        monkeypatch.setenv("ATHLETE_WEIGHT", "70.0")
        monkeypatch.setenv("ATHLETE_PROFIL_FIBRES", "explosif")
        monkeypatch.setenv("ATHLETE_CADENCE_OFFSET", "5")

        profile = AthleteProfile.from_env()

        assert profile.profil_fibres == "explosif"
        assert profile.cadence_offset == 5

    def test_from_env_without_biomechanics_fields(self, monkeypatch):
        """Test loading profile without biomechanics fields uses defaults."""
        monkeypatch.setenv("ATHLETE_AGE", "35")
        monkeypatch.setenv("ATHLETE_CATEGORY", "senior")
        monkeypatch.setenv("ATHLETE_RECOVERY_CAPACITY", "normal")
        monkeypatch.setenv("ATHLETE_SLEEP_DEPENDENT", "false")
        monkeypatch.setenv("ATHLETE_FTP", "280")
        monkeypatch.setenv("ATHLETE_WEIGHT", "70.0")
        # Biomechanics fields not set

        profile = AthleteProfile.from_env()

        assert profile.profil_fibres == "mixte"  # Default
        assert profile.cadence_offset == 0  # Default
