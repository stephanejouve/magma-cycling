# TASK: Fix Hardcoded "Claude.ai" References + Git Skip Logic

## Context

Migration AI Providers v2.0.0 is complete with 5 operational providers (Mistral, Claude, OpenAI, Ollama, Clipboard). However, 2 UX bugs remain that break the provider-agnostic experience:

**Bug 1: Hardcoded "Claude.ai" in generate_analysis_prompt.py**
- User selects `--provider mistral_api`
- Workflow correctly uses Mistral API
- BUT output still says "PROMPT PRÊT POUR CLAUDE.AI"
- Shows manual instructions: "1. Ouvrir Claude.ai dans votre navigateur"
- Confusing and contradicts provider selection

**Bug 2: Git skip flag not working properly**
- User passes `--skip-git` flag
- Step 7 shows "Le commit git a été skippé"
- BUT git commands may still execute after message
- Missing early return statement

## Evidence from Logs

### Bug 1 Evidence (sortie_20251225_165234.log)

```
🤖 Provider IA : mistral_api                    ← Correct

============================================================
✅ PROMPT PRÊT POUR CLAUDE.AI                   ← HARDCODED!
============================================================

📝 ÉTAPES SUIVANTES :

1. Ouvrir Claude.ai dans votre navigateur       ← HARDCODED!
   → https://claude.ai

2. Coller le prompt (Cmd+V)

3. Attendre l'analyse de Claude                 ← HARDCODED!

4. Copier la réponse de Claude                  ← HARDCODED!
```

**Expected with Mistral API:**
```
🤖 Provider IA : mistral_api

============================================================
✅ PROMPT GÉNÉRÉ ET ENVOYÉ À L'IA
============================================================

⏳ Analyse en cours via API...
   Le résultat sera automatiquement disponible.
```

### Bug 2 Evidence

```bash
# Command executed:
train --skip-git --provider mistral_api --activity-id i101413894

# Output shows:
======================================================================
  ⏭️  Git Commit (Skip)
  Étape 7/7 : Sauvegarde (optionnel)
======================================================================

Le commit git a été skippé (--skip-git).

# But execution may continue instead of returning immediately
```

## Required Changes

### File 1: magma_cycling/generate_analysis_prompt.py

**Location:** Main function that prints instructions after prompt generation

**Current code (approximate):**
```python
def main():
    """Generate analysis prompt and copy to clipboard."""
    # ... prompt generation code ...

    # Copy to clipboard
    pyperclip.copy(prompt)

    # PROBLEMATIC: Hardcoded instructions
    print("""
============================================================
✅ PROMPT PRÊT POUR CLAUDE.AI
============================================================

📝 ÉTAPES SUIVANTES :

1. Ouvrir Claude.ai dans votre navigateur
   → https://claude.ai

2. Coller le prompt (Cmd+V)

3. Attendre l'analyse de Claude

4. Copier la réponse de Claude (UNIQUEMENT le bloc markdown)

5. Exécuter le script d'insertion :
   python3 magma_cycling/insert_analysis.py

============================================================
""")
```

**Required fix:**

1. Import AI config to detect provider type
2. Make instructions conditional based on provider
3. For API providers (mistral_api, claude_api, openai, ollama): Show automated message
4. For clipboard provider: Show generic manual instructions

**Target code:**
```python
def main():
    """Generate analysis prompt and copy to clipboard."""
    # ... existing prompt generation code ...

    # Import AI config
    from .config import get_ai_config

    # Get active provider
    config = get_ai_config()
    provider = config.default_provider

    # Copy to clipboard
    pyperclip.copy(prompt)

    # Conditional instructions based on provider
    if provider in ['claude_api', 'mistral_api', 'openai', 'ollama']:
        # API providers - automated workflow
        print("""
============================================================
✅ PROMPT GÉNÉRÉ ET ENVOYÉ À L'IA
============================================================

⏳ Analyse en cours via API...
   Le résultat sera automatiquement copié dans le presse-papier.

============================================================
""")
    else:
        # Clipboard - manual workflow (generic)
        print("""
============================================================
✅ PROMPT PRÊT POUR ANALYSE
============================================================

📝 ÉTAPES SUIVANTES :

1. Ouvrir votre IA préférée dans votre navigateur
   Exemples : Claude.ai, ChatGPT, etc.
   → https://claude.ai (si vous utilisez Claude)

2. Coller le prompt (Cmd+V)

3. Attendre l'analyse de votre IA

4. Copier la réponse (UNIQUEMENT le bloc markdown)

5. Exécuter le script d'insertion :
   python3 magma_cycling/insert_analysis.py

============================================================
""")
```

