# Magma Cycling

[![CI](https://github.com/stephanejouve/magma-cycling/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/stephanejouve/magma-cycling/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/stephanejouve/magma-cycling/branch/main/graph/badge.svg?token=K39R7YEOPN)](https://codecov.io/gh/stephanejouve/magma-cycling)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue)](https://python-poetry.org/)
[![Quality](https://img.shields.io/badge/Quality-Production%20Ready-brightgreen)](CODING_STANDARDS.md)
[![MCP Tools](https://img.shields.io/badge/MCP_tools-50-8A2BE2)](magma_cycling/_mcp/)

A personal cycling training log system integrating Intervals.icu, AI coaching, and structured workout management.

---

## Quick Start

```bash
git clone https://github.com/stephanejouve/magma-cycling.git
cd magma-cycling
poetry install
poetry run setup          # interactive wizard — creates .env, athlete profile, data repo
poetry run workflow-coach
```

---

## Features

**Monitoring & Adherence**
- Automatic workout adherence tracking with risk scoring (0-100)
- Day-of-week pattern detection
- 21-day baseline analysis with actionable insights
- Daily sync with Intervals.icu (CLI command)
- End-of-week automated planning (CLI command)
- Optional scheduling via cron (Linux/Windows) or LaunchAgents (macOS)

**Training Intelligence**
- Progressive learning system: confidence levels LOW → MEDIUM → HIGH → VALIDATED
- Recurring pattern identification from historical data
- Protocol adaptations based on past performance
- Backfill from 2+ years of Intervals.icu history
- PID controller for adaptive FTP progression (Kp/Ki/Kd)

**Analysis & Planning**
- Weekly analysis: TSS, IF, zones, recovery scoring
- Monthly trends and FTP progression
- Weekly planner: TSS-targeted sessions with recovery logic
- Planning manager: athlete constraints, calendar logic, validation

**Intervals.icu Integration**
- Bidirectional sync: upload workouts, fetch activities and wellness data
- Event management: create, update, cancel sessions (with NOTE sync)
- Full API client: activities, events, wellness, athlete profile

**Multi-AI Support**
- Providers: OpenAI, Anthropic Claude, Mistral, Ollama
- Clipboard fallback (zero API cost)
- Workflow Coach orchestration pipeline

---

## Providers & compatibilité

Magma-cycling s'intègre à des services externes pour la planification, le suivi santé et le coaching IA. Le système est conçu pour être agnostique — les noms de marque n'apparaissent que dans les implémentations concrètes.

### Services intégrés

| Fonction | Provider | Statut |
|---|---|---|
| Plateforme d'entraînement | [Intervals.icu](https://intervals.icu) | Testé en prod |
| Suivi santé / sommeil | [Withings](https://www.withings.com) | Testé en prod |
| Workouts indoor | [Zwift](https://www.zwift.com) (scraping catalogue) | Testé en prod |
| Coach IA | Claude — Anthropic | Testé en prod |
| Coach IA | Mode manuel (clipboard) | Testé en prod |
| Coach IA | Mistral AI | Intégré, non testé en prod |
| Coach IA | OpenAI | Intégré, non testé en prod |
| Coach IA | Ollama (local) | Intégré, non testé en prod |

### Matériel testé

Matériel validé par l'auteur — les données transitent correctement du capteur vers Intervals.icu puis vers magma-cycling.

| Type | Modèle |
|---|---|
| Capteur sommeil | Withings Sleep Analyser (sous-matelas) |
| Ordinateur vélo | Wahoo ROAM V3, ROAM V2 |
| Capteur puissance | Wahoo POWRLINK ZERO |
| Radar | Garmin Varia RTL515 |
| Indoor | Apple TV + Zwift Companion |

> Ce tableau reflète uniquement ce qui a été testé en conditions réelles. Tout appareil compatible Intervals.icu devrait fonctionner — les contributions pour élargir cette liste sont bienvenues via issues GitHub.

---

## Installation

**Requirements:** Python 3.11+, [Poetry](https://python-poetry.org/)

```bash
# Install Poetry (macOS/Linux)
curl -sSL https://install.python-poetry.org | python3 -

# Clone and install
git clone https://github.com/stephanejouve/magma-cycling.git
cd magma-cycling
poetry install
```

### Configuration

Le wizard interactif configure tout automatiquement :

```bash
poetry run setup
```

Il crée le `.env`, le profil athlète (`athlete_context.yaml`), l'espace de données (`~/training-logs/`), et valide la connexion à Intervals.icu en direct.

<details>
<summary>Configuration manuelle (alternative)</summary>

Créer un fichier `.env` à la racine du projet (voir `.env.example`) :

```bash
# Intervals.icu API (obligatoire)
VITE_INTERVALS_ATHLETE_ID=your_athlete_id
VITE_INTERVALS_API_KEY=your_api_key_here

# Profil athlète
ATHLETE_AGE=40
ATHLETE_FTP=200
ATHLETE_WEIGHT=75
ATHLETE_CATEGORY=master
ATHLETE_RECOVERY_CAPACITY=normal
ATHLETE_SLEEP_DEPENDENT=true

# Coach IA (optionnel — défaut : clipboard)
DEFAULT_AI_PROVIDER=clipboard
# CLAUDE_API_KEY=sk-ant-api03-xxxxx
# MISTRAL_API_KEY=xxxxx
```

**Credentials Intervals.icu :** Settings → Developer Settings → Generate API key. L'athlete ID apparaît dans l'URL : `https://intervals.icu/athlete/your_athlete_id/...`

</details>

> All `.env` variables must be accessed through `magma_cycling/config.py`. Direct env reading in individual modules is prohibited.

---

## Usage

### CLI Commands

**Workflow:**
```bash
poetry run workflow-coach                        # full coaching pipeline
```

**Analysis:**
```bash
poetry run weekly-analysis --week 67
poetry run monthly-analysis --month 2026-01
```

**Monitoring & Adherence:**
```bash
poetry run check-workout-adherence --week S078
poetry run baseline-analysis --start-date 2026-01-05 --days 21
poetry run pattern-analysis --data ~/data/monitoring/workout_adherence.jsonl
```

**Planning:**
```bash
poetry run weekly-planner --week 2026-W01 --target-tss 350
poetry run upload-workouts --file workouts/W01-01.zwo
```

**Session Management:**
```bash
# Cancel a session and sync to Intervals.icu as NOTE [ANNULÉE]
poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue" --sync

# Skip a session
poetry run update-session --week S074 --session S074-03 --status skipped --reason "Travel" --sync

# Mark completed
poetry run update-session --week S074 --session S074-01 --status completed
```

**Training Intelligence:**
```bash
poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31 --output ~/data/intelligence.json
poetry run pid-daily-evaluation --days-back 7
```

**All commands:**
```bash
poetry run --help
# Lists: weekly-analysis, monthly-analysis, upload-workouts, workflow-coach,
#        backfill-intelligence, weekly-planner, update-session, sync-intervals, and more
```

---

## Architecture

```
magma-cycling/
├── magma_cycling/      # Production code
│   ├── intelligence/            # Training intelligence (learnings, PID)
│   ├── monitoring/              # Adherence monitoring, pattern analysis
│   ├── planning/                # Planning manager, weekly planner
│   ├── analyzers/               # Weekly/daily aggregators
│   ├── api/                     # Intervals.icu client
│   ├── workflows/               # Workflow orchestration
│   ├── ai_providers/            # Multi-AI support
│   ├── scripts/                 # CLI entry points
│   └── config.py                # Centralized configuration
├── scripts/
│   ├── launchagents/            # Optional macOS scheduling agents
│   └── monitoring/              # Monitoring automation helpers
├── tests/                       # Unit + integration tests
│   ├── intelligence/
│   ├── monitoring/
│   ├── planning/
│   └── integration/
├── project-docs/                # Guides, roadmap, changelogs, architecture
└── pyproject.toml               # Poetry config and CLI entry points
```

---

## Development

### Tests

```bash
# Full test suite
poetry run pytest tests/ -v

# Unit tests only (what CI runs)
poetry run pytest tests/config/ tests/intelligence/ tests/planning/ tests/test_ai_providers/ tests/utils/ -v

# Specific module
poetry run pytest tests/monitoring/ -v
poetry run pytest tests/workflows/ -v

# With coverage
poetry run pytest tests/ --cov=magma_cycling --cov-report=html
```

### Code Quality

```bash
poetry run ruff check magma_cycling/   # lint
poetry run black magma_cycling/        # format
poetry run mypy magma_cycling/         # type check
poetry run poe check                            # all checks (format, lint, types, tests)
```

### Pre-commit Hooks (recommended)

```bash
pip install pre-commit
pre-commit install
# Runs: black, isort, ruff, detect-secrets on each commit
```

### Standards

Before contributing, read:

- **[CODING_STANDARDS.md](CODING_STANDARDS.md)** — Docstrings (PEP 257 / Google style), imperative mood (D401), period-ending first lines (D400/D415), required for all public symbols.
- **[COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md)** — Format: `<type>(<scope>): <description> [ROADMAP@<sha>]`. Reference ROADMAP SHA in sprint commits.
- **Configuration rule** — All `.env` access goes through `config.py`. Never read `.env` directly in modules.

```bash
# Get current ROADMAP SHA for commit messages
git log -1 --format=%h project-docs/ROADMAP.md
```

---

## Documentation

User guides in `project-docs/guides/`:
- [GUIDE_INTELLIGENCE.md](project-docs/guides/GUIDE_INTELLIGENCE.md) — Learnings, patterns, PID controller, backfill
- [GUIDE_PLANNING.md](project-docs/guides/GUIDE_PLANNING.md) — Weekly planner, constraints, calendar logic
- [GUIDE_WEEKLY_ANALYSIS.md](project-docs/guides/GUIDE_WEEKLY_ANALYSIS.md) — Weekly analysis workflow
- [GUIDE_UPLOAD_WORKOUTS.md](project-docs/guides/GUIDE_UPLOAD_WORKOUTS.md) — Workout upload to Intervals.icu

Technical docs in `project-docs/`:
- [ROADMAP.md](project-docs/ROADMAP.md) — Project roadmap
- [CHANGELOG.md](project-docs/CHANGELOG.md) — Version history
- [COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md) — Git commit traceability
- [architecture/](project-docs/architecture/) — System architecture
- [workflows/](project-docs/workflows/) — Workflow diagrams (GRAFCET, UML)

---

## Contributing

Pull requests are welcome for bug fixes and feature improvements.

Before submitting:
1. Read [Development Standards](#development) above
2. Run `poetry run poe check` and ensure all checks pass
3. Use the commit convention format from [COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md)
4. Open an issue first for significant changes

---

## License

MIT License (code) — see [LICENSE](LICENSE) for details.

© 2025-2026 Stéphane Jouve
