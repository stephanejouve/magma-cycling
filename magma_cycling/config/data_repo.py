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

#: Var d'env override pour le dossier de l'intelligence (rétro-compat dev
#: local). Si définie, prend priorité sur ``<root>/data/intelligence/``.
#: Par défaut (env absent) : ``<TRAINING_DATA_ROOT>/data/intelligence/``
#: pour que le fichier survive aux redeploys container (cf. plan iso-config
#: PR1, incident 2026-05-12 où redeploy stack #33 a effacé
#: ``/home/magma/data/intelligence.json`` du writable layer Docker).
INTELLIGENCE_DATA_DIR_ENV = "INTELLIGENCE_DATA_DIR"

#: Var d'env override pour le path complet du fichier ``athlete.yaml``
#: (rétro-compat dev / tests). Si définie, prend priorité sur
#: ``<root>/config/athlete.yaml``. Par défaut (env absent) :
#: ``<TRAINING_DATA_ROOT>/config/athlete.yaml`` pour que la config athlète
#: vive dans le repo training-logs portable (plan iso-config PR5, AC1
#: portabilité). Fallback final = ``paths.get_athlete_yaml_path()`` (legacy
#: user config dir) quand aucune des deux options n'est disponible (boot
#: initial sans repo, dev sans env).
ATHLETE_CONFIG_PATH_ENV = "ATHLETE_CONFIG_PATH"

#: Nom du fichier d'index `.operators.yaml` à la racine du repo.
OPERATORS_FILE = ".operators.yaml"

#: Sous-dossier (relatif à la racine training-logs) qui héberge
#: ``intelligence.json`` et les artefacts apparentés (= shared entre writers).
INTELLIGENCE_SUBDIR = "data/intelligence"

#: Nom du fichier intelligence sous :data:`INTELLIGENCE_SUBDIR`.
INTELLIGENCE_FILENAME = "intelligence.json"

#: Sous-dossier (relatif à la racine training-logs) qui héberge l'archive
#: wellness brut (1 fichier JSON par jour, PR2 plan iso-config AC2). Shared
#: cross-writers — wellness est un fait per-athlète, pas per-writer. Le
#: backfill 90j via PR2bis remplit rétroactivement ce dossier (~270 KB).
WELLNESS_SUBDIR = "data/wellness"

#: Sous-dossier (relatif à la racine training-logs) qui héberge le decision
#: log go-forward (PR8 plan iso-config). 1 fichier markdown par décision
#: stratégique : ``decision-SXXX-NN.md`` avec front-matter YAML.
#: Shared cross-writers — décisions = athlète, pas opérateur.
DECISIONS_SUBDIR = "data/decisions"

#: Sous-dossier (relatif à la racine training-logs) qui héberge la config
#: athlète portable (PR5 AC1). Shared cross-writers — un seul athlète par repo.
ATHLETE_CONFIG_SUBDIR = "config"

#: Nom du fichier athlète sous :data:`ATHLETE_CONFIG_SUBDIR`. PR5 plan
#: iso-config : externalisation depuis ``magma_cycling/config/athlete_context.yaml``
#: (bundle, devient bootstrap fallback) vers ce fichier portable.
ATHLETE_CONFIG_FILENAME = "athlete.yaml"