**Key points:**
- Import `get_ai_config` from `.config`
- Check `config.default_provider`
- List of API providers: `['claude_api', 'mistral_api', 'openai', 'ollama']`
- Clipboard gets generic instructions mentioning multiple AI options

### File 2: magma_cycling/workflow_coach.py

**Location:** `step_7_git_commit()` method in WorkflowCoach class

**Issue:** Method shows skip message but may not return immediately, allowing git commands to execute.

**Current code (approximate):**
```python
def step_7_git_commit(self):
    """Step 7: Git commit (optional)."""
    self._print_step_header("Git Commit", 7, 7, "Sauvegarde (optionnel)")

    if self.skip_git:
        print("\nLe commit git a été skippé (--skip-git).")
        print("\nPour commiter manuellement plus tard :")
        print("  git add logs/workouts-history.md")
        print("  git commit -m \"Analyse: Séance du [DATE]\"")
        # MISSING: return statement here!

    # Git commit code that may execute even with skip_git=True
    print("\n💾 Commit des modifications...")
    # ... git commands ...
```

**Required fix:**

Add explicit `return` statement immediately after skip message to prevent further execution.

**Target code:**
```python
def step_7_git_commit(self):
    """Step 7: Git commit (optional)."""
    self._print_step_header("Git Commit", 7, 7, "Sauvegarde (optionnel)")

    if self.skip_git:
        print("\nLe commit git a été skippé (--skip-git).")
        print("\nPour commiter manuellement plus tard :")
        print("  git add logs/workouts-history.md")
        print("  git commit -m \"Analyse: Séance du [DATE]\"")

        # CRITICAL FIX: Return immediately to prevent git execution
        return

    # Git commit code - only executed if NOT skipped
    print("\n💾 Commit des modifications...")
    # ... git commands ...
```

**Key point:**
- Single line addition: `return` after skip message block
- Ensures no git commands execute when `--skip-git` flag is active

## Validation Tests

After implementing fixes, verify:

### Test 1: No hardcoded "Claude.ai" with API providers

```bash
# Run workflow with Mistral API
poetry run workflow-coach --provider mistral_api --activity-id i101413894 \
  --skip-feedback --skip-git 2>&1 | grep -i "claude\.ai"

# Expected:
# - 0 matches in hardcoded instructions
# - Only in generic example: "Claude.ai, ChatGPT, etc."
```

### Test 2: Git skip prevents execution

```bash
# Note current git HEAD
git log -1 --format="%H %s"

# Run workflow with --skip-git
poetry run workflow-coach --provider mistral_api --activity-id i101413894 \
  --skip-feedback --skip-git

# Check git HEAD again
git log -1 --format="%H %s"

# Expected: Same commit hash (no new commit created)
```

### Test 3: Clipboard workflow still shows instructions

```bash
# Run with clipboard provider (default or explicit)
poetry run workflow-coach --provider clipboard --activity-id i101413894 \
  --skip-feedback --skip-git 2>&1 | grep -A 5 "ÉTAPES SUIVANTES"

# Expected: Generic instructions mentioning "votre IA (Claude.ai, ChatGPT, etc.)"
```

### Test 4: Existing tests pass

```bash
poetry run pytest tests/ -v

# Expected: 161/161 tests passing
# Coverage: 87% maintained
```

## Success Criteria

