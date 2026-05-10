"""Data repository configuration.

Manages paths to the external training-logs data repository.

Phase 2 (ADR v5 — ticket #39) : ajout du writer-scoping. Le repo
training-logs peut être organisé en subdirs par writer (hash 12-char
opaque par operator), résolus via ``TRAINING_DATA_WRITER_ID``. Activé
par feature flag ``TRAINING_DATA_WRITER_SCOPED=1`` (défaut OFF =
rétro-compat layout flat legacy).

Variables d'environnement :

- ``TRAINING_DATA_ROOT`` (nouveau, ADR v5) : path racine du repo
  training-logs. Remplace ``TRAINING_DATA_REPO`` (deprecated avec
  fallback + DeprecationWarning).
- ``TRAINING_DATA_WRITER_ID`` (nouveau, ADR v5 Phase 2) : hash 12-char
  identifiant le writer courant. Requis si ``TRAINING_DATA_WRITER_SCOPED=1``.
- ``TRAINING_DATA_WRITER_SCOPED`` (nouveau, feature flag, défaut ``0``) :
  si ``1``/``true`` activé, ``data_repo_path = ROOT/<WRITER_ID>``.
  Sinon (défaut), ``data_repo_path = ROOT`` (layout flat legacy).
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from magma_cycling.paths import get_env_path

_env_file = get_env_path()
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

#: Nom de la var d'env (nouvelle) pour le path racine du repo training-logs.
ROOT_ENV = "TRAINING_DATA_ROOT"

#: Var d'env legacy, deprecated. Fallback toléré + DeprecationWarning.
#: Sera supprimée dans une PR future post-wave finale (cf. ADR v5).
LEGACY_ROOT_ENV = "TRAINING_DATA_REPO"

#: Var d'env du hash 12-char identifiant le writer courant. Requis si
#: ``TRAINING_DATA_WRITER_SCOPED=1``.
WRITER_ID_ENV = "TRAINING_DATA_WRITER_ID"

#: Feature flag (défaut OFF). Si ``1``/``true``, active le writer-scoping
#: (subdirs par writer). Permet rollback instantané via flag (filet de
#: sécurité #1 du protocole niveau diamant).
WRITER_SCOPED_ENV = "TRAINING_DATA_WRITER_SCOPED"

#: Nom du fichier d'index `.operators.yaml` à la racine du repo.
OPERATORS_FILE = ".operators.yaml"

#: Whitelist par défaut des fichiers racine autorisés (utilisée si
#: ``.operators.yaml`` absent ou ne définit pas ``shared_root_files``).
DEFAULT_SHARED_ROOT_FILES = [
    ".gitignore",
    "README.md",
    OPERATORS_FILE,
]


def _writer_scoped_enabled() -> bool:
    """Lit le feature flag ``TRAINING_DATA_WRITER_SCOPED``.

    Returns:
        ``True`` si ``1``/``true``/``yes`` (case-insensitive), sinon ``False``.
    """
    return os.getenv(WRITER_SCOPED_ENV, "0").strip().lower() in ("1", "true", "yes")


def _resolve_root_from_env() -> Path | None:
    """Lit le path racine du repo depuis les vars d'env.

    Priorité :
    1. ``TRAINING_DATA_ROOT`` (nouvelle var, recommandée)
    2. ``TRAINING_DATA_REPO`` (deprecated, fallback avec DeprecationWarning)

    Returns:
        ``Path`` résolu si une des vars est définie, sinon ``None``.
    """
    root = os.getenv(ROOT_ENV)
    legacy = os.getenv(LEGACY_ROOT_ENV)
    if root:
        return Path(root).expanduser()
    if legacy:
        logger.warning(
            "%s is deprecated, please rename to %s. "
            "Fallback will be removed in a future release.",
            LEGACY_ROOT_ENV,
            ROOT_ENV,
        )
        return Path(legacy).expanduser()
    return None


def _load_operators_yaml(root: Path) -> dict | None:
    """Charge ``.operators.yaml`` à la racine du repo si présent.

    Args:
        root: Path racine du repo training-logs.

    Returns:
        Dict parsé du yaml, ou ``None`` si fichier absent / parse error.
        Un parse error log un warning mais retourne ``None`` (pas fatal —
        le caller décide).
    """
    yaml_path = root / OPERATORS_FILE
    if not yaml_path.is_file():
        return None
    try:
        with yaml_path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse %s: %s", yaml_path, exc)
        return None


class DataRepoConfig:
    """Configuration for external data repository paths.

    En mode legacy (flag OFF, défaut), ``data_repo_path = ROOT``. En mode
    writer-scoped (``TRAINING_DATA_WRITER_SCOPED=1``),
    ``data_repo_path = ROOT/<WRITER_ID>`` et ``ROOT`` reste accessible
    via :attr:`root_path` pour le scope racine (writes whitelist).
    """

    def __init__(
        self,
        data_repo_path: Path | None = None,
        *,
        writer_scoped: bool | None = None,
        writer_id: str | None = None,
    ):
        """Initialize data repository configuration.

        Args:
            data_repo_path: Override explicite (back-compat tests). Si fourni,
                bypass la résolution env vars + writer-scoping. Le path est
                à la fois ``root_path`` et ``data_repo_path``.
            writer_scoped: Override le feature flag (sinon lu depuis env).
            writer_id: Override le writer ID (sinon lu depuis env). Requis
                si ``writer_scoped=True`` et pas d'override ``data_repo_path``.

        Raises:
            FileNotFoundError: si data repository path n'existe pas.
            RuntimeError: si writer-scoped activé mais ``WRITER_ID`` absent.
        """
        if data_repo_path is not None:
            # Override explicite : data_repo_path = root_path (back-compat).
            self.root_path = Path(data_repo_path).resolve()
            self.data_repo_path = self.root_path
            self.writer_id = writer_id
            self.writer_scoped = bool(writer_scoped) if writer_scoped is not None else False
        else:
            root = _resolve_root_from_env()
            if root is None:
                root = Path.home() / "training-logs"
            self.root_path = root.resolve()
            self.writer_scoped = (
                writer_scoped if writer_scoped is not None else _writer_scoped_enabled()
            )
            if self.writer_scoped:
                resolved_writer_id = writer_id or os.getenv(WRITER_ID_ENV)
                if not resolved_writer_id:
                    raise RuntimeError(
                        f"{WRITER_ID_ENV} is required when {WRITER_SCOPED_ENV}=1. "
                        f"Run `provision-writer <alias>` to provision a writer, "
                        f"or unset {WRITER_SCOPED_ENV} to fall back to flat layout."
                    )
                self.writer_id = resolved_writer_id
                self.data_repo_path = self.root_path / resolved_writer_id
            else:
                self.writer_id = None
                self.data_repo_path = self.root_path

        if not self.data_repo_path.exists():
            raise FileNotFoundError(
                f"Data repo not found: {self.data_repo_path}\n"
                f"Set {ROOT_ENV} env var or clone:\n"
                f"  git clone https://github.com/YOUR_USERNAME/training-logs.git ~/training-logs"
            )

        # Cache .operators.yaml content (lazy via property)
        self._operators_yaml_cache: dict | None = None
        self._operators_yaml_loaded = False

        # Duplicate detection settings (paranoid mode for backfill testing)
        self.paranoid_duplicate_check = True
        self.auto_fix_duplicates = False
        self.duplicate_check_window = 50

    @property
    def operators_yaml(self) -> dict | None:
        """Contenu parsé de ``.operators.yaml`` (lazy-loaded, cached)."""
        if not self._operators_yaml_loaded:
            self._operators_yaml_cache = _load_operators_yaml(self.root_path)
            self._operators_yaml_loaded = True
        return self._operators_yaml_cache

    @property
    def shared_root_files(self) -> list[str]:
        """Liste des paths racine autorisés en write (whitelist).

        Lue depuis ``.operators.yaml::shared_root_files`` si défini,
        sinon retourne :data:`DEFAULT_SHARED_ROOT_FILES`.
        """
        ops = self.operators_yaml
        if ops and isinstance(ops.get("shared_root_files"), list):
            return list(ops["shared_root_files"])
        return list(DEFAULT_SHARED_ROOT_FILES)

    def is_safe_write_path(self, path: Path | str) -> bool:
        """Vérifie qu'un path est autorisé en écriture sous le layout courant.

        En mode legacy (writer_scoped=False) : tout path sous root est OK
        (rétro-compat).

        En mode writer-scoped : path doit être :
        - Sous ``data_repo_path`` (= ``root/<writer_id>``), OU
        - Dans la whitelist ``shared_root_files`` à la racine du repo.

        Tout autre write hors subdir + hors whitelist = refus (guard-rail
        contre pollution racine).

        Args:
            path: Path absolu (ou résolvable) à vérifier.

        Returns:
            ``True`` si write autorisé, ``False`` sinon.
        """
        try:
            p = Path(path).resolve()
        except (OSError, RuntimeError):
            return False

        if not self.writer_scoped:
            # Legacy : tout sous root OK (comportement avant ADR Phase 2)
            return self._is_under(p, self.root_path)

        # Mode scoped : sous data_repo_path (= root/<writer_id>) OK
        if self._is_under(p, self.data_repo_path):
            return True

        # Sinon, doit matcher la whitelist shared_root_files à la racine
        if not self._is_under(p, self.root_path):
            return False
        rel = p.relative_to(self.root_path)
        rel_str = str(rel)
        # Compare avec chaque entrée de la whitelist (matching exact ou prefix
        # pour les patterns dossier comme "docs/architecture/**")
        for entry in self.shared_root_files:
            entry_clean = entry.rstrip("/").rstrip("*").rstrip("/")
            if rel_str == entry or rel_str == entry_clean:
                return True
            if entry_clean and rel_str.startswith(entry_clean + "/"):
                return True
        return False

    @staticmethod
    def _is_under(child: Path, parent: Path) -> bool:
        """``True`` si ``child`` est ``parent`` ou descendant."""
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

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


def startup_health_check() -> DataRepoConfig | None:
    """Fail-fast startup health-check pour le serveur MCP.

    Validation à BOOT (vs lazy au 1er tool call) :
    - ``TRAINING_DATA_ROOT`` (ou legacy ``TRAINING_DATA_REPO``) env existe
      et pointe vers un dossier
    - Si ``TRAINING_DATA_WRITER_SCOPED=1`` : ``TRAINING_DATA_WRITER_ID`` set
      et le subdir existe
    - ``workouts-history.md`` présent dans ``data_repo_path``
    - Lecture autorisée

    En cas d'échec, log FATAL puis ``sys.exit(1)`` avec message clair —
    évite le pattern observé sur INFRA-001 où ``FileNotFoundError`` surfaçait
    en plein tool call (perte de séance utilisateur S091-02 le 2026-04-28).

    En cas de succès, log INFO avec le path résolu, la taille de
    ``workouts-history.md`` et le SHA HEAD git si applicable.

    The ``MCP_SKIP_STARTUP_HEALTH_CHECK=1`` env var skips the validation and
    returns ``None`` — used by the PyInstaller smoke tests in CI where there
    is no training-logs repo on the runner. Production deployments must NOT
    set this variable.

    Returns:
        DataRepoConfig validé (peut être ré-utilisé par le caller pour éviter
        une 2e instanciation), ou ``None`` si le check est skipped.
    """
    if os.getenv("MCP_SKIP_STARTUP_HEALTH_CHECK", "").lower() in ("1", "true", "yes"):
        logger.warning(
            "data_repo_health_skipped: MCP_SKIP_STARTUP_HEALTH_CHECK=%s "
            "(intended for PyInstaller smoke tests; do NOT set in production)",
            os.getenv("MCP_SKIP_STARTUP_HEALTH_CHECK"),
        )
        return None

    try:
        cfg = DataRepoConfig()
        cfg.validate()
        # Lecture-test : os.access (perm bit) + open (ouverture effective) pour
        # détecter les permissions cassées au lieu d'attendre un read en runtime.
        if not os.access(cfg.workouts_history_path, os.R_OK):
            raise PermissionError(f"workouts-history.md not readable: {cfg.workouts_history_path}")
        with cfg.workouts_history_path.open("rb") as fh:
            fh.read(1)
    except (FileNotFoundError, PermissionError, OSError, RuntimeError) as exc:
        msg = f"FATAL: training data repo invalid: {exc}"
        logger.error(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)

    head_sha = _git_head_short(cfg.data_repo_path)
    logger.info(
        "data_repo_health_ok: path=%s scoped=%s writer_id=%s "
        "workouts_history_bytes=%d head_sha=%s",
        cfg.data_repo_path,
        cfg.writer_scoped,
        cfg.writer_id or "n/a",
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
