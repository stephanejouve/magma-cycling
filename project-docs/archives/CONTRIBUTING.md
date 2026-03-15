# Contributing to Cyclisme Training Logs

Thank you for contributing to Cyclisme Training Logs! This guide will help you get started.

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or 3.12
- Poetry (dependency management)
- Git

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/stephanejouve/magma-cycling.git
cd magma-cycling

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

## Workflow Git — règles obligatoires

### Après chaque rebase ou merge

Toujours relancer l'environnement Poetry avant de lancer les tests :

```bash
# 1. Synchroniser l'environnement (évite les erreurs pydantic/pydantic-core)
poetry install --sync

# 2. Vérifier que tout passe
poetry run pytest tests/ -x --ignore=tests/reports -q

# 3. Vérifier pre-commit
poetry run pre-commit run --all-files
```

> **Ne pas sauter le `poetry install --sync`** — les dépendances peuvent se
> désynchroniser silencieusement après un rebase, notamment pydantic et pydantic-core.

### Si pydantic-core casse après un rebase

Cause : dossier corrompu `typing_extensions-4.15.0 2.dist-info`
(espace dans le nom) dans le venv qui corrompt pip.

Fix :

```bash
rm -rf ".venv/lib/python3.13/site-packages/typing_extensions-4.15.0 2.dist-info"
poetry run pip install --force-reinstall --no-deps pydantic-core
poetry run python -c "import pydantic_core; print(pydantic_core.__version__)"
# doit afficher 2.42.0
```

## 🔄 Development Workflow

### 1. Create a Branch

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b fix/bug-description
```

### 2. Make Changes

Write your code following our [coding standards](CODING_STANDARDS.md).

### 3. Run Tests Locally

```bash
# Unit tests only (326 tests - what CI runs)
poetry run pytest tests/config/ tests/intelligence/ tests/planning/ tests/test_*.py -v

# All tests including integration (598 tests)
poetry run pytest tests/ -v

# With coverage
poetry run pytest tests/ --cov=magma_cycling --cov-report=html
```

### 4. Format and Lint

Pre-commit hooks will automatically run on commit, but you can run them manually:

```bash
# Format code
poetry run black magma_cycling/ tests/

# Lint
poetry run ruff check magma_cycling/ --fix

# Sort imports
poetry run isort magma_cycling/ tests/

# Check docstrings
poetry run pydocstyle magma_cycling/

# Type check
poetry run mypy magma_cycling/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: Your feature description"
```

**Commit Message Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test changes
- `refactor`: Code refactoring
- `chore`: Build/tooling changes
- `perf`: Performance improvements

**Examples:**
```bash
feat(workflow): Add AI provider fallback mechanism
fix(upload): Handle missing dashes in workout notation
docs(readme): Update test coverage statistics
test(coach): Add workflow orchestration tests
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## 🤖 Continuous Integration (CI/CD)

### Automated Checks

Every push and pull request triggers our CI/CD pipeline:

#### Test Job (Python 3.11 & 3.12)

- **Unit Tests**: 326 core tests
- **Coverage**: Reported to Codecov
- **Matrix**: Tests run on both Python versions

#### Lint Job

- **Black**: Code formatting check
- **Ruff**: Fast Python linter
- **isort**: Import sorting check
- **mypy**: Type checking (non-blocking)
- **pydocstyle**: Docstring style (non-blocking)

#### Security Job

- **Safety**: Dependency vulnerability scan

### CI Status

[![CI](https://github.com/stephanejouve/magma-cycling/actions/workflows/ci.yml/badge.svg)](https://github.com/stephanejouve/magma-cycling/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/stephanejouve/magma-cycling/branch/main/graph/badge.svg)](https://codecov.io/gh/stephanejouve/magma-cycling)

### Required Checks

All CI checks must pass before merging:

- ✅ Unit tests passing (Python 3.11 & 3.12)
- ✅ Code formatting (Black)
- ✅ Linting (Ruff, isort)
- ✅ Coverage reported

**Note:** mypy and pydocstyle are non-blocking while we progressively improve type hints and docstrings.

## 📝 Code Quality Standards

### Testing

- Write tests for new features
- Maintain or improve coverage
- Follow existing test patterns
- Use descriptive test names

### Documentation

- Update README.md if adding features
- Add docstrings (Google style)
- Update CHANGELOG.md
- Document complex logic with comments

### Code Style

- **Line length**: 100 characters
- **Docstrings**: Google style convention
- **Imports**: isort with black profile
- **Type hints**: Encouraged (mypy checking)

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify on latest version
3. Check if already fixed in `main`

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- Python version:
- OS:
- Poetry version:
- Package versions: (from poetry show)

**Additional Context**
Any other relevant information
```

## 🎯 Pull Request Guidelines

### Before Submitting

- ✅ Tests pass locally
- ✅ Code is formatted (Black, isort)
- ✅ No linting errors (Ruff)
- ✅ Documentation updated
- ✅ CHANGELOG.md updated

### PR Description Template

```markdown
## Description
What does this PR do?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

## 🏗️ Project Structure

```
magma_cycling/
├── magma_cycling/     # Main package
│   ├── ai_providers/           # AI provider implementations
│   ├── analyzers/              # Data analyzers
│   ├── api/                    # API clients (Intervals.icu)
│   ├── config/                 # Configuration
│   ├── core/                   # Core utilities
│   ├── intelligence/           # Training intelligence
│   ├── planning/               # Training planning
│   └── workflows/              # Workflow orchestration
├── tests/                      # Test suite
│   ├── config/                 # Config tests
│   ├── intelligence/           # Intelligence tests
│   ├── planning/               # Planning tests
│   ├── api/                    # API tests
│   ├── analyzers/              # Analyzer tests
│   ├── integration/            # Integration tests
│   └── workflows/              # Workflow tests
├── docs/                       # Documentation
├── project-docs/               # Project documentation
└── scripts/                    # Utility scripts
```

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/stephanejouve/magma-cycling/issues)
- **Discussions**: [GitHub Discussions](https://github.com/stephanejouve/magma-cycling/discussions)
- **Documentation**: Check `/docs` and `/project-docs`

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Recognition

All contributors will be recognized in:
- Git commit history
- CHANGELOG.md
- Project documentation

---

**Thank you for contributing to Cyclisme Training Logs!** 🚴‍♂️
