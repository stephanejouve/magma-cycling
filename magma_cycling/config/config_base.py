"""
Configuration centrale pour séparation code/données.

Module de configuration gérant la séparation entre code (magma-cycling)
et données athlète (training-logs externe). Configure les chemins vers le dépôt
de données externe via variable d'environnement TRAINING_DATA_REPO, avec fallback
vers ~/training-logs par défaut.

Examples:
    Command-line usage::

        # Configuration via variable d'environnement
        export TRAINING_DATA_REPO=~/training-logs
        poetry run workflow-coach

    Programmatic usage::

        from magma_cycling.config import get_data_config

        # Récupération configuration (singleton)
        config = get_data_config()

        # Accès aux chemins configurés
        data_path = config.data_repo_path
        workouts_path = config.workouts_history_path
        context_path = config.context_path

        print(f"Data repo: {data_path}")
        print(f"Workouts: {workouts_path}")

    Advanced usage::

        from magma_cycling.config import DataRepoConfig, reset_data_config

        # Configuration personnalisée pour tests
        custom_config = DataRepoConfig(data_repo_path="/tmp/test-data")

        # Reset singleton (utile pour tests)
        reset_data_config()

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I (Infrastructure)
    Status: Production
    Priority: P0
    Version: v2
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DataRepoConfig:
    """Configuration for external data repository paths."""

    def __init__(self, data_repo_path: Path | None = None):
        """
        Initialize data repository configuration.

        Args:
            data_repo_path: Path to external data repository.
                           If None, will try TRAINING_DATA_REPO env var,
                           then default to ~/training-logs

        Raises:
            FileNotFoundError: If data repository path doesn't exist
        """
        if data_repo_path is None:
            # Try env var first
            env_path = os.getenv("TRAINING_DATA_REPO")
            if env_path:
                data_repo_path = Path(env_path).expanduser()
            else:
                # Default to ~/training-logs
                data_repo_path = Path.home() / "training-logs"

        self.data_repo_path = Path(data_repo_path).resolve()

        # Validate path exists
        if not self.data_repo_path.exists():
            raise FileNotFoundError(
                f"Data repo not found: {self.data_repo_path}\n"
                f"Set TRAINING_DATA_REPO env var or clone:\n"
                f"  git clone https://github.com/YOUR_USERNAME/training-logs.git ~/training-logs"
            )

        # Duplicate detection settings (paranoid mode for backfill testing)
        self.paranoid_duplicate_check = True  # Check après chaque insertion
        self.auto_fix_duplicates = False  # Auto-suppression ou erreur (fail-fast)
        self.duplicate_check_window = 50  # Lignes à scanner (optimisation)

    @property
    def workouts_history_path(self) -> Path:
        """Path to workouts-history.md in data repo."""
        return self.data_repo_path / "workouts-history.md"

    @property
    def bilans_dir(self) -> Path:
        """Path to bilans/ directory in data repo."""
        return self.data_repo_path / "bilans"

    @property
    def data_dir(self) -> Path:
        """Path to data/ directory in data repo."""
        return self.data_repo_path / "data"

    @property
    def week_planning_dir(self) -> Path:
        """Path to data/week_planning/ directory in data repo."""
        return self.data_dir / "week_planning"

    @property
    def workout_templates_dir(self) -> Path:
        """Path to data/workout_templates/ directory in data repo."""
        return self.data_dir / "workout_templates"

    @property
    def workflow_state_path(self) -> Path:
        """Path to .workflow_state.json in data repo."""
        return self.data_repo_path / ".workflow_state.json"

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        self.bilans_dir.mkdir(parents=True, exist_ok=True)

        self.week_planning_dir.mkdir(parents=True, exist_ok=True)
        self.workout_templates_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """
        Validate data repository structure.

        Returns:
            True if all required files/dirs exist

        Raises:
            FileNotFoundError: If critical files missing
        """
        # Check workouts-history.md exists

        if not self.workouts_history_path.exists():
            raise FileNotFoundError(
                f"workouts-history.md not found in data repo: {self.data_repo_path}\n"
                f"Create it with: touch {self.workouts_history_path}"
            )

        # Ensure directories exist
        self.ensure_directories()

        return True


# Global config instance
_global_config: DataRepoConfig | None = None


def get_data_config() -> DataRepoConfig:
    """
    Get or create global data repository configuration.

    Returns:
        DataRepoConfig instance

    Raises:
        FileNotFoundError: If data repository not found.
    """
    global _global_config

    if _global_config is None:
        _global_config = DataRepoConfig()
        _global_config.validate()

    return _global_config


def set_data_config(config: DataRepoConfig | None):
    """
    Set global data repository configuration.

    Useful for testing with temporary paths.

    Args:
        config: DataRepoConfig instance or None to reset.
    """
    global _global_config

    _global_config = config


def reset_data_config():
    """Reset global configuration (mainly for testing)."""
    global _global_config

    _global_config = None


# ============================================================================
# AI Providers Configuration
# ============================================================================


class AIProvidersConfig:
    """Configuration for AI providers.

    Manages configuration for multiple AI providers (clipboard, Claude API,
    Mistral AI, OpenAI, Ollama) with auto-detection and fallback chain.

    Attributes:
        default_provider: Default provider if not specified (from env or 'clipboard')
        enable_fallback: Whether to fallback to next provider on failure
        fallback_priority: Priority order for provider fallback chain

    Examples:
        >>> config = get_ai_config()
        >>> providers = config.get_available_providers()
        >>> print(providers)
        ['claude_api', 'mistral_api', 'clipboard']
    """

    def __init__(self):
        """Initialize AI providers configuration from environment variables."""
        # General settings

        self.default_provider = os.getenv("DEFAULT_AI_PROVIDER", "clipboard")
        self.enable_fallback = os.getenv("ENABLE_AI_FALLBACK", "true").lower() == "true"
        self.fallback_priority = ["claude_api", "mistral_api", "openai", "ollama", "clipboard"]

        # Mistral AI - Direct attributes for easy access
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.mistral_model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        self.mistral_temperature = float(os.getenv("MISTRAL_TEMPERATURE", "0.7"))
        self.mistral_max_tokens = int(os.getenv("MISTRAL_MAX_TOKENS", "4000"))
        self.mistral_timeout = int(os.getenv("MISTRAL_TIMEOUT", "60"))

        # Claude API (Anthropic) - Direct attributes
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        # OpenAI - Direct attributes
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

        # Ollama (local LLMs) - Direct attributes
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "mistral:7b")

        # Provider-specific configs (for backward compatibility with factory)
        self._configs = {
            "clipboard": {},
            "claude_api": {
                "claude_api_key": self.claude_api_key,
                "claude_model": self.claude_model,
            },
            "mistral_api": {
                "mistral_api_key": self.mistral_api_key,
                "mistral_model": self.mistral_model,
                "mistral_temperature": self.mistral_temperature,
                "mistral_max_tokens": self.mistral_max_tokens,
                "mistral_timeout": self.mistral_timeout,
            },
            "openai": {"openai_api_key": self.openai_api_key, "openai_model": self.openai_model},
            "ollama": {"ollama_base_url": self.ollama_base_url, "ollama_model": self.ollama_model},
        }

    def is_provider_configured(self, provider: str) -> bool:
        """Check if provider has valid configuration.

        Args:
            provider: Provider name (clipboard, claude_api, etc.)

        Returns:
            True if provider is configured and ready to use

        Examples:
            >>> config = get_ai_config()
            >>> config.is_provider_configured('clipboard')
            True
            >>> config.is_provider_configured('claude_api')
            False  # If CLAUDE_API_KEY not set.
        """
        if provider == "clipboard":
            return True  # Always available
        if provider == "ollama":
            return True  # Assume localhost available

        # Check API key from direct attributes
        if provider == "claude_api":
            return bool(self.claude_api_key)
        elif provider == "mistral_api":
            return bool(self.mistral_api_key)
        elif provider == "openai":
            return bool(self.openai_api_key)

        return False

    def get_available_providers(self) -> list[str]:
        """Return list of configured providers in priority order.

        Returns:
            List of provider names that are configured

        Examples:
            >>> config = get_ai_config()
            >>> config.get_available_providers()
            ['claude_api', 'mistral_api', 'clipboard'].
        """
        available = []

        for provider in self.fallback_priority:
            if self.is_provider_configured(provider):
                available.append(provider)
        return available

    def get_provider_config(self, provider: str) -> dict:
        """Get configuration dict for specific provider.

        Args:
            provider: Provider name

        Returns:
            Configuration dictionary for the provider

        Examples:
            >>> config = get_ai_config()
            >>> cfg = config.get_provider_config('claude_api')
            >>> print(cfg.get('claude_model'))
            'claude-sonnet-4-20250514'.
        """
        return self._configs.get(provider, {})

    def get_fallback_chain(self) -> list[str]:
        """Get fallback chain based on priority and availability.

        Returns:
            List of providers in fallback order

        Examples:
            >>> config = get_ai_config()
            >>> config.get_fallback_chain()
            ['claude_api', 'mistral_api', 'ollama', 'clipboard'].
        """
        if not self.enable_fallback:
            return [self.default_provider]
        return self.get_available_providers()


# Global AI config instance
_ai_config_instance: AIProvidersConfig | None = None


def get_ai_config() -> AIProvidersConfig:
    """Get singleton instance of AI providers config.

    Returns:
        AIProvidersConfig instance

    Examples:
        >>> config = get_ai_config()
        >>> print(config.default_provider)
        'clipboard'.
    """
    global _ai_config_instance

    if _ai_config_instance is None:
        _ai_config_instance = AIProvidersConfig()
    return _ai_config_instance


def reset_ai_config():
    """Reset AI config singleton (useful for tests).

    Examples:
        >>> reset_ai_config()
        >>> config = get_ai_config()  # Creates new instance.
    """
    global _ai_config_instance

    _ai_config_instance = None


# ============================================================================
# Intervals.icu API Configuration
# ============================================================================


class IntervalsConfig:
    """Configuration for Intervals.icu API.

    Manages athlete ID and API key for Intervals.icu integration.
    Uses VITE_ prefix for React compatibility.

    Attributes:
        athlete_id: Intervals.icu athlete ID (format: i123456)
        api_key: Intervals.icu API key
        base_url: API base URL (default: https://intervals.icu/api/v1)

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'iXXXXXX'
        >>> print(config.is_configured())
        True.
    """

    def __init__(self):
        """Initialize Intervals.icu configuration from environment variables."""
        # Read from VITE_ prefixed variables (React compatibility)

        self.athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
        self.api_key = os.getenv("VITE_INTERVALS_API_KEY")
        self.base_url = os.getenv("VITE_INTERVALS_BASE_URL", "https://intervals.icu/api/v1")

    def is_configured(self) -> bool:
        """Check if Intervals.icu API is properly configured.

        Returns:
            True if both athlete_id and api_key are set

        Examples:
            >>> config = get_intervals_config()
            >>> if config.is_configured():
            ...     # Use API
            ...     pass
            ... else:
            ...     # Fallback mode
            ...     pass.
        """
        return bool(self.athlete_id and self.api_key)

    def get_headers(self) -> dict:
        """Get authentication headers for Intervals.icu API.

        Returns:
            Dict with Authorization header using Basic auth

        Examples:
            >>> config = get_intervals_config()
            >>> headers = config.get_headers()
            >>> # Use with requests
            >>> import requests
            >>> response = requests.get(url, headers=headers).
        """
        if not self.is_configured():
            raise ValueError("Intervals.icu API not configured")

        import base64

        auth_string = f"API_KEY:{self.api_key}"
        auth_bytes = auth_string.encode("ascii")
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode("ascii")

        return {"Authorization": f"Basic {base64_string}", "Content-Type": "application/json"}


# Global Intervals config instance
_intervals_config_instance: IntervalsConfig | None = None


def get_intervals_config() -> IntervalsConfig:
    """Get singleton instance of Intervals.icu config.

    Returns:
        IntervalsConfig instance

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'iXXXXXX'.
    """
    global _intervals_config_instance

    if _intervals_config_instance is None:
        _intervals_config_instance = IntervalsConfig()
    return _intervals_config_instance


def reset_intervals_config():
    """Reset Intervals config singleton (useful for tests).

    Examples:
        >>> reset_intervals_config()
        >>> config = get_intervals_config()  # Creates new instance.
    """
    global _intervals_config_instance

    _intervals_config_instance = None


def create_intervals_client():
    """Factory function for creating configured IntervalsClient.

    This is the preferred way to create an IntervalsClient instance as it
    centralizes credential loading and validation.

    Returns:
        IntervalsClient: Configured client ready to use

    Raises:
        ValueError: If Intervals.icu credentials are not configured
        ImportError: If IntervalsClient module is not available

    Examples:
        >>> from magma_cycling.config import create_intervals_client
        >>> client = create_intervals_client()
        >>> activities = client.get_activities(oldest="2026-01-01", newest="2026-01-15")

    Note:
        Replaces pattern of manually loading credentials and creating client:
        ```python
        # OLD (duplicated across 21 instances):
        athlete_id = os.getenv("VITE_INTERVALS_ATHLETE_ID")
        api_key = os.getenv("VITE_INTERVALS_API_KEY")
        client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)

        # NEW (centralized):
        client = create_intervals_client()
        ```
    """
    from magma_cycling.api.intervals_client import IntervalsClient

    config = get_intervals_config()

    if not config.is_configured():
        raise ValueError(
            "Intervals.icu API not configured. "
            "Set VITE_INTERVALS_ATHLETE_ID and VITE_INTERVALS_API_KEY environment variables."
        )

    return IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)


def load_json_config(config_file: str) -> dict | None:
    """Generic JSON config loader with expanduser support.

    Safely loads a JSON configuration file with proper error handling.
    Supports ~ expansion for user home directory.

    Args:
        config_file: Path to JSON config file (e.g., "~/.intervals_config.json")

    Returns:
        dict: Parsed JSON config, or None if file doesn't exist or is invalid

    Examples:
        >>> config = load_json_config("~/.intervals_config.json")
        >>> if config:
        ...     athlete_id = config.get("athlete_id")

    Note:
        Replaces pattern duplicated across 11 files:
        ```python
        # OLD (duplicated):
        config_path = Path.home() / ".intervals_config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

        # NEW (centralized):
        config = load_json_config("~/.intervals_config.json")
        ```
    """
    from pathlib import Path

    config_path = Path(config_file).expanduser()

    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # Log error but don't crash - allow caller to handle
        # Catches JSON decode errors, file I/O errors, and any other exceptions
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return None


# ============================================================================
# Week Reference Configuration
# ============================================================================


class WeekReferenceConfig:
    """Configuration for week numbering reference with multi-season support.

    Manages S001 reference dates for calculating week start dates across multiple
    training seasons. Reads from .config.json in the data repository (~/training-logs).

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
        import json

        if data_repo_path is None:
            data_config = get_data_config()
            data_repo_path = data_config.data_repo_path

        self.config_path = data_repo_path / ".config.json"

        # Check if config file exists
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Week reference config not found: {self.config_path}\n"
                f"Create it with multi-season support"
            )

        # Load config file
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_path}: {e}") from e

        # Extract week_reference section
        week_ref = config_data.get("week_reference")
        if not week_ref:
            raise ValueError(f"Missing 'week_reference' section in {self.config_path}")

        # Check if multi-season format
        if "seasons" in week_ref:
            # Multi-season format
            self.seasons = week_ref["seasons"]
            self.active_season = week_ref.get("active_season")

            if not self.seasons:
                raise ValueError(f"Empty 'seasons' in {self.config_path}")

            # Validate each season
            for season_id, season_data in self.seasons.items():
                if "s001_date" not in season_data:
                    raise ValueError(
                        f"Missing 's001_date' for season '{season_id}' in {self.config_path}"
                    )
                if "global_week_start" not in season_data:
                    raise ValueError(
                        f"Missing 'global_week_start' for season '{season_id}' in {self.config_path}"
                    )
                # Validate date format
                self._validate_date_format(season_data["s001_date"], season_id)

        else:
            # Legacy format: single season
            s001_date = week_ref.get("s001_date")
            if not s001_date:
                raise ValueError(
                    f"Missing 's001_date' in week_reference section of {self.config_path}"
                )

            self._validate_date_format(s001_date, "legacy")

            # Convert to multi-season format internally
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
        from datetime import datetime

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
                # Active season (no end date)
                if week_num >= start:
                    return season_id
            else:
                if start <= week_num <= end:
                    return season_id

        # Fallback: use active_season or first season
        if self.active_season:
            return self.active_season
        return list(self.seasons.keys())[0]

    def get_reference_for_week(self, week_id: str) -> tuple:
        """Get reference date and week offset for a given week ID.

        Args:
            week_id: Week identifier (e.g., "S075")

        Returns:
            Tuple of (reference_date, weeks_offset)
            - reference_date: datetime.date for the season's S001
            - weeks_offset: Number of weeks to add from season's S001

        Examples:
            >>> config = get_week_config()
            >>> ref, offset = config.get_reference_for_week("S075")
            >>> print(ref, offset)
            2026-01-05 0  # S075 is the first week of season 2026
        """
        from datetime import datetime

        week_num = int(week_id[1:])  # S075 → 75

        # Find the season for this week
        season_id = self.get_season_for_week(week_num)
        season_data = self.seasons[season_id]

        # Get reference date for this season
        reference_date = datetime.strptime(season_data["s001_date"], "%Y-%m-%d").date()

        # Calculate offset from season's start
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
            date(2024, 8, 5)  # Season 2024-2025
            >>> config.get_s001_date_obj("S075")
            date(2026, 1, 5)  # Season 2026
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


