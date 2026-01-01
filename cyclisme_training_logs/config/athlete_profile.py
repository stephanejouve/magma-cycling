"""
Athlete Profile Configuration Module.

Centralized athlete profile configuration loaded from environment variables.
Provides type-safe access to athlete characteristics that influence training
thresholds and recommendations.

Examples:
    Load athlete profile from environment::

        profile = AthleteProfile.from_env()
        print(f"Age: {profile.age}, FTP: {profile.ftp}W")
        print(f"Recovery: {profile.recovery_capacity}")

    Check sleep dependency::

        if profile.sleep_dependent:
            print("Athlete performance is sleep-dependent")

Author: Claude Code
Created: 2026-01-01
"""

import os
from typing import Literal
from pydantic import BaseModel, Field, ValidationError


class AthleteProfile(BaseModel):
    """
    Athlete profile with training-relevant characteristics.

    Attributes:
        age: Athlete age in years (affects recovery and threshold recommendations)
        category: Competition category (affects training zones and load recommendations)
        recovery_capacity: Recovery ability (affects overtraining thresholds)
        sleep_dependent: Whether performance is strongly sleep-dependent
        ftp: Functional Threshold Power in watts
        weight: Athlete weight in kg
    """

    age: int = Field(gt=0, le=120, description="Athlete age in years")
    category: Literal["junior", "senior", "master"] = Field(
        description="Competition category"
    )
    recovery_capacity: Literal["normal", "good", "exceptional"] = Field(
        description="Recovery ability level"
    )
    sleep_dependent: bool = Field(
        description="Whether performance is strongly sleep-dependent"
    )
    ftp: int = Field(gt=0, description="Functional Threshold Power in watts")
    weight: float = Field(gt=0, description="Athlete weight in kg")

    @classmethod
    def from_env(cls) -> "AthleteProfile":
        """
        Load athlete profile from environment variables.

        Environment Variables:
            ATHLETE_AGE: Age in years (int)
            ATHLETE_CATEGORY: Competition category (junior/senior/master)
            ATHLETE_RECOVERY_CAPACITY: Recovery ability (normal/good/exceptional)
            ATHLETE_SLEEP_DEPENDENT: Sleep dependency (true/false)
            ATHLETE_FTP: Functional Threshold Power in watts (int)
            ATHLETE_WEIGHT: Weight in kg (float)

        Returns:
            AthleteProfile: Configured athlete profile

        Raises:
            ValueError: If required environment variables are missing or invalid
            ValidationError: If values don't meet validation constraints

        Examples:
            >>> profile = AthleteProfile.from_env()
            >>> print(f"Category: {profile.category}, Age: {profile.age}")
        """
        try:
            age = int(os.getenv("ATHLETE_AGE", "0"))
            category = os.getenv("ATHLETE_CATEGORY", "").lower()
            recovery = os.getenv("ATHLETE_RECOVERY_CAPACITY", "").lower()
            sleep_dep_str = os.getenv("ATHLETE_SLEEP_DEPENDENT", "false").lower()
            ftp = int(os.getenv("ATHLETE_FTP", "0"))
            weight = float(os.getenv("ATHLETE_WEIGHT", "0"))

            # Parse boolean
            sleep_dependent = sleep_dep_str in ["true", "1", "yes", "on"]

            # Validate required fields
            if age == 0:
                raise ValueError("ATHLETE_AGE environment variable is required")
            if not category:
                raise ValueError("ATHLETE_CATEGORY environment variable is required")
            if not recovery:
                raise ValueError(
                    "ATHLETE_RECOVERY_CAPACITY environment variable is required"
                )
            if ftp == 0:
                raise ValueError("ATHLETE_FTP environment variable is required")
            if weight == 0:
                raise ValueError("ATHLETE_WEIGHT environment variable is required")

            return cls(
                age=age,
                category=category,  # type: ignore
                recovery_capacity=recovery,  # type: ignore
                sleep_dependent=sleep_dependent,
                ftp=ftp,
                weight=weight,
            )

        except ValidationError as e:
            raise ValueError(f"Invalid athlete profile configuration: {e}") from e
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(
                    f"Invalid numeric value in athlete profile configuration: {e}"
                ) from e
            raise

    def is_master_athlete(self) -> bool:
        """
        Check if athlete is in master category.

        Returns:
            bool: True if master category
        """
        return self.category == "master"

    def has_exceptional_recovery(self) -> bool:
        """
        Check if athlete has exceptional recovery capacity.

        Returns:
            bool: True if exceptional recovery
        """
        return self.recovery_capacity == "exceptional"

    def get_power_to_weight_ratio(self) -> float:
        """
        Calculate power-to-weight ratio (FTP/kg).

        Returns:
            float: FTP divided by weight in kg

        Examples:
            >>> profile = AthleteProfile(age=54, category="master",
            ...     recovery_capacity="exceptional", sleep_dependent=True,
            ...     ftp=240, weight=72.5)
            >>> profile.get_power_to_weight_ratio()
            3.31
        """
        return round(self.ftp / self.weight, 2)
