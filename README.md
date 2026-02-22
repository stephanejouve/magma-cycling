# Cyclisme Training Logs

[![CI](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/stephanejouve/cyclisme-training-logs/branch/main/graph/badge.svg)](https://codecov.io/gh/stephanejouve/cyclisme-training-logs)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue)](https://python-poetry.org/)
[![Architecture Review](https://img.shields.io/badge/Architecture%20Review-10%2F10-brightgreen)](project-docs/ARCHITECTURE_REVIEW_20260104.md)
[![Quality](https://img.shields.io/badge/Quality-Production%20Ready-brightgreen)](CODING_STANDARDS.md)

**Système automatisé d'analyse et planification d'entraînements cyclisme avec intelligence artificielle.**

> ⭐ **Architecture de Référence** - Validation externe 10/10 (tous axes) - [Voir rapport complet](project-docs/ARCHITECTURE_REVIEW_20260104.md)

---

## ⚡ Quick Start (30 secondes)

```bash
# Clone repository
git clone https://github.com/stephanejouve/cyclisme-training-logs.git
cd cyclisme-training-logs

# Install dependencies
poetry install

# Configure Intervals.icu credentials (create .env file)
cp .env.example .env  # Edit with your API key and athlete ID

# Run workflow coach
poetry run workflow-coach
```

**That's it!** Vous êtes prêt à analyser votre entraînement.

---

## 🚀 Features

### 🤖 Automation & Monitoring (Sprint R9 - NEW!)
- **Adherence monitoring** : Surveillance automatique adherence workouts (CLI + optional automation)
- **Pattern analysis** : Détection patterns jour semaine, risk scoring 0-100
- **Baseline analysis** : Analyse 21 jours adherence, TSS, patterns
- **PID evaluation** : Intelligence AI 7 jours - génération learnings/patterns/adaptations
- **Daily-sync automation** : Sync quotidien Intervals.icu (CLI command)
- **End-of-week automation** : Planning hebdomadaire automatique (CLI command)
- **Baseline established** : 77.8% adherence (14/18 workouts), 4 insights actionnables
- **LaunchAgents** _(macOS only, optional)_ : Automation via 7 agents (scripts/launchagents/)

### 🧠 Training Intelligence
- **Apprentissage progressif** : Learnings avec confidence LOW → MEDIUM → HIGH → VALIDATED
- **Pattern detection** : Identification automatique patterns récurrents
- **Protocol adaptations** : Adaptations protocoles basées sur données historiques
- **Multi-temporal insights** : Daily, weekly, monthly analysis
- **Backfill historique** : Extraction learnings depuis 2+ ans de données Intervals.icu

### 📊 Analysis & Planning
- **Weekly Analysis** : Analyse hebdomadaire complète (TSS, IF, zones, recovery)
- **Monthly Analysis** : Trends long terme, progression FTP
- **Weekly Planner** : Génération plans semaine optimisés (TSS target, recovery)
- **Planning Manager** : Contraintes athlète, calendar logic, validation
- **PID Controller** : Contrôle adaptatif progression FTP (gains Kp/Ki/Kd dynamiques)

### 🔄 Intervals.icu Integration
- **Sync bidirectionnel** : Upload workouts, fetch activities/wellness
- **Event management** : Create, update, cancel sessions (avec sync NOTE)
- **API client** : IntervalsClient complet (activities, events, wellness, athlete profile)
- **Data aggregation** : Weekly/daily aggregators avec métriques avancées

### 🤖 Multi-AI Support
- **4 AI providers** : OpenAI, Claude, Mistral, Ollama
- **Clipboard fallback** : 0 API cost (copie/colle manuel)
- **Workflow orchestration** : Workflow Coach pipeline complet

### 📅 Optional: LaunchAgents Automation _(macOS only)_
**Note**: All features work via CLI commands. LaunchAgents provide optional scheduling on macOS.

For macOS users wanting automatic scheduling:
- **7 agents available** in `scripts/launchagents/` with setup instructions
- Automate: daily-sync (21:30), adherence check (22:00), PID evaluation (23:00), end-of-week (Sun 20:00)
- **Other platforms**: Use cron (Linux) or Task Scheduler (Windows) with same CLI commands

---

## 📦 Installation

### Requirements
- **Python 3.11+**
- **Poetry** (package manager)
- **Intervals.icu account** (optional, for sync features)

### Install Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Install Project

```bash
git clone https://github.com/stephanejouve/cyclisme-training-logs.git
cd cyclisme-training-logs
poetry install
```

### Configure Credentials

Create `.env` file at project root:

```bash
# Intervals.icu API
VITE_INTERVALS_ATHLETE_ID=i151223
VITE_INTERVALS_API_KEY=your_api_key_here

# Email (for daily-sync --send-email)
BREVO_API_KEY=your_brevo_api_key_here
EMAIL_TO=your.email@example.com
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Training Logs

# AI Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
OLLAMA_URL=http://localhost:11434
```

**Get Intervals.icu credentials:**
1. Login to [intervals.icu](https://intervals.icu)
2. Go to Settings → Developer Settings
3. Generate API key
4. Your athlete ID is in URL: `https://intervals.icu/athlete/i151223/...`

**Get Brevo (email) credentials (optional - for daily-sync email reports):**
1. Create free account at [brevo.com](https://www.brevo.com) (ex-Sendinblue)
2. Go to Settings → SMTP & API → API Keys
3. Generate API key (v3)
4. Configure sender email (must be verified)
5. Add `BREVO_API_KEY`, `EMAIL_TO`, `EMAIL_FROM` to `.env`

**⚙️ Code Quality Standards:**
All `.env` variables MUST be accessed through `cyclisme_training_logs/config.py`. Direct reading of `.env` files by individual modules is prohibited. This ensures centralized configuration management, type safety, and easier testing.

---

## 🎯 Usage

### CLI Commands

**Monitoring & Adherence:**
```bash
# Check workout adherence (run manually or schedule via cron/LaunchAgents)
poetry run check-workout-adherence --week S078

# View adherence baseline data
cat ~/data/monitoring/workout_adherence.jsonl | jq '.'

# Generate baseline analysis (21 days)
poetry run baseline-analysis --start-date 2026-01-05 --days 21

# Pattern analysis with risk scoring
poetry run pattern-analysis --data ~/data/monitoring/workout_adherence.jsonl
```

**Training Intelligence:**
```bash
# Backfill intelligence from historical data (2024-2025)
poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31 --output ~/data/intelligence.json

# Daily PID evaluation (runs automatically at 23h00)
poetry run pid-daily-evaluation --days-back 7

# View learnings
python -c "from cyclisme_training_logs.intelligence import TrainingIntelligence; ti = TrainingIntelligence.load_from_file('intelligence.json'); print([l.description for l in ti.learnings.values()])"
```

**Planning:**
```bash
# Generate weekly plan
poetry run weekly-planner --week 2026-W01 --target-tss 350

# Upload workouts to Intervals.icu
poetry run upload-workouts --file workouts/W01-01.zwo
```

**Analysis:**
```bash
# Weekly analysis (AI-powered)
poetry run weekly-analysis --week 67

# Monthly analysis
poetry run monthly-analysis --month 2026-01
```

**Session Management:**
```bash
# Cancel session (sync to Intervals.icu as NOTE [ANNULÉE])
poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue" --sync

# Skip session (sync as NOTE [SAUTÉE])
poetry run update-session --week S074 --session S074-03 --status skipped --reason "Voyage" --sync

# Mark completed
poetry run update-session --week S074 --session S074-01 --status completed
```

**Workflow:**
```bash
# Run complete workflow coach
poetry run workflow-coach
```

**All available commands:**
```bash
poetry run --help
# Lists: weekly-analysis, monthly-analysis, upload-workouts, workflow-coach,
#        backfill-intelligence, weekly-planner, update-session, sync-intervals,
#        and more...
```

---

## 📖 Documentation

**Guides Utilisateur** (`project-docs/guides/`):
- **[GUIDE_INTELLIGENCE.md](project-docs/guides/GUIDE_INTELLIGENCE.md)** - Training Intelligence (1692 lignes, v2.2.0)
  - Learnings, Patterns, Adaptations
  - Backfill historique (4 analyses)
  - PID Controller adaptatif
- **[GUIDE_PLANNING.md](project-docs/guides/GUIDE_PLANNING.md)** - Planning Manager
  - Weekly planner
  - Constraints management
  - Calendar logic
- **[GUIDE_WEEKLY_ANALYSIS.md](project-docs/guides/GUIDE_WEEKLY_ANALYSIS.md)** - Analyse hebdomadaire
- **[GUIDE_UPLOAD_WORKOUTS.md](project-docs/guides/GUIDE_UPLOAD_WORKOUTS.md)** - Upload workouts
- **[GUIDE_COMMIT_GITHUB.md](project-docs/guides/GUIDE_COMMIT_GITHUB.md)** - Git workflow

**Technical Docs** (`project-docs/`):
- **[ROADMAP.md](project-docs/ROADMAP.md)** - Roadmap projet (Sprint R9-R13, Phase 3)
- **[COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md)** - Convention traçabilité commits
- **[CHANGELOG.md](project-docs/CHANGELOG.md)** - Historique versions
- **[ARCHITECTURE.md](project-docs/architecture/)** - Architecture système
- **[WORKFLOWS/](project-docs/workflows/)** - Workflow diagrams (GRAFCET, UML)
- **[LaunchAgents/](scripts/launchagents/)** - Automation setup (7 agents)

**Sprints & Validation** (`project-docs/sprints/`):
- **[SPRINT_R4PP_VALIDATION_MOA.md](project-docs/sprints/)** - Sprint R4++ (120/100) ✅
- Sprint reports, MOA validations

---

## 🧪 Development

### Run Tests

```bash
# All tests (636+ tests including integration tests)
poetry run pytest tests/ -v

# Unit tests only (364+ tests - what CI runs)
poetry run pytest tests/config/ tests/intelligence/ tests/planning/ tests/test_ai_providers/ tests/utils/ -v

# Specific module
poetry run pytest tests/intelligence/ -v
poetry run pytest tests/planning/ -v
poetry run pytest tests/api/ -v  # Di2 tests (6 tests)
poetry run pytest tests/workflows/ -v  # Upload tests (32 tests)

# With coverage
poetry run pytest tests/ -v --cov=cyclisme_training_logs --cov-report=html
# Open htmlcov/index.html in browser

# Coverage report
poetry run pytest tests/ --cov=cyclisme_training_logs --cov-report=term
```

**Test Suite v3.0.0:**
- **636+ tests total** (634+ passed)
- **38 new tests** (v3.0.0): Monitoring & baseline analysis
  - Adherence monitoring: 15 tests
  - Pattern analysis: 12 tests (risk scoring, day-of-week patterns)
  - Baseline analysis: 11 tests (21-day baseline validation)
- **54 tests** (v2.3.1): Di2 analysis + upload_workouts
  - API Di2: 6 tests, Analyzers: 9 tests, Workflows: 32 tests, Integration: 8 tests
- **Coverage: 30%** overall (improvement from 29%)
  - Core modules: 90-100% (utils, intelligence, planning)
  - Monitoring modules: 84% (adherence, patterns, baseline)
  - Di2 modules: 53-72% (upload_workouts, intervals_client)

**Note**: CI/CD runs unit tests only (364+ tests). Full test suite includes integration tests requiring local data files and API access.

### Code Quality

```bash
# Linting
poetry run ruff check cyclisme_training_logs/

# Formatting
poetry run black cyclisme_training_logs/

# Type checking
poetry run mypy cyclisme_training_logs/

# All checks
poetry run poe check  # Runs format-check, lint, type-check, test
```

### Pre-commit Hooks (optional)

```bash
# Install pre-commit hooks (auto-format, auto-lint before commit)
pip install pre-commit
pre-commit install
```

### 📜 Development Standards & Conventions

**REQUIRED READING** before contributing to this project:

1. **[CODING_STANDARDS.md](CODING_STANDARDS.md)** - Production code quality standards
   - ✅ Docstrings: PEP 257 + Google Style (OBLIGATOIRE)
   - ✅ Imperative mood for functions (D401)
   - ✅ Period ending first line (D400/D415)
   - ✅ Public modules/classes/functions must have docstrings

2. **[COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md)** - Git commit traceability
   - ✅ Format: `<type>(<scope>): <description> [ROADMAP@<sha>]`
   - ✅ Reference ROADMAP version in all sprint-related commits
   - ✅ Use scope: `(R9.A)`, `(R10)`, `(S080)`, `(roadmap)`
   - ✅ Include `Refs:` and `ROADMAP commit:` in body

3. **Configuration Management (Code Quality)**
   - ✅ ALL `.env` variables MUST be accessed through `cyclisme_training_logs/config.py`
   - ❌ Direct reading of `.env` files by modules is PROHIBITED
   - ✅ Ensures centralized config, type safety, testability

4. **Pre-commit Hooks** (recommended)
   - Automatic formatting (black, isort)
   - Linting (ruff)
   - Security checks (detect-secrets)
   - See installation above

**Quick Command**:
```bash
# Get current ROADMAP SHA for commits
git log -1 --format=%h project-docs/ROADMAP.md
```

---

## 🏗️ Architecture

```
cyclisme-training-logs/
├── cyclisme_training_logs/      # Code production
│   ├── intelligence/            # Training Intelligence (learnings, PID)
│   ├── monitoring/              # Adherence monitoring, pattern analysis (NEW v3.0.0)
│   ├── planning/                # Planning Manager (weekly planner)
│   ├── analyzers/               # Weekly/daily aggregators
│   ├── api/                     # Intervals.icu client
│   ├── workflows/               # Workflow orchestration
│   ├── ai_providers/            # Multi-AI support (OpenAI, Claude, etc.)
│   ├── scripts/                 # CLI scripts (backfill, pid-evaluation, etc.)
│   └── ...
├── scripts/                     # Automation scripts
│   ├── launchagents/            # Optional: macOS LaunchAgents setup (NEW v3.0.0)
│   └── monitoring/              # Monitoring automation scripts
├── tests/                       # Tests (unit + integration)
│   ├── intelligence/            # Intelligence tests (44 tests)
│   ├── monitoring/              # Monitoring tests (38 tests) (NEW v3.0.0)
│   ├── planning/                # Planning tests
│   ├── integration/             # Integration tests
│   └── ...
├── project-docs/                # Documentation
│   ├── guides/                  # User guides
│   ├── sprints/                 # Sprint reports
│   ├── workflows/               # Workflow diagrams
│   ├── architecture/            # Architecture docs
│   └── ROADMAP.md               # Roadmap projet (NEW v3.0.0)
└── pyproject.toml               # Poetry config + CLI entry points
```

---

## 📊 Version

**Current:** v3.0.0 (2026-01-25) 🚀

**Recent Releases:**
- **v3.0.0** (2026-01-25) - **Sprint R9 Complete & ROADMAP Reorganization** 🎯
  - Sprint R9.A-F: Monitoring & Baseline Analysis (04-25 Jan)
  - LaunchAgents architecture (7 agents productifs, auto-migration)
  - Adherence baseline 77.8% (14/18 workouts)
  - Pattern analysis avec risk scoring
  - ROADMAP reorganization + Commit conventions
  - 206 commits, 38 tests, 84% coverage modules monitoring
  - [Release Notes](https://github.com/stephanejouve/cyclisme-training-logs/releases/tag/v3.0.0)
- **v2.3.1** - Di2 Analysis + Tests (54 tests, coverage +1%, upload_workouts +53%)
- **v2.2.0** - Sprint R4++ (Training Intelligence + Backfill + PID) - 120/100 MOA
- **v2.1.1** - Intervals.icu Sync Fix (session cancellation → NOTE)
- **v2.1.0** - Sprint R4 (Training Intelligence & Feedback Loop)
- **v2.0.0** - Sprint R3 (Planning Manager)

See [CHANGELOG.md](project-docs/CHANGELOG.md) for complete history.

---

## 🤝 Contributing

**Project Status:** Active development, personal use

**Pull Requests:** Welcome for bug fixes, feature enhancements

**Issues:** Use GitHub Issues for bug reports, feature requests

**Before Contributing:**
- 📜 **READ** [Development Standards & Conventions](#-development-standards--conventions) section
- ✅ Follow [CODING_STANDARDS.md](CODING_STANDARDS.md) for all production code
- ✅ Use [COMMIT_CONVENTIONS.md](project-docs/COMMIT_CONVENTIONS.md) for git commits
- ✅ Access `.env` variables ONLY through `config.py`
- 🔍 Run `poetry run poe check` before submitting PR

---

## 📝 License

**Propriétaire - Usage personnel**

© 2024-2026 Stéphane Jouve

---

## 🙏 Acknowledgments

- **Intervals.icu** - Training platform & API
- **Anthropic Claude** - AI analysis
- **OpenAI** - AI providers
- **Python Poetry** - Dependency management

---

**Questions?** Open an issue or check [documentation](project-docs/guides/)

**Need help?** See [GUIDE_INTELLIGENCE.md](project-docs/guides/GUIDE_INTELLIGENCE.md) for detailed usage
