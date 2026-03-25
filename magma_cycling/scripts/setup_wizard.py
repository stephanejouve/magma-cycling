"""Assistant de configuration interactif pour magma-cycling.

Guide un nouvel utilisateur a travers la configuration complete :
plateforme d'entrainement, profil athlete, espace de donnees, coach IA.

Usage:
    poetry run setup
"""

import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from magma_cycling.scripts.setup.prompts import (
    ask_choice,
    ask_float,
    ask_int,
    ask_secret,
    ask_text,
    ask_yes_no,
    print_error,
    print_info,
    print_step,
    print_success,
)
from magma_cycling.utils.cli import cli_main

TOTAL_STEPS = 6
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _get_version() -> str:
    """Lit la version depuis pyproject.toml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text().splitlines():
            if line.strip().startswith("version"):
                return line.split('"')[1]
    return "?"


def _env_path() -> Path:
    """Chemin du fichier .env."""
    return PROJECT_ROOT / ".env"


def _check_prerequisites() -> bool:
    """Verifie Python >= 3.11 et git installe."""
    ok = True
    if sys.version_info < (3, 11):
        print_error(
            f"Python 3.11+ requis (actuel : {sys.version_info.major}.{sys.version_info.minor})"
        )
        ok = False
    else:
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}")

    if shutil.which("git"):
        print_success("git installe")
    else:
        print_error("git non trouve — installe-le avant de continuer")
        ok = False
    return ok


def _validate_intervals_credentials(athlete_id: str, api_key: str) -> str | None:
    """Teste les credentials Intervals.icu.

    Returns:
        Nom de l'athlete si succes, None sinon.
    """
    auth = base64.b64encode(f"API_KEY:{api_key}".encode()).decode()
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    try:
        resp = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("name") or data.get("athlete", {}).get("name") or athlete_id
        return None
    except requests.RequestException:
        return None


def _category_from_age(age: int) -> str:
    """Deduit la categorie athlete de l'age."""
    if age >= 40:
        return "master"
    if age >= 19:
        return "senior"
    return "junior"


def _build_env_content(config: dict) -> str:
    """Genere le contenu du fichier .env."""
    lines = [
        "# ==============================================",
        "# magma-cycling — Configuration",
        "# Genere par le wizard de configuration",
        "# ==============================================",
        "",
        "# Plateforme d'entrainement (Intervals.icu)",
        f'VITE_INTERVALS_ATHLETE_ID={config["athlete_id"]}',
        f'VITE_INTERVALS_API_KEY={config["api_key"]}',
        "",
        "# Profil athlete",
        f'ATHLETE_AGE={config["age"]}',
        f'ATHLETE_CATEGORY={config["category"]}',
        f'ATHLETE_WEIGHT={config["weight"]}',
        f'ATHLETE_FTP={config["ftp"]}',
        f'ATHLETE_FTP_TARGET={config["ftp_target"]}',
        f'ATHLETE_RECOVERY_CAPACITY={config["recovery"]}',
        f'ATHLETE_SLEEP_DEPENDENT={str(config["sleep_dependent"]).lower()}',
    ]

    # Data repo (seulement si custom)
    data_repo = config.get("data_repo")
    if data_repo and str(data_repo) != str(Path.home() / "training-logs"):
        lines += [
            "",
            "# Espace de donnees",
            f"TRAINING_DATA_REPO={data_repo}",
        ]

    # AI provider
    lines += [
        "",
        "# ==============================================",
        "# Coach IA",
        "# ==============================================",
        f'DEFAULT_AI_PROVIDER={config.get("ai_provider", "clipboard")}',
        "ENABLE_AI_FALLBACK=true",
    ]

    ai_provider = config.get("ai_provider", "clipboard")
    claude_key = config.get("claude_api_key")
    mistral_key = config.get("mistral_api_key")

    if ai_provider == "claude_api" and claude_key:
        lines += [
            f"CLAUDE_API_KEY={claude_key}",
            "# CLAUDE_MODEL=claude-sonnet-4-20250514",
        ]
    else:
        lines += [
            "# CLAUDE_API_KEY=sk-ant-api03-xxxxx",
            "# CLAUDE_MODEL=claude-sonnet-4-20250514",
        ]

    if ai_provider == "mistral_api" and mistral_key:
        lines += [
            f"MISTRAL_API_KEY={mistral_key}",
            "# MISTRAL_MODEL=mistral-large-latest",
        ]
    else:
        lines += [
            "# MISTRAL_API_KEY=xxxxx",
            "# MISTRAL_MODEL=mistral-large-latest",
        ]

    lines += [
        "",
        "# OpenAI (optionnel)",
        "# OPENAI_API_KEY=sk-xxxxx",
        "# OPENAI_MODEL=gpt-4-turbo-preview",
        "",
        "# Ollama local (optionnel)",
        "# OLLAMA_BASE_URL=http://localhost:11434",
        "# OLLAMA_MODEL=mistral:7b",
        "",
        "# ==============================================",
        "# Seuils d'entrainement (modifiables plus tard)",
        "# ==============================================",
        "TSB_FRESH_MIN=10",
        "TSB_OPTIMAL_MIN=-5",
        "TSB_FATIGUED_MIN=-15",
        "TSB_CRITICAL=-25",
        "ATL_CTL_RATIO_OPTIMAL=1.0",
        "ATL_CTL_RATIO_WARNING=1.3",
        "ATL_CTL_RATIO_CRITICAL=1.8",
        "",
        "# MCP Server",
        "MCP_TRANSPORT=stdio",
        "",
    ]
    return "\n".join(lines)