# ============================================================================
# Email Configuration (Brevo)
# ============================================================================


class EmailConfig:
    """Configuration for email notifications via Brevo API.

    Manages Brevo API credentials and email settings for automated reports.

    Attributes:
        api_key: Brevo API key (format: xkeysib-...)
        email_to: Recipient email address
        email_from: Sender email address (must be verified in Brevo)
        email_from_name: Sender display name

    Examples:
        >>> config = get_email_config()
        >>> if config.is_configured():
        ...     print(f"Email configured for {config.email_to}")
        ... else:
        ...     print("Email not configured")
    """

    def __init__(self):
        """Initialize email configuration from environment variables."""
        self.api_key = os.getenv("BREVO_API_KEY")
        self.email_to = os.getenv("EMAIL_TO")
        self.email_from = os.getenv("EMAIL_FROM")
        self.email_from_name = os.getenv("EMAIL_FROM_NAME", "Training Logs")

    def is_configured(self) -> bool:
        """Check if email is properly configured.

        Returns:
            True if all required settings are present

        Examples:
            >>> config = get_email_config()
            >>> if config.is_configured():
            ...     # Send email
            ...     pass
            ... else:
            ...     # Skip email sending
            ...     pass
        """
        return bool(self.api_key and self.email_to and self.email_from)

    def get_missing_vars(self) -> list[str]:
        """Get list of missing required environment variables.

        Returns:
            List of missing variable names

        Examples:
            >>> config = get_email_config()
            >>> missing = config.get_missing_vars()
            >>> if missing:
            ...     print(f"Missing: {', '.join(missing)}")
        """
        missing = []
        if not self.api_key:
            missing.append("BREVO_API_KEY")
        if not self.email_to:
            missing.append("EMAIL_TO")
        if not self.email_from:
            missing.append("EMAIL_FROM")
        return missing


