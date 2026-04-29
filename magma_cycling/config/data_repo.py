"""Data repository configuration.

Manages paths to the external training-logs data repository.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from magma_cycling.paths import get_env_path

_env_file = get_env_path()
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()

logger = logging.getLogger(__name__)


class DataRepoConfig:
    """Configuration for external data repository paths."""

    def __init__(self, data_repo_path: Path | None = None):
        """Initialize data repository configuration.

        Args:
            data_repo_path: Path to external data repository.
                           If None, will try TRAINING_DATA_REPO env var,
                           then default to ~/training-logs

        Raises:
            FileNotFoundError: If data repository path doesn't exist
        """
        if data_repo_path is None:
            env_path = os.getenv("TRAINING_DATA_REPO")
            if env_path:
                data_repo_path = Path(env_path).expanduser()
            else:
                data_repo_path = Path.home() / "training-logs"

        self.data_repo_path = Path(data_repo_path).resolve()

        if not self.data_repo_path.exists():
            raise FileNotFoundError(
                f"Data repo not found: {self.data_repo_path}\n"
                f"Set TRAINING_DATA_REPO env var or clone:\n"
                f"  git clone https://github.com/YOUR_USERNAME/training-logs.git ~/training-logs"
            )

        # Duplicate detection settings (paranoid mode for backfill testing)
        self.paranoid_duplicate_check = True
        self.auto_fix_duplicates = False
        self.duplicate_check_window = 50

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
    def terrain_circuits_dir(self) -> Path:
        """Path to data/terrain_circuits/ directory in data repo."""
        return self.data_dir / "terrain_circuits"

    @property
    def workflow_state_path(self) -> Path:
        """Path to .workflow_state.json in data repo."""
        return self.data_repo_path / ".workflow_state.json"

    @property
    def handoff_dir(self) -> Path:
        """Path to handoff/ directory in data repo (context-handoff snapshots)."""
        return self.data_repo_path / "handoff"

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        self.bilans_dir.mkdir(parents=True, exist_ok=True)
        self.week_planning_dir.mkdir(parents=True, exist_ok=True)
        self.workout_templates_dir.mkdir(parents=True, exist_ok=True)
        self.terrain_circuits_dir.mkdir(parents=True, exist_ok=True)
        self.handoff_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Validate data repository structure.

        Returns:
            True if all required files/dirs exist

        Raises:
            FileNotFoundError: If critical files missing
        """
        if not self.workouts_history_path.exists():
            raise FileNotFoundError(
                f"workouts-history.md not found in data repo: {self.data_repo_path}\n"
                f"Create it with: touch {self.workouts_history_path}"
            )
        self.ensure_directories()
        return True


# Global config instance
_global_config: DataRepoConfig | None = None


def get_data_config() -> DataRepoConfig:
    """Get or create global data repository configuration.

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
    """Set global data repository configuration.

    Args:
        config: DataRepoConfig instance or None to reset.
    """
    global _global_config
    _global_config = config


def reset_data_config():
    """Reset global configuration (mainly for testing)."""
    global _global_config
    _global_config = None


def _git_head_short(path: Path) -> str | None:
    """Best-effort lecture du SHA HEAD git du repo data — None si pas un git repo.

    Utile pour log INFO au boot (traçabilité version data) et future ADR Phase 2
    où le hash subdir writer sera dérivé du SHA. Timeout court pour pas bloquer
    le boot si git est lent.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def startup_health_check() -> DataRepoConfig:
    """Fail-fast startup health-check pour le serveur MCP.

    Validation à BOOT (vs lazy au 1er tool call) :
    - ``TRAINING_DATA_REPO`` env existe et pointe vers un dossier
    - ``workouts-history.md`` présent à la racine (file à plat post-rollback ADR v5)
    - Lecture autorisée

    En cas d'échec, log FATAL puis ``sys.exit(1)`` avec message clair —
    évite le pattern observé sur INFRA-001 où ``FileNotFoundError`` surfaçait
    en plein tool call (perte de séance utilisateur S091-02 le 2026-04-28).

    En cas de succès, log INFO avec le path résolu, la taille de
    ``workouts-history.md`` et le SHA HEAD git si applicable.

    Returns:
        DataRepoConfig validé (peut être ré-utilisé par le caller pour éviter
        une 2e instanciation).
    """
    try:
        cfg = DataRepoConfig()
        cfg.validate()
        # Lecture-test : os.access (perm bit) + open (ouverture effective) pour
        # détecter les permissions cassées au lieu d'attendre un read en runtime.
        if not os.access(cfg.workouts_history_path, os.R_OK):
            raise PermissionError(f"workouts-history.md not readable: {cfg.workouts_history_path}")
        with cfg.workouts_history_path.open("rb") as fh:
            fh.read(1)
    except (FileNotFoundError, PermissionError, OSError) as exc:
        msg = f"FATAL: training data repo invalid: {exc}"
        logger.error(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)

    head_sha = _git_head_short(cfg.data_repo_path)
    logger.info(
        "data_repo_health_ok: path=%s workouts_history_bytes=%d head_sha=%s",
        cfg.data_repo_path,
        cfg.workouts_history_path.stat().st_size,
        head_sha or "n/a",
    )
    return cfg


def load_json_config(config_file: str) -> dict | None:
    """Generic JSON config loader with expanduser support.

    Args:
        config_file: Path to JSON config file (e.g., "~/.intervals_config.json")

    Returns:
        dict: Parsed JSON config, or None if file doesn't exist or is invalid
    """
    config_path = Path(config_file).expanduser()

    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return None