def _build_athlete_yaml(config: dict) -> str:
    """Genere le contenu de athlete_context.yaml."""
    name = config.get("name", "Athlete")
    age = config["age"]
    objective = config.get("objective", "Progression forme generale")
    platform = config.get("platform", "Home trainer (virtuel)")
    constraints_text = config.get("constraints", "")

    constraints_block = ""
    if constraints_text:
        for c in constraints_text.split(","):
            c = c.strip()
            if c:
                constraints_block += f'    - "{c}"\n'
    else:
        constraints_block = '    - "Aucune contrainte specifique"\n'

    return f"""athlete:
  name: "{name}"
  age: {age}
  training_since: "2025-01"
  platform: "{platform}"
  objectives: "{objective}"
  constraints:
{constraints_block.rstrip()}
  system_context: >
    L'athlete utilise un systeme integre avec planification hebdomadaire
    automatisee, suivi sante (sommeil, poids, readiness) et coaching IA
    multi-provider. Ne JAMAIS recommander d'outils externes (Google Sheets,
    TrainingPeaks, coach humain, appli tierce) car le systeme actuel couvre
    ces besoins.
"""


def _init_data_repo(data_repo_path: Path):
    """Initialise l'espace de donnees (git init, fichiers, arborescence)."""
    if data_repo_path.exists() and (data_repo_path / "workouts-history.md").exists():
        print_success(f"Deja en place : {data_repo_path}")
        # Assure quand meme les sous-dossiers
        _ensure_data_directories(data_repo_path)
        return

    data_repo_path.mkdir(parents=True, exist_ok=True)

    # git init
    subprocess.run(["git", "init"], cwd=data_repo_path, capture_output=True)

    # Fichiers de base
    (data_repo_path / "workouts-history.md").write_text(
        "# Historique des seances\n", encoding="utf-8"
    )
    (data_repo_path / ".workflow_state.json").write_text("{}", encoding="utf-8")

    # Arborescence
    _ensure_data_directories(data_repo_path)

    # Commit initial
    subprocess.run(["git", "add", "-A"], cwd=data_repo_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial setup"],
        cwd=data_repo_path,
        capture_output=True,
    )
    print_success(f"Espace de donnees cree : {data_repo_path}")


def _ensure_data_directories(data_repo_path: Path):
    """Cree les sous-dossiers requis (meme logique que DataRepoConfig)."""
    from magma_cycling.config.data_repo import DataRepoConfig

    # Instancie directement avec le chemin — pas besoin du .env
    config = DataRepoConfig(data_repo_path=data_repo_path)
    config.ensure_directories()