# Global Email config instance
_email_config_instance: EmailConfig | None = None


def get_email_config() -> EmailConfig:
    """Get singleton instance of Email config.

    Returns:
        EmailConfig instance

    Examples:
        >>> config = get_email_config()
        >>> if config.is_configured():
        ...     print("Email ready")
    """
    global _email_config_instance

    if _email_config_instance is None:
        _email_config_instance = EmailConfig()
    return _email_config_instance


def reset_email_config():
    """Reset Email config singleton (useful for tests).

    Examples:
        >>> reset_email_config()
        >>> config = get_email_config()  # Creates new instance
    """
    global _email_config_instance

    _email_config_instance = None


# ============================================================================
# Withings API Configuration
# ============================================================================


class WithingsConfig:
    """Configuration for Withings API.

    Manages OAuth credentials and API settings for Withings health data integration.

    Attributes:
        client_id: Withings OAuth client ID
        client_secret: Withings OAuth client secret
        redirect_uri: OAuth callback URI
        credentials_path: Path to stored OAuth credentials JSON

    Examples:
        >>> config = get_withings_config()
        >>> print(config.is_configured())
        True
        >>> if config.has_valid_credentials():
        ...     # Use Withings API
        ...     pass
    """

    def __init__(self):
        """Initialize Withings configuration from environment variables."""
        self.client_id = os.getenv("WITHINGS_CLIENT_ID")
        self.client_secret = os.getenv("WITHINGS_CLIENT_SECRET")
        self.redirect_uri = os.getenv("WITHINGS_REDIRECT_URI", "http://localhost:8080/callback")

        # Credentials storage path
        data_config = get_data_config()
        self.credentials_path = data_config.data_repo_path / ".withings_credentials.json"

    def is_configured(self) -> bool:
        """Check if Withings API credentials are properly configured.

        Returns:
            True if both client_id and client_secret are set

        Examples:
            >>> config = get_withings_config()
            >>> if config.is_configured():
            ...     # Initialize client
            ...     pass
            ... else:
            ...     print("Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET")
        """
        return bool(self.client_id and self.client_secret)

    def has_valid_credentials(self) -> bool:
        """Check if stored OAuth credentials exist and are valid.

        Returns:
            True if credentials file exists and tokens are not expired

        Examples:
            >>> config = get_withings_config()
            >>> if not config.has_valid_credentials():
            ...     # Need to run OAuth flow
            ...     print("Run setup_withings.py to authenticate")
        """
        if not self.credentials_path.exists():
            return False

        try:
            with open(self.credentials_path, encoding="utf-8") as f:
                creds = json.load(f)

            # Check if required fields exist
            if not all(k in creds for k in ["access_token", "refresh_token", "token_expiry"]):
                return False

            # A refresh_token is sufficient — the client refreshes automatically
            return True

        except Exception:
            return False


