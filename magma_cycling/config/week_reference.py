"""Week reference configuration with multi-season support.

Manages S001 reference dates for calculating week start dates across
multiple training seasons.
"""

import json
from datetime import datetime
from pathlib import Path


class WeekReferenceConfig:
    """Configuration for week numbering reference with multi-season support.

    Supports two config formats:
    1. Legacy (single season): {"week_reference": {"s001_date": "2024-08-05", ...}}
    2. Multi-season: {"week_reference": {"seasons": {...}}}

    Attributes:
        seasons: Dict of season configs {season_id: {s001_date, global_week_start, ...}}
        active_season: Current active season identifier
        config_path: Path to .config.json file

    Examples:
        >>> config = get_week_config()
        >>> ref_date, offset = config.get_reference_for_week("S075")
        >>> print(ref_date, offset)
        2026-01-05 0  # Season 2026, week 75 is its first week
    """

    def __init__(self, data_repo_path: Path | None = None):
        """Initialize week reference configuration.

        Args:
            data_repo_path: Path to data repository. If None, uses get_data_config().

        Raises:
            FileNotFoundError: If .config.json doesn't exist
            ValueError: If .config.json is invalid or missing required fields
        """
        if data_repo_path is None:
            from magma_cycling.config.data_repo import get_data_config

            data_config = get_data_config()
            data_repo_path = data_config.data_repo_path

        self.config_path = data_repo_path / ".config.json"

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Week reference config not found: {self.config_path}\n"
                f"Create it with multi-season support"
            )

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_path}: {e}") from e

        week_ref = config_data.get("week_reference")
        if not week_ref:
            raise ValueError(f"Missing 'week_reference' section in {self.config_path}")

        if "seasons" in week_ref:
            self.seasons = week_ref["seasons"]
            self.active_season = week_ref.get("active_season")

            if not self.seasons:
                raise ValueError(f"Empty 'seasons' in {self.config_path}")

            for season_id, season_data in self.seasons.items():
                if "s001_date" not in season_data:
                    raise ValueError(
                        f"Missing 's001_date' for season '{season_id}' in {self.config_path}"
                    )
                if "global_week_start" not in season_data:
                    raise ValueError(
                        f"Missing 'global_week_start' for season '{season_id}' in {self.config_path}"
                    )
                self._validate_date_format(season_data["s001_date"], season_id)
        else:
            s001_date = week_ref.get("s001_date")
            if not s001_date:
                raise ValueError(
                    f"Missing 's001_date' in week_reference section of {self.config_path}"
                )

            self._validate_date_format(s001_date, "legacy")

            self.seasons = {
                "legacy": {
                    "s001_date": s001_date,
                    "description": week_ref.get("description", ""),
                    "season": week_ref.get("season", "Unknown"),
                    "global_week_start": 1,
                    "global_week_end": None,
                }
            }
            self.active_season = "legacy"

    def _validate_date_format(self, date_str: str, season_id: str):
        """Validate date format (YYYY-MM-DD).

        Args:
            date_str: Date string to validate
            season_id: Season identifier for error messages

        Raises:
            ValueError: If date format is invalid
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format for season '{season_id}' in {self.config_path}: "
                f"'{date_str}' (expected YYYY-MM-DD)"
            ) from e

    def get_season_for_week(self, week_num: int) -> str:
        """Get season identifier for a given global week number.

        Args:
            week_num: Global week number (e.g., 75 for S075)

        Returns:
            Season identifier (e.g., "2026")

        Examples:
            >>> config = get_week_config()
            >>> config.get_season_for_week(50)
            '2024-2025'
            >>> config.get_season_for_week(75)
            '2026'
        """
        for season_id, season_data in self.seasons.items():
            start = season_data["global_week_start"]
            end = season_data.get("global_week_end")

            if end is None:
                if week_num >= start:
                    return season_id
            else:
                if start <= week_num <= end:
                    return season_id

        if self.active_season:
            return self.active_season
        return list(self.seasons.keys())[0]

    def get_reference_for_week(self, week_id: str) -> tuple:
        """Get reference date and week offset for a given week ID.

        Args:
            week_id: Week identifier (e.g., "S075")

        Returns:
            Tuple of (reference_date, weeks_offset)

        Examples:
            >>> config = get_week_config()
            >>> ref, offset = config.get_reference_for_week("S075")
            >>> print(ref, offset)
            2026-01-05 0
        """
        week_num = int(week_id[1:])

        season_id = self.get_season_for_week(week_num)
        season_data = self.seasons[season_id]

        reference_date = datetime.strptime(season_data["s001_date"], "%Y-%m-%d").date()

        season_start = season_data["global_week_start"]
        weeks_offset = week_num - season_start

        return (reference_date, weeks_offset)

    def get_s001_date_obj(self, week_id: str = "S001"):
        """Get S001 reference date for a given week's season.

        Args:
            week_id: Week identifier (default: "S001")

        Returns:
            datetime.date object for the season's S001 reference date

        Examples:
            >>> config = get_week_config()
            >>> config.get_s001_date_obj("S001")
            date(2024, 8, 5)
            >>> config.get_s001_date_obj("S075")
            date(2026, 1, 5)
        """
        ref_date, _ = self.get_reference_for_week(week_id)
        return ref_date


# Global week config instance
_week_config_instance: WeekReferenceConfig | None = None


def get_week_config() -> WeekReferenceConfig:
    """Get singleton instance of week reference config.

    Returns:
        WeekReferenceConfig instance

    Raises:
        FileNotFoundError: If .config.json doesn't exist
        ValueError: If .config.json is invalid

    Examples:
        >>> config = get_week_config()
        >>> print(config.s001_date)
        '2024-08-05'
    """
    global _week_config_instance

    if _week_config_instance is None:
        _week_config_instance = WeekReferenceConfig()
    return _week_config_instance


def reset_week_config():
    """Reset week config singleton (useful for tests).

    Examples:
        >>> reset_week_config()
        >>> config = get_week_config()  # Creates new instance
    """
    global _week_config_instance
    _week_config_instance = None
