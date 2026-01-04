# Cyclisme Training Logs

[![Tests](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/tests.yml/badge.svg)](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/tests.yml)
[![Lint](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/lint.yml/badge.svg)](https://github.com/stephanejouve/cyclisme-training-logs/actions/workflows/lint.yml)
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

---

## 🎯 Usage

### CLI Commands

**Training Intelligence:**
```bash
# Backfill intelligence from historical data (2024-2025)
poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31 --output ~/data/intelligence.json

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
- **[CHANGELOG.md](project-docs/CHANGELOG.md)** - Historique versions
- **[ARCHITECTURE.md](project-docs/architecture/)** - Architecture système
- **[WORKFLOWS/](project-docs/workflows/)** - Workflow diagrams (GRAFCET, UML)

**Sprints & Validation** (`project-docs/sprints/`):
- **[SPRINT_R4PP_VALIDATION_MOA.md](project-docs/sprints/)** - Sprint R4++ (120/100) ✅
- Sprint reports, MOA validations

---

## 🧪 Development

### Run Tests

```bash
# All tests (497 tests including integration tests)
poetry run pytest tests/ -v

# Unit tests only (326 tests - what CI runs)
poetry run pytest tests/config/ tests/intelligence/ tests/planning/ tests/test_ai_providers/ tests/utils/ -v

# Specific module
poetry run pytest tests/intelligence/ -v
poetry run pytest tests/planning/ -v

# With coverage
poetry run pytest tests/ -v --cov=cyclisme_training_logs --cov-report=html
# Open htmlcov/index.html in browser
```

**Note**: CI/CD runs unit tests only (326 tests). Full test suite (497 tests) includes integration tests requiring local data files and API access.

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

---

## 🏗️ Architecture

```
cyclisme-training-logs/
├── cyclisme_training_logs/      # Code production
│   ├── intelligence/            # Training Intelligence (learnings, PID)
│   ├── planning/                # Planning Manager (weekly planner)
│   ├── analyzers/               # Weekly/daily aggregators
│   ├── api/                     # Intervals.icu client
│   ├── workflows/               # Workflow orchestration
│   ├── ai_providers/            # Multi-AI support (OpenAI, Claude, etc.)
│   ├── scripts/                 # CLI scripts (backfill, etc.)
│   └── ...
├── tests/                       # Tests (unit + integration)
│   ├── intelligence/            # Intelligence tests (44 tests)
│   ├── planning/                # Planning tests
│   ├── integration/             # Integration tests
│   └── ...
├── project-docs/                # Documentation
│   ├── guides/                  # User guides
│   ├── sprints/                 # Sprint reports
│   ├── workflows/               # Workflow diagrams
│   └── architecture/            # Architecture docs
└── pyproject.toml               # Poetry config + CLI entry points
```

---

## 📊 Version

**Current:** v2.1.1 (2026-01-02)

**Recent Releases:**
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