def _detect_claude_desktop() -> Path | None:
    """Detecte l'installation de Claude Desktop."""
    candidates = [
        Path.home() / "Library" / "Application Support" / "Claude",
        Path.home() / ".config" / "claude",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


class SetupWizard:
    """Facade du wizard de configuration."""

    def __init__(self):
        """Initialise le wizard."""
        self.config: dict = {}

    def run(self):
        """Execute le wizard complet."""
        self.step_welcome()
        self.step_training_platform()
        self.step_athlete_profile()
        self.step_data_repo()
        self.step_ai_coach()
        self.step_write_and_summary()

    def step_welcome(self):
        """Etape 1 — Bienvenue + prerequis."""
        print_step(1, TOTAL_STEPS, "Bienvenue")

        version = _get_version()
        print(f"  magma-cycling v{version}")
        print("  Assistant de configuration\n")

        if not _check_prerequisites():
            print_error("Prerequis manquants — corrige les erreurs ci-dessus.")
            sys.exit(1)

        if _env_path().exists():
            print()
            if not ask_yes_no("Une configuration existe deja. Reconfigurer ?", default=False):
                print_info("Configuration conservee.")
                sys.exit(0)

        print()
        print_info("Ce wizard va configurer magma-cycling en quelques questions.")
        print_info("Tu peux quitter a tout moment avec Ctrl+C.")

    def step_training_platform(self):
        """Etape 2 — Plateforme d'entrainement."""
        print_step(2, TOTAL_STEPS, "Connexion a ta plateforme d'entrainement")

        print_info(
            "Magma-cycling se connecte a Intervals.icu pour lire tes seances,\n"
            "    ta charge d'entrainement et ton calendrier."
        )
        print_info("Connecte-toi sur intervals.icu → Settings → Developer Settings → API Key\n")

        while True:
            athlete_id = ask_text("Ton identifiant athlete (commence par 'i', ex: i123456)")
            api_key = ask_secret("Ta cle API Intervals.icu")

            print_info("Verification en cours...")
            name = _validate_intervals_credentials(athlete_id, api_key)

            if name:
                print_success(f"Connecte ! Athlete : {name}")
                self.config["athlete_id"] = athlete_id
                self.config["api_key"] = api_key
                self.config["api_name"] = name
                break
            else:
                print_error("Connexion echouee — verifie ton ID et ta cle API.")
                print()

    def step_athlete_profile(self):
        """Etape 3 — Profil athlete."""
        print_step(3, TOTAL_STEPS, "Ton profil cycliste")

        default_name = self.config.get("api_name")
        name = ask_text("Ton prenom ?", default=default_name)
        self.config["name"] = name

        age = ask_int("Ton age ?", min_val=10, max_val=99)
        self.config["age"] = age

        category = _category_from_age(age)
        self.config["category"] = category
        print_info(f"Categorie : {category}")

        weight = ask_float("Ton poids actuel (kg) ?", min_val=30)
        self.config["weight"] = weight

        ftp = ask_int(
            "Ta FTP actuelle (watts) ? Si tu ne sais pas, tape Entree",
            default=150,
            min_val=50,
        )
        self.config["ftp"] = ftp

        ftp_target_default = round(ftp * 1.1)
        ftp_target = ask_int(
            "Ton objectif FTP (watts) ?",
            default=ftp_target_default,
            min_val=ftp,
        )
        self.config["ftp_target"] = ftp_target

        recovery = ask_choice(
            "Comment recuperes-tu entre les seances ?",
            [
                ("normal", "Normalement"),
                ("good", "Bien"),
                ("exceptional", "Tres bien"),
            ],
            default=0,
        )
        self.config["recovery"] = recovery

        sleep_dep = ask_yes_no(
            "Ton sommeil impacte-t-il beaucoup tes performances ?",
            default=True,
        )
        self.config["sleep_dependent"] = sleep_dep

        objective = ask_choice(
            "Ton objectif principal ?",
            [
                ("Progression forme generale", "Forme generale"),
                ("Preparer un evenement", "Preparer un evenement"),
                ("Progresser en puissance", "Progresser en puissance"),
            ],
            default=0,
        )
        self.config["objective"] = objective

        platform = ask_choice(
            "Tu roules sur ?",
            [
                ("Home trainer (virtuel)", "Home trainer"),
                ("Route", "Route"),
                ("Home trainer et route", "Les deux"),
            ],
            default=0,
        )
        self.config["platform"] = platform

        constraints = ask_text(
            "Des contraintes particulieres ? (horaires, sante...)",
            default="",
            required=False,
        )
        self.config["constraints"] = constraints

    def step_data_repo(self):
        """Etape 4 — Espace de donnees (automatique)."""
        print_step(4, TOTAL_STEPS, "Creation de ton espace de donnees")

        env_repo = os.getenv("TRAINING_DATA_REPO")
        if env_repo:
            data_repo_path = Path(env_repo).expanduser()
        else:
            data_repo_path = Path.home() / "training-logs"

        self.config["data_repo"] = data_repo_path
        _init_data_repo(data_repo_path)

    def step_ai_coach(self):
        """Etape 5 — Coach IA (optionnel)."""
        print_step(5, TOTAL_STEPS, "Configuration du coach IA")

        provider = ask_choice(
            "Comment veux-tu utiliser l'analyse IA ?",
            [
                ("clipboard", "Mode manuel — tu copieras les analyses vers ton IA prefere"),
                ("claude_api", "Claude API — analyse automatique via Claude"),
                ("mistral_api", "Mistral API — alternative economique"),
            ],
            default=0,
        )
        self.config["ai_provider"] = provider

        if provider == "claude_api":
            print_info("Cle API disponible sur console.anthropic.com\n")
            key = ask_secret("Ta cle API Claude")
            self.config["claude_api_key"] = key
        elif provider == "mistral_api":
            print_info("Cle API disponible sur console.mistral.ai\n")
            key = ask_secret("Ta cle API Mistral")
            self.config["mistral_api_key"] = key

    def step_write_and_summary(self):
        """Etape 6 — Ecriture des fichiers + resume."""
        print_step(6, TOTAL_STEPS, "Finalisation")

        # 1. Ecrire .env
        env_content = _build_env_content(self.config)
        _env_path().write_text(env_content, encoding="utf-8")
        print_success(".env cree")

        # 2. Ecrire athlete_context.yaml (avec backup)
        yaml_path = PROJECT_ROOT / "magma_cycling" / "config" / "athlete_context.yaml"
        if yaml_path.exists():
            backup_path = yaml_path.with_suffix(".yaml.bak")
            shutil.copy2(yaml_path, backup_path)
            print_info(f"Backup : {backup_path.name}")
        yaml_content = _build_athlete_yaml(self.config)
        yaml_path.write_text(yaml_content, encoding="utf-8")
        print_success("athlete_context.yaml genere")

        # 3. Resume
        print("\n  ── Resume ──\n")
        print_success(f"Athlete    : {self.config.get('name')}")
        print_success(f"Categorie  : {self.config['category']}")
        print_success(f"FTP        : {self.config['ftp']}W → objectif {self.config['ftp_target']}W")
        print_success(f"Plateforme : {self.config.get('platform')}")
        print_success(f"Coach IA   : {self.config.get('ai_provider', 'clipboard')}")
        print_success(f"Donnees    : {self.config.get('data_repo')}")

        # 4. MCP Claude Desktop
        claude_path = _detect_claude_desktop()
        if claude_path:
            print("\n  ── Integration Claude Desktop detectee ──\n")
            print_info("Ajoute ce bloc dans ta config MCP :\n")
            cwd = str(PROJECT_ROOT)
            print(
                f"""    {{
      "mcpServers": {{
        "magma-cycling": {{
          "command": "poetry",
          "args": ["run", "mcp-server"],
          "cwd": "{cwd}"
        }}
      }}
    }}"""
            )
        else:
            print_info("\nClaude Desktop non detecte — tu pourras configurer le MCP plus tard.")

        # 5. Prochaines etapes
        print("\n  ── Prochaines etapes ──\n")
        print_info("Lance `poetry run daily-sync` pour ta premiere synchronisation")
        print_info("Pour connecter une balance/montre : `poetry run setup-withings`")
        print()


@cli_main
def main():
    """Point d'entree du wizard de configuration."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