✅ Fix 1: `generate_analysis_prompt.py`
- Imports `get_ai_config` correctly
- Detects active provider
- Shows automated message for API providers
- Shows generic manual instructions for clipboard
- No hardcoded "Claude.ai" in primary workflow

✅ Fix 2: `workflow_coach.py`
- `step_7_git_commit()` has `return` after skip message
- No git commands execute when `--skip-git` active
- Manual git instructions still shown for reference

✅ All tests pass (161/161)

✅ No regression in existing functionality

✅ Backward compatible with clipboard workflow

## Implementation Notes

### Import pattern for get_ai_config

```python
# In generate_analysis_prompt.py
from .config import get_ai_config
```

### Provider detection pattern

```python
config = get_ai_config()
provider = config.default_provider

# API providers list
API_PROVIDERS = ['claude_api', 'mistral_api', 'openai', 'ollama']

if provider in API_PROVIDERS:
    # Automated workflow message
else:
    # Manual clipboard instructions
```

### Git skip pattern

```python
if self.skip_git:
    # Show skip message
    print("Le commit git a été skippé (--skip-git).")
    # Manual instructions for reference
    print("Pour commiter manuellement plus tard :")
    print("  git add logs/workouts-history.md")
    # CRITICAL: Stop execution
    return

# Git commands only execute if we reach here (skip_git=False)
```

## Edge Cases to Consider

1. **Provider not configured**: Should fall back to clipboard (existing behavior)
2. **Multiple calls to main()**: Each should detect provider independently
3. **Git skip in batch mode**: Should skip for all activities, not just first
4. **Config changes mid-workflow**: Not expected, but provider should be read once at start

## File Structure Context

```
magma_cycling/
├── config.py                      # Contains get_ai_config()
├── generate_analysis_prompt.py    # FIX 1: Conditional instructions
└── workflow_coach.py              # FIX 2: Add return in step_7
```

## Constraints

- **DO NOT** modify any other files
- **DO NOT** change existing test files (unless adding new tests)
- **DO NOT** alter the clipboard workflow behavior (backward compat critical)
- **MAINTAIN** 87% test coverage
- **PRESERVE** all existing command-line arguments and flags

## Expected Commit Message

After fixes are complete and tested:

```
fix(ux): Remove hardcoded Claude.ai refs + Fix git skip logic

Bug 1: generate_analysis_prompt.py
- Import get_ai_config to detect active provider
- Conditional instructions based on provider type
- API providers: Show automated workflow message
- Clipboard: Generic instructions ("votre IA" instead of "Claude.ai")

Bug 2: workflow_coach.py
- Add return statement after skip_git message in step_7_git_commit()
- Prevents git commands from executing when --skip-git is active
- Manual instructions still shown for reference

Tests: 161/161 passing (87% coverage maintained)
Fixes: UX inconsistencies in provider-agnostic workflow
Impact: Production-ready user experience
Version: v2.0.2
```

## Questions?

If you encounter issues:

1. **Import errors**: Verify `get_ai_config` is exported from `config.py`
2. **Provider detection fails**: Check `config.default_provider` attribute exists
3. **Tests fail**: Run `poetry run pytest tests/test_ai_providers/ -v` first to isolate
4. **Git skip still executing**: Double-check indentation of `return` statement

## Context Files Available

You have access to:
- `magma_cycling/config.py` (AI config with get_ai_config())
- `magma_cycling/workflow_coach.py` (Workflow orchestration)
- `magma_cycling/generate_analysis_prompt.py` (Prompt generation)
- All test files in `tests/` directory

Refer to these files to understand:
- How `get_ai_config()` works
- How `default_provider` is set
- How `skip_git` flag is handled in other methods

---

## Summary

**Goal**: Polish v2.0.0 migration by fixing 2 UX bugs
**Scope**: 2 files, ~20 lines total changes
**Impact**: Critical for provider-agnostic user experience
**Risk**: Low (isolated changes, well-tested)
**Timeline**: Should take ~30 minutes to implement and validate

Ready to implement these fixes?