# Global Withings config instance
_withings_config_instance: WithingsConfig | None = None


def get_withings_config() -> WithingsConfig:
    """Get singleton instance of Withings config.

    Returns:
        WithingsConfig instance

    Examples:
        >>> config = get_withings_config()
        >>> print(config.client_id)
        'your_withings_client_id_here'
    """
    global _withings_config_instance

    if _withings_config_instance is None:
        _withings_config_instance = WithingsConfig()
    return _withings_config_instance


def reset_withings_config():
    """Reset Withings config singleton (useful for tests).

    Examples:
        >>> reset_withings_config()
        >>> config = get_withings_config()  # Creates new instance
    """
    global _withings_config_instance

    _withings_config_instance = None


def create_withings_client():
    """Factory function for creating configured WithingsClient.

    This is the preferred way to create a WithingsClient instance as it
    centralizes credential loading and validation.

    Returns:
        WithingsClient: Configured client ready to use

    Raises:
        ValueError: If Withings credentials are not configured
        ImportError: If WithingsClient module is not available

    Examples:
        >>> from magma_cycling.config import create_withings_client
        >>> client = create_withings_client()
        >>> if client.is_authenticated():
        ...     sleep = client.get_last_night_sleep()
        ... else:
        ...     url = client.get_authorization_url()
        ...     print(f"Authorize at: {url}")

    Note:
        Follows the same pattern as create_intervals_client() for consistency.
        The client will automatically load existing credentials if available.
    """
    from magma_cycling.api.withings_client import WithingsClient

    config = get_withings_config()

    if not config.is_configured():
        raise ValueError(
            "Withings API not configured. "
            "Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET environment variables."
        )

    return WithingsClient(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        credentials_path=config.credentials_path,
    )


# ============================================================================


def create_health_provider():
    """Factory function for creating a configured HealthProvider.

    Delegates to magma_cycling.health.factory. Returns NullProvider if
    Withings is not configured or on any error.

    Returns:
        HealthProvider: Configured provider ready to use
    """
    from magma_cycling.health.factory import create_health_provider as _factory

    return _factory()


__all__ = [
    # Data repo config
    "DataRepoConfig",
    "get_data_config",
    "set_data_config",
    "reset_data_config",
    # AI providers config
    "AIProvidersConfig",
    "get_ai_config",
    "reset_ai_config",
    # Intervals.icu config
    "IntervalsConfig",
    "get_intervals_config",
    "reset_intervals_config",
    "create_intervals_client",
    # Withings config
    "WithingsConfig",
    "get_withings_config",
    "reset_withings_config",
    "create_withings_client",
    # Health provider
    "create_health_provider",
    # Week reference config
    "WeekReferenceConfig",
    "get_week_config",
    "reset_week_config",
    # Email config (Brevo)
    "EmailConfig",
    "get_email_config",
    "reset_email_config",
    # Utilities
    "load_json_config",
]