#: Whitelist par défaut des fichiers racine autorisés (utilisée si
#: ``.operators.yaml`` absent ou ne définit pas ``shared_root_files``).
#: ``data/intelligence/**`` et ``data/wellness/**`` sont inclus pour que le
#: mode writer-scoped futur (cf. ADR v5) autorise l'écriture des artefacts
#: shared cross-writers.
DEFAULT_SHARED_ROOT_FILES = [
    ".gitignore",
    "README.md",
    OPERATORS_FILE,
    "data/intelligence/**",
    "data/wellness/**",
    "data/decisions/**",
    "config/athlete.yaml",
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


def resolve_athlete_yaml_path() -> Path:
    """Résout le path de ``athlete.yaml`` (config athlète portable, PR5 AC1).

    Priorité :

    1. :data:`ATHLETE_CONFIG_PATH_ENV` (override explicite, dev / tests).
    2. :data:`ROOT_ENV` (``TRAINING_DATA_ROOT``) → ``<root>/config/athlete.yaml``.
    3. :data:`LEGACY_ROOT_ENV` (``TRAINING_DATA_REPO``) → idem (avec DeprecationWarning
       déjà émis par :func:`_resolve_root_from_env`).
    4. Fallback legacy ``paths.get_athlete_yaml_path()`` (user config dir),
       qui préserve le comportement pré-PR5 sur un poste sans env training-logs.

    Le helper ne touche pas au file system — la création du dossier parent
    reste à la charge du caller (``mkdir(parents=True, exist_ok=True)``).
    Le bundle ``magma_cycling/config/athlete_context.yaml`` reste utilisé en
    bootstrap fallback en lecture par
    :func:`magma_cycling.config.athlete_context.load_athlete_context` quand
    le path résolu n'existe pas encore (= 1ère exécution sur un repo
    training-logs vierge).
    """
    override = os.getenv(ATHLETE_CONFIG_PATH_ENV)
    if override:
        return Path(override).expanduser()
    root = _resolve_root_from_env()
    if root is not None:
        return root / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME
    from magma_cycling.paths import get_athlete_yaml_path

    return get_athlete_yaml_path()


def resolve_intelligence_file_path() -> Path:
    """Résout le path de ``intelligence.json`` sans instancier ``DataRepoConfig``.

    Priorité (cf. plan iso-config PR1, ADR v5 §3) :

    1. :data:`INTELLIGENCE_DATA_DIR_ENV` (override explicite, rétro-compat dev local).
    2. :data:`ROOT_ENV` (``TRAINING_DATA_ROOT``) → ``<root>/data/intelligence/intelligence.json``.
    3. :data:`LEGACY_ROOT_ENV` (``TRAINING_DATA_REPO``) → idem (avec DeprecationWarning).
    4. Fallback legacy ``~/data/intelligence.json`` (dev local sans env, comportement pré-PR1).

    Le helper ne touche pas au file system — la création du dossier parent reste
    à la charge du caller (``mkdir(parents=True, exist_ok=True)``).
    """
    override = os.getenv(INTELLIGENCE_DATA_DIR_ENV)
    if override:
        return Path(override).expanduser() / INTELLIGENCE_FILENAME
    root = _resolve_root_from_env()
    if root is not None:
        return root / INTELLIGENCE_SUBDIR / INTELLIGENCE_FILENAME
    return Path.home() / "data" / INTELLIGENCE_FILENAME


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
        # POSIX-style separator pour matching cross-platform (les patterns
        # dans .operators.yaml utilisent toujours `/`, jamais `\` Windows).
        rel_str = rel.as_posix()
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
    def athlete_config_path(self) -> Path:
        """Path à ``athlete.yaml`` (shared cross-writers, sous root_path).

        PR5 plan iso-config : la config athlète vit dans le repo training-logs
        portable, pas dans le bundle MCP. Sous ``root_path`` (et non
        ``data_repo_path``) car un seul athlète par repo training-logs —
        invariant ADR v5 — donc shared cross-writers en mode writer-scoped.

        :data:`ATHLETE_CONFIG_PATH_ENV` reste prioritaire (override dev / tests).
        """
        override = os.getenv(ATHLETE_CONFIG_PATH_ENV)
        if override:
            return Path(override).expanduser()
        return self.root_path / ATHLETE_CONFIG_SUBDIR / ATHLETE_CONFIG_FILENAME

    @property
    def decisions_dir(self) -> Path:
        """Path au decision log go-forward (shared cross-writers, sous root_path).

        PR8 plan iso-config : decisions = stratégiques athlète (changement
        cible, bascule modale, post-incident, adaptation post-bilan ≥S+1).
        1 fichier markdown par décision, granularité ≤10/mois.
        """
        return self.root_path / DECISIONS_SUBDIR

    @property
    def wellness_dir(self) -> Path:
        """Path au dossier d'archive wellness (shared cross-writers, sous root_path).

        PR2 plan iso-config (AC2 self-contained) : 1 fichier JSON par jour de
        wellness brut Intervals.icu (sleep, HRV, weight, readiness, CTL/ATL/TSB).
        Sous ``root_path`` (et non ``data_repo_path``) car wellness est un fait
        per-athlète, pas per-writer — invariant ADR v5.
        """
        return self.root_path / WELLNESS_SUBDIR

    @property
    def intelligence_dir(self) -> Path:
        """Path au dossier intelligence (shared cross-writers).

        Résolution :
        1. Si :data:`INTELLIGENCE_DATA_DIR_ENV` est défini → ``Path(env).expanduser()``
           (rétro-compat dev local / override explicite).
        2. Sinon → ``root_path / data/intelligence/`` (mount training-logs partagé).

        Le path utilise :attr:`root_path` (et non :attr:`data_repo_path`) pour
        rester shared cross-writers en mode writer-scoped futur.
        """
        env_override = os.getenv(INTELLIGENCE_DATA_DIR_ENV)
        if env_override:
            return Path(env_override).expanduser()
        return self.root_path / INTELLIGENCE_SUBDIR

    @property
    def intelligence_file_path(self) -> Path:
        """Path au fichier ``intelligence.json`` (sous :attr:`intelligence_dir`)."""
        return self.intelligence_dir / INTELLIGENCE_FILENAME

    @property
    def handoff_dir(self) -> Path:
        """Path to handoff/ directory in data repo (context-handoff snapshots)."""
        return self.data_repo_path / "handoff"

    @property
    def authority_rules(self) -> list[tuple[str, str]]:
        """Liste ordonnée ``(pattern, writer_alias)`` issue de ``.operators.yaml::authority``.

        L'ordre de déclaration YAML est préservé (premier match gagne dans
        :meth:`resolve_read_path`). Retourne ``[]`` si la section ``authority``
        est absente, le fichier ``.operators.yaml`` n'existe pas, ou les
        valeurs ne sont pas des dicts simples ``pattern -> alias``.

        Phase 3 PR D (plan iso-config PR11a) — strict read-only.
        """
        ops = self.operators_yaml
        if not ops:
            return []
        auth = ops.get("authority")
        if not isinstance(auth, dict):
            return []
        out: list[tuple[str, str]] = []
        for pattern, alias in auth.items():
            if isinstance(pattern, str) and isinstance(alias, str):
                out.append((pattern, alias))
        return out

    def _resolve_writer_alias_to_hash(self, alias: str) -> str | None:
        """Résoud un alias writer (``mac``, ``nas-prod``, ...) en son hash 12-char.

        Consulte la section ``writers:`` de ``.operators.yaml``. Retourne
        ``None`` si l'alias n'est pas trouvé ou si la section est absente.
        Une entrée writer avec ``decommissioned_at`` non-null n'est PAS
        exclue (read fallback historique reste possible — l'historique est
        préservé même après décommission par convention ADR v5 §3).
        """
        ops = self.operators_yaml
        if not ops:
            return None
        writers = ops.get("writers")
        if not isinstance(writers, dict):
            return None
        for writer_hash, meta in writers.items():
            if not isinstance(meta, dict):
                continue
            if meta.get("alias") == alias:
                return writer_hash if isinstance(writer_hash, str) else None
        return None

    @staticmethod
    def _match_authority_pattern(file_pattern: str, rule_pattern: str) -> bool:
        """Match un ``file_pattern`` (path POSIX) contre un ``rule_pattern`` ``.operators.yaml::authority``.

        Sémantique des patterns supportés :
        - Suffixe ``/**`` ou ``/*`` → match préfixe directory récursif (ex.
          ``workouts/**`` matche ``workouts/foo.zwo`` et ``workouts/sub/bar.zwo``)
        - Sinon → match exact via :func:`fnmatch.fnmatchcase` (glob standard
          POSIX, supporte ``*`` / ``?`` / ``[abc]``)

        L'argument ``rule_pattern`` est tel que déclaré dans ``authority:``
        (un seul wildcard récursif terminal est typiquement utilisé).
        """
        import fnmatch

        if rule_pattern.endswith("/**") or rule_pattern.endswith("/*"):
            prefix = rule_pattern.rsplit("/", 1)[0].rstrip("/") + "/"
            return file_pattern.startswith(prefix)
        return fnmatch.fnmatchcase(file_pattern, rule_pattern)

    def resolve_read_path(self, file_pattern: str) -> Path:
        """Résoud un path de lecture multi-writer selon ``.operators.yaml::authority``.

        Phase 3 PR D (plan iso-config PR11a) — helper central consumer-side
        pour faire converger les lectures vers la subdir du writer autoritaire,
        plutôt que de lire flat depuis la racine du repo.

        Comportement :

        - **Mode legacy** (``writer_scoped=False``, défaut) : retourne
          ``root_path / file_pattern`` — comportement runtime inchangé pour
          tous les consumers, l'helper est un no-op jusqu'à l'activation
          du flag.
        - **Mode scoped** (``writer_scoped=True``) :
            1. Itère :attr:`authority_rules` dans l'ordre de déclaration YAML
            2. Premier ``rule_pattern`` qui matche ``file_pattern`` gagne
            3. Si l'alias résolvable en hash via :meth:`_resolve_writer_alias_to_hash` →
               retourne ``root_path / <hash> / file_pattern``
            4. Si pas de match, ou alias non résolvable → fallback
               ``root_path / file_pattern`` + warning log (le fichier pourrait
               être co-owned racine, ou la config ``.operators.yaml`` incomplète)

        Args:
            file_pattern: Path relatif POSIX-style depuis la racine du repo
                (ex. ``weekly-reports/S094/bilan_final_s094.md``).

        Returns:
            Path absolu résolu. **Le path n'est PAS vérifié pour existence**
            — le caller décide (read-only helper, pas de side effect FS).

        Examples:
            >>> cfg.resolve_read_path("workouts/MyWorkout.zwo")
            PosixPath('/Users/me/training-logs/b08921dae3e7/workouts/MyWorkout.zwo')

            >>> cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
            PosixPath('/Users/me/training-logs/5e6f282f9f03/weekly-reports/S094/bilan_final.md')
        """
        if not self.writer_scoped:
            return self.root_path / file_pattern

        for rule_pattern, writer_alias in self.authority_rules:
            if self._match_authority_pattern(file_pattern, rule_pattern):
                writer_hash = self._resolve_writer_alias_to_hash(writer_alias)
                if writer_hash:
                    return self.root_path / writer_hash / file_pattern
                logger.warning(
                    "authority rule '%s' → alias '%s' but no writer hash "
                    "resolved in .operators.yaml::writers ; falling back to root_path",
                    rule_pattern,
                    writer_alias,
                )
                return self.root_path / file_pattern

        logger.debug(
            "no authority rule matched file_pattern '%s' ; falling back to root_path "
            "(file may be co-owned shared_root_files)",
            file_pattern,
        )
        return self.root_path / file_pattern

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        self.bilans_dir.mkdir(parents=True, exist_ok=True)
        self.week_planning_dir.mkdir(parents=True, exist_ok=True)
        self.workout_templates_dir.mkdir(parents=True, exist_ok=True)
        self.terrain_circuits_dir.mkdir(parents=True, exist_ok=True)
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        self.intelligence_dir.mkdir(parents=True, exist_ok=True)
        self.athlete_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.wellness_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

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
