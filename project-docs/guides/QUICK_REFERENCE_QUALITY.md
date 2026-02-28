# Quick Reference: Code Quality Tools

## 🔍 Type Checking (MyPy)

### Check All Files
```bash
poetry run mypy magma_cycling/ --show-error-codes 2>&1 | grep "^Found"
```

### Check Specific File
```bash
poetry run mypy magma_cycling/workflow_coach.py --show-error-codes
```

### Current Status
- **Total Errors:** 38 (down from 56)
- **Files with Errors:** 5 (down from 14)
- **Clean Files:** 9/14 (64%)

---

## 📝 Documentation (Pydocstyle)

### Check All
```bash
poetry run pydocstyle magma_cycling/ --count
```

### By Error Type
```bash
poetry run pydocstyle magma_cycling/ | grep -E "^        D[0-9]+" | cut -d: -f1 | sort | uniq -c | sort -rn
```

### Auto-fix Scripts
```bash
# Fix missing periods (D400)
python3 scripts/fix_d400_docstrings.py

# Fix trailing period bugs
python3 scripts/fix_trailing_period_bug.py

# Fix missing blank lines (D205)
python3 scripts/fix_d205_docstrings.py
```

---

## 🧪 Testing

### Full Suite
```bash
poetry run pytest tests/ -v
```

### Quick Check
```bash
poetry run pytest tests/ -x --tb=short -q
```

### With Coverage
```bash
poetry run pytest tests/ --cov=magma_cycling --cov-report=html
```

### Specific Test
```bash
poetry run pytest tests/test_workflow_weekly.py -v
```

---

## 📊 Code Complexity

### Check Complexity (Radon)
```bash
# Cyclomatic complexity
poetry run radon cc magma_cycling/ -a -s

# Complex functions only (C and above)
poetry run radon cc magma_cycling/ -nc

# Maintainability index
poetry run radon mi magma_cycling/ -s
```

### Current Critical Functions
All previously critical functions have been refactored:
- ✅ step_1b_detect_all_gaps: F-48 → manageable
- ✅ step_2_collect_feedback: C-17 → B-8
- ✅ CasingNormalizer.run: C-15 → B-7

---

## 🔧 Code Formatting

### Format All
```bash
poetry run black magma_cycling/
```

### Check Only
```bash
poetry run black magma_cycling/ --check
```

---

## 🎯 Linting (Ruff)

### Check All
```bash
poetry run ruff check magma_cycling/
```

### Auto-fix
```bash
poetry run ruff check magma_cycling/ --fix
```

---

## 📦 Dependencies

### Show Outdated
```bash
poetry show --outdated
```

### Update Safe (Minor/Patch)
```bash
poetry update coverage pytz sphinx docutils
```

### Update All (Risky)
```bash
poetry update
```

---

## 🔄 Pre-commit Hooks

### Install
```bash
poetry run pre-commit install
```

### Run Manually
```bash
poetry run pre-commit run --all-files
```

### Update Hooks
```bash
poetry run pre-commit autoupdate
```

---

## 📈 Quality Metrics Dashboard

### Quick Health Check
```bash
# Run all quality checks
echo "=== MyPy ===" && poetry run mypy magma_cycling/ 2>&1 | grep "^Found"
echo "\n=== Pydocstyle ===" && poetry run pydocstyle magma_cycling/ --count | tail -1
echo "\n=== Tests ===" && poetry run pytest tests/ -q --tb=no
echo "\n=== Ruff ===" && poetry run ruff check magma_cycling/ --quiet && echo "✅ No issues" || echo "⚠️ Issues found"
```

---

## 🎯 Common Patterns

### MyPy: Cast for dict[str, Any]
```python
from typing import cast

result: dict[str, Any] = {"issues": []}
issues = cast(list[str], result["issues"])
issues.append("error")
```

### MyPy: Optional Types
```python
self.api: IntervalsClient | None

if self.api is None:
    return False

response = self.api.create_event(data)  # Type-safe
```

### MyPy: Type Guards
```python
activity_id = activity.get("id")

if activity_id is None:
    continue

# Now activity_id is known to be not None
process(str(activity_id))
```

### Docstrings: Google Style
```python
def function(arg1: str, arg2: int) -> bool:
    """Short description ending with period.

    Longer description if needed. Explains what the function does
    and why it exists.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If arg2 is negative

    Examples:
        >>> function("test", 5)
        True
    """
    pass
```

---

## 🚨 CI/CD Integration

### Pre-commit Hook
Already configured in `.pre-commit-config.yaml`:
- black (formatting)
- ruff (linting)
- isort (imports)
- yaml/toml/json checks
- trailing whitespace
- large files detection

### Recommended CI Additions
```yaml
# Add to CI pipeline
- name: Type Check
  run: poetry run mypy magma_cycling/ --show-error-codes

- name: Doc Check
  run: poetry run pydocstyle magma_cycling/ --count
  continue-on-error: true  # Until all fixed

- name: Complexity Check
  run: poetry run radon cc magma_cycling/ -nc
  continue-on-error: true
```

---

## 📚 Resources

### Documentation
- MyPy: https://mypy.readthedocs.io/
- Pydocstyle: http://www.pydocstyle.org/
- Google Style: https://google.github.io/styleguide/pyguide.html
- Radon: https://radon.readthedocs.io/

### Session Summary
See `SESSION_SUMMARY_2026-01-03.md` for detailed improvement session report.

---

**Last Updated:** 2026-01-03
**Status:** 497/497 tests passing ✅
