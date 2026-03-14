"""Registry of known Zwift workout collections on whatsonzwift.com."""

KNOWN_COLLECTIONS: dict[str, str] = {
    # Workout categories (direct listings)
    "endurance": "Endurance (Z2 base building)",
    "sweet-spot": "Sweet Spot (88-93% FTP)",
    "threshold": "Threshold (FTP/seuil)",
    "vo2-max": "VO2 Max (high-intensity intervals)",
    "recovery": "Recovery (active recovery)",
    "sprinting": "Sprinting (sprint-specific)",
    "climbing": "Climbing (hill-specific training)",
    "ftp-tests": "FTP Tests (testing protocols)",
    # Duration-based collections
    "30-minutes-to-burn": "30 minutes to burn (short workouts)",
    "30-60-minutes-to-burn": "30-60 minutes to burn",
    "60-90-minutes-to-burn": "60-90 minutes to burn",
    "90plus-minutes-to-burn": "90+ minutes to burn (long workouts)",
    # Training plans
    "build-me-up": "Build Me Up (progressive loading)",
    "ftp-builder": "FTP Builder (structured training)",
    "active-offseason": "Active Offseason (recovery phase)",
    "gravel-grinder": "Gravel Grinder (endurance focus)",
    "gran-fondo": "Gran Fondo (endurance/distance)",
    "crit-crusher": "Crit Crusher (race prep)",
    "back-to-fitness": "Back To Fitness (return to form)",
    "zwift-camp-baseline": "Zwift Camp: Baseline (test workouts)",
}
