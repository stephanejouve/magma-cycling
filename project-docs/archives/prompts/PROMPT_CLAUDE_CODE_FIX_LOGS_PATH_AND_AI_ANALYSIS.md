# TASK: Fix Logs Path Configuration + Missing AI Analysis Collection

## Context

The cyclisme-training-logs project has two critical issues:

1. **Logs Path Hardcoded**: Logs written to `cyclisme-training-logs/logs/` instead of external `training-logs/` repo
2. **AI Analysis Not Collected**: Backfill tests show analyses not appearing in workouts-history.md

**Current State:**
- ✅ Backfill tool works (activities analyzed)
- ✅ Stats reported (success rate 100%)
- ❌ AI coach reflections/analyses NOT inserted into logs
- ❌ Logs written to wrong repository

**Example Missing Analysis:**

After running:
```bash
poetry run backfill-history --limit 2 --yes --provider mistral_api
```

Expected in `workouts-history.md`:
```markdown
### S073-04-FOR-ForceEndurance-V001
Date: 25/12/2025

#### Analyse Coach IA
[Detailed AI analysis with insights, patterns, recommendations]
```

Actual result:
```markdown
### S073-04-FOR-ForceEndurance-V001
Date: 25/12/2025

[Empty or missing AI analysis section]
```

---

## Problem Analysis

### Issue 1: Path Configuration

**Files Affected:**
- `cyclisme_training_logs/config.py` - Hardcoded paths
- `insert_analysis.py` - Uses config paths
- `workflow_coach.py` - Uses config paths
- `backfill_history.py` - Uses config paths

**Current Code (config.py):**
```python
class Config:
    def __init__(self):
        # Hardcoded to local repo
        self.logs_dir = Path(__file__).parent.parent / "logs"
        self.workouts_history_path = self.logs_dir / "workouts-history.md"
```

**Required Change:**
- Read `TRAINING_LOGS_PATH` from `.env`
- Use external repo if set
- Fallback to local if not set

---

### Issue 2: Missing AI Analysis

**Root Cause Investigation Needed:**

Possible causes:
1. **Prompt generation working** but **insertion failing**
2. **AI response** generated but **not parsed correctly**
3. **Auto mode (--yes)** bypassing analysis insertion
4. **insert_analysis.py** not called in backfill workflow
5. **Response format** from AI not matching expected pattern

**Files to Investigate:**
- `backfill_history.py` - Check workflow call chain
- `workflow_coach.py` - Verify analysis insertion step
- `insert_analysis.py` - Check parsing and insertion logic
- `generate_analysis_prompt.py` - Verify prompt generation

**Debug Steps Required:**
1. Add verbose logging to track workflow steps
2. Verify AI response is actually generated
3. Check if insert_analysis.py is called
4. Validate response parsing logic
5. Test insertion with real AI response

---

## Required Implementation

### Part 1: Configurable Logs Path

#### File: cyclisme_training_logs/config.py

**Changes:**

```python
import os
from pathlib import Path
from typing import Optional

class Config:
    """Configuration for cyclisme training logs."""

    def __init__(self):
        # Initialize .env loading
        self._load_env()

        # Configure logs directory
        self._setup_logs_path()

        # Initialize other paths
        self._setup_file_paths()

        # Existing config (Intervals.icu, AI providers, etc.)
        # ... keep existing code ...

    def _load_env(self):
        """Load environment variables from .env file."""
        from dotenv import load_dotenv

        # Try to load .env from project root
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Fallback to system .env
            load_dotenv()

    def _setup_logs_path(self):
        """
        Setup logs directory path.

        Priority:
        1. TRAINING_LOGS_PATH from .env (external repo)
        2. Fallback to local logs/ directory
        """
        training_logs_base = os.getenv('TRAINING_LOGS_PATH')

        if training_logs_base:
            # Use external training-logs repository
            base_path = Path(training_logs_base)

            # Validate path exists
            if not base_path.exists():
                print(f"⚠️  Warning: TRAINING_LOGS_PATH not found: {base_path}")
                print(f"   Falling back to local logs/")
                self.logs_dir = Path(__file__).parent.parent / "logs"
            else:
                self.logs_dir = base_path / "logs"
                print(f"✅ Using external logs: {self.logs_dir}")
        else:
            # Fallback: local logs directory
            self.logs_dir = Path(__file__).parent.parent / "logs"
            print(f"ℹ️  Using local logs: {self.logs_dir}")

        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _setup_file_paths(self):
        """Setup all log file paths."""
        self.workouts_history_path = self.logs_dir / "workouts-history.md"
        self.metrics_evolution_path = self.logs_dir / "metrics-evolution.md"
        self.training_learnings_path = self.logs_dir / "training-learnings.md"
        self.workout_templates_path = self.logs_dir / "workout-templates.md"

        # State file (keep in cyclisme-training-logs)
        # This is NOT training data, it's tool state
        state_dir = Path(__file__).parent.parent / ".state"
        state_dir.mkdir(exist_ok=True)
        self.state_file = state_dir / "analyzed_activities.json"
```

**Key Points:**
- Uses `TRAINING_LOGS_PATH` from `.env` if available
- Falls back to local `logs/` if not set
- Validates external path exists before using
- Creates directories if needed
- Provides clear console feedback

---

#### File: .env (Add Variable)

```bash
# Intervals.icu Configuration
VITE_INTERVALS_ATHLETE_ID=iXXXXXX
VITE_INTERVALS_API_KEY=your_api_key_here

# AI Providers
ANTHROPIC_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Training Logs Repository Path
# Point to external training-logs repo for proper data separation
# Leave empty or comment out to use local logs/ directory
TRAINING_LOGS_PATH=/Users/your_username/training-logs

# Alternative: Relative path (from cyclisme-training-logs)
# TRAINING_LOGS_PATH=../training-logs
```

---

#### File: .env.example (Documentation)

```bash
# Intervals.icu Configuration
VITE_INTERVALS_ATHLETE_ID=your_athlete_id
VITE_INTERVALS_API_KEY=your_api_key

# AI Providers (at least one required)
ANTHROPIC_API_KEY=your_anthropic_key
MISTRAL_API_KEY=your_mistral_key
OPENAI_API_KEY=your_openai_key

# Training Logs Repository Path (Optional)
#
# Use this to store training logs in a separate git repository
# for better data/code separation.
#
# Example: /Users/john/training-logs
# Example: ../training-logs (relative path)
#
# Leave empty to use local logs/ directory (default behavior)
TRAINING_LOGS_PATH=

# Note: The path should point to the ROOT of training-logs repo
# Logs will be written to: {TRAINING_LOGS_PATH}/logs/
```

---

#### File: README.md (Update Configuration Section)

Add to configuration documentation:

```markdown
## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required: Intervals.icu
VITE_INTERVALS_ATHLETE_ID=your_athlete_id
VITE_INTERVALS_API_KEY=your_api_key

# Required: At least one AI provider
MISTRAL_API_KEY=your_mistral_key        # Recommended for cost
ANTHROPIC_API_KEY=your_anthropic_key    # Best quality
OPENAI_API_KEY=your_openai_key          # Good balance

# Optional: External logs repository
TRAINING_LOGS_PATH=/path/to/training-logs
```

### Logs Location

By default, training logs are stored in `logs/` within this repository.

For better separation of code and data, you can use an external repository:

1. Create/clone your training-logs repository
2. Set `TRAINING_LOGS_PATH` in `.env`
3. All logs will be written there automatically

**Example:**
```bash
# .env
TRAINING_LOGS_PATH=/Users/john/training-logs

# Results in:
# - Logs written to: /Users/john/training-logs/logs/
# - Code in: /Users/john/cyclisme-training-logs/
```
```

---

### Part 2: Fix Missing AI Analysis Collection

#### Investigation Steps

**Step 1: Add Debug Logging to workflow_coach.py**

```python
def main():
    """Main workflow."""
    args = parse_args()

    print("\n" + "="*70)
    print("🔍 DEBUG: Workflow Steps")
    print("="*70)

    # ... existing code ...

    # After prompt generation
    print(f"\n✅ Prompt generated")
    print(f"   Provider: {args.provider}")
    print(f"   Auto mode: {args.auto}")

    # After AI analysis
    print(f"\n✅ AI analysis received")
    print(f"   Length: {len(analysis_text)} characters")
    print(f"   Preview: {analysis_text[:200]}...")

    # Before insertion
    print(f"\n🔄 Calling insert_analysis.py")
    print(f"   Activity: {activity_id}")
    print(f"   History path: {config.workouts_history_path}")
    print(f"   Auto mode: {args.auto}")

    # After insertion
    print(f"\n✅ Analysis inserted")
    print(f"   File: {config.workouts_history_path}")
```

**Step 2: Verify insert_analysis.py is Called in Backfill**

Check `backfill_history.py`:

```python
def analyze_activity(self, activity: Dict) -> bool:
    """Analyze single activity using workflow-coach --auto."""

    # Current command
    cmd = [
        'poetry', 'run', 'workflow-coach',
        '--activity-id', activity_id,
        '--provider', self.provider,
        '--auto',              # Fully automated
        '--skip-feedback',     # No manual feedback
        '--skip-git'           # Batch commits later
    ]

    # Add debug logging
    print(f"\n🔍 DEBUG: Command to execute:")
    print(f"   {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Add output inspection
    if result.returncode == 0:
        print(f"\n📋 Subprocess stdout:")
        print(result.stdout)

        # Check if analysis was actually inserted
        if "Analyse insérée" in result.stdout or "Analysis inserted" in result.stdout:
            print(f"✅ Analysis confirmed inserted")
        else:
            print(f"⚠️  WARNING: No insertion confirmation found")
```

**Step 3: Check insert_analysis.py Auto Mode Logic**

Verify `--yes` flag is properly handled:

```python
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    # ... existing args ...
    parser.add_argument('--yes', action='store_true', help='Auto-confirm insertion')

    args = parser.parse_args()

    # Debug
    print(f"\n🔍 insert_analysis.py called")
    print(f"   Activity ID: {args.activity_id}")
    print(f"   Analysis file: {args.analysis_file}")
    print(f"   Auto mode (--yes): {args.yes}")

    # ... existing code ...

    # Ensure analysis is inserted in auto mode
    if args.yes:
        print(f"✅ Auto mode: Inserting without confirmation")
        # Insert directly
        insert_analysis_to_history(...)
    else:
        # Ask for confirmation
        response = input("Insert analysis? (y/n): ")
        # ...
```

**Step 4: Verify AI Response Format**

Check that AI providers return proper format:

```python
# In ai_providers/mistral_api.py (and others)

def generate_analysis(self, prompt: str) -> str:
    """Generate analysis from prompt."""

    response = self.client.chat(
        model=self.model,
        messages=[{"role": "user", "content": prompt}]
    )

    analysis = response.choices[0].message.content

    # Debug
    print(f"\n🔍 AI Response received")
    print(f"   Provider: Mistral API")
    print(f"   Length: {len(analysis)} chars")
    print(f"   First 200 chars: {analysis[:200]}")

    # Validate response has content
    if not analysis or len(analysis) < 100:
        raise ValueError(f"AI response too short: {len(analysis)} chars")

    return analysis
```

---

#### Potential Fixes

**Fix 1: Ensure insert_analysis.py is Always Called**

In `workflow_coach.py`, verify the complete workflow:

```python
def run_workflow(args):
    """Run complete analysis workflow."""

    # Step 1: Generate prompt
    print("\n📝 Step 1: Generating analysis prompt...")
    prompt_file = generate_prompt(args.activity_id)

    # Step 2: Get AI analysis
    print("\n🤖 Step 2: Getting AI analysis...")
    analysis = get_ai_analysis(prompt_file, args.provider)

    # Step 3: Save analysis
    print("\n💾 Step 3: Saving analysis...")
    analysis_file = save_analysis(analysis, args.activity_id)

    # Step 4: Insert into history (CRITICAL)
    print("\n📋 Step 4: Inserting into workouts-history.md...")

    # Build insert command
    insert_cmd = [
        'python', '-m', 'cyclisme_training_logs.insert_analysis',
        '--activity-id', args.activity_id,
        '--analysis-file', str(analysis_file)
    ]

    # Add --yes if auto mode
    if args.auto:
        insert_cmd.append('--yes')

    # Execute insertion
    result = subprocess.run(insert_cmd, check=True)

    if result.returncode != 0:
        raise RuntimeError("Analysis insertion failed")

    print("✅ Analysis inserted successfully")
```

**Fix 2: Direct Insertion (No Subprocess)**

Alternative: Call insertion function directly instead of subprocess:

```python
# In workflow_coach.py

from cyclisme_training_logs.insert_analysis import insert_analysis_to_history

def run_workflow(args):
    # ... prompt generation ...
    # ... AI analysis ...

    # Direct insertion (no subprocess)
    print("\n📋 Inserting analysis into history...")

    insert_analysis_to_history(
        activity_id=args.activity_id,
        analysis_text=analysis,
        config=config,
        auto_confirm=args.auto  # or args.yes
    )

    print("✅ Analysis inserted")
```

**Fix 3: Verify workouts-history.md is Updated**

After insertion, verify the file was actually modified:

```python
# In insert_analysis.py

def insert_analysis_to_history(activity_id, analysis_text, config, auto_confirm=False):
    """Insert analysis into workouts-history.md."""

    history_path = config.workouts_history_path

    # Get file modification time before
    mtime_before = history_path.stat().st_mtime if history_path.exists() else 0

    # ... do insertion ...

    # Verify file was modified
    mtime_after = history_path.stat().st_mtime

    if mtime_after > mtime_before:
        print(f"✅ File updated: {history_path}")
        print(f"   Before: {mtime_before}")
        print(f"   After: {mtime_after}")
    else:
        print(f"⚠️  WARNING: File NOT modified!")
        raise RuntimeError("workouts-history.md was not updated")
```

---

## Implementation Plan

### Phase 1: Path Configuration (Priority 1)

1. **Update config.py**
   - Add `_load_env()` method
   - Add `_setup_logs_path()` method
   - Add `_setup_file_paths()` method
   - Add validation and feedback

2. **Update .env**
   - Add `TRAINING_LOGS_PATH` variable
   - Document with examples

3. **Update .env.example**
   - Add documentation for new variable
   - Provide usage examples

4. **Update README.md**
   - Document logs location configuration
   - Provide setup examples

5. **Test Path Configuration**
   ```bash
   # Test 1: With external path
   echo "TRAINING_LOGS_PATH=/path/to/training-logs" >> .env
   poetry run workflow-coach --help
   # Should show: "✅ Using external logs: /path/to/training-logs/logs"

   # Test 2: Without external path
   # Comment out TRAINING_LOGS_PATH
   poetry run workflow-coach --help
   # Should show: "ℹ️  Using local logs: .../cyclisme-training-logs/logs"
   ```

---

### Phase 2: Fix Missing AI Analysis (Priority 2)

1. **Add Debug Logging**
   - Update `workflow_coach.py` with verbose logging
   - Update `insert_analysis.py` with step tracking
   - Update `backfill_history.py` to show subprocess output

2. **Investigate Root Cause**
   - Run test with debug logging:
     ```bash
     poetry run backfill-history --limit 1 --yes --provider mistral_api
     ```
   - Examine output for missing steps
   - Identify where analysis insertion fails

3. **Implement Fix**
   - Based on root cause, apply appropriate fix
   - Add validation checks
   - Add error handling

4. **Verify Fix**
   - Run backfill test: `poetry run backfill-history --limit 2 --yes`
   - Check `workouts-history.md` has AI analyses
   - Verify file modification timestamps
   - Confirm insertion success messages

---

## Validation Tests

### Test 1: Path Configuration

```bash
# Setup
cd ~/cyclisme-training-logs

# Test external path
echo "TRAINING_LOGS_PATH=$HOME/training-logs" > .env.test
cp .env.test .env

# Run workflow
poetry run workflow-coach --help

# Expected output:
# ✅ Using external logs: /Users/you/training-logs/logs

# Verify logs location
poetry run python -c "from cyclisme_training_logs.config import get_config; print(get_config().logs_dir)"

# Expected: /Users/you/training-logs/logs
```

### Test 2: Analysis Insertion

```bash
# Run single analysis with debug
poetry run backfill-history --limit 1 --yes --provider mistral_api > test_output.txt 2>&1

# Check output for analysis confirmation
grep -i "analysis inserted" test_output.txt
grep -i "✅" test_output.txt

# Check workouts-history.md was updated
tail -100 ~/training-logs/logs/workouts-history.md

# Should show:
# ### SXXX-XX-...
# Date: ...
#
# #### Analyse Coach IA
# [Detailed analysis content]
```

### Test 3: End-to-End Backfill

```bash
# Full test with 3 activities
poetry run backfill-history \
  --start-date 2024-08-01 \
  --end-date 2024-08-31 \
  --limit 3 \
  --yes \
  --provider mistral_api

# Verify all 3 have AI analyses
grep -c "#### Analyse Coach IA" ~/training-logs/logs/workouts-history.md

# Expected: Count should increase by 3
```

---

## Success Criteria

✅ **Path Configuration**
- [ ] TRAINING_LOGS_PATH read from .env
- [ ] External path used when set
- [ ] Fallback to local when not set
- [ ] Path validation works
- [ ] Console feedback clear
- [ ] .env.example documented
- [ ] README updated

✅ **AI Analysis Collection**
- [ ] Debug logging shows all workflow steps
- [ ] AI response received and logged
- [ ] insert_analysis.py called correctly
- [ ] workouts-history.md updated
- [ ] File modification verified
- [ ] Analysis content present in logs
- [ ] Success rate >95% on backfill test

✅ **Integration**
- [ ] Existing tests pass
- [ ] Backward compatible (no .env = local logs)
- [ ] Works with all AI providers
- [ ] Backfill workflow complete
- [ ] Git commits clean

---

## Critical Notes

1. **Don't Break Existing Functionality**
   - All existing tests must pass
   - Backward compatible (local logs/ as fallback)
   - No changes to AI provider interfaces

2. **Root Cause First**
   - Add debug logging BEFORE implementing fixes
   - Identify exact point of failure
   - Fix the actual problem, not symptoms

3. **Validation Critical**
   - Verify AI analyses actually appear in logs
   - Check file modification timestamps
   - Confirm insertion success messages

4. **Path Handling**
   - Support both absolute and relative paths
   - Validate paths exist
   - Create directories if needed
   - Clear error messages

---

## Expected Output After Fix

```bash
# Run backfill
poetry run backfill-history --limit 2 --yes --provider mistral_api

# Output:
✅ Using external logs: /Users/you/training-logs/logs

📊 Analyse: Force Endurance
   ID: i113782165
   Date: 2024-08-15

🚀 Lancement analyse automatique...
✅ Prompt généré
🤖 Analyse IA reçue (1234 chars)
📋 Insertion dans workouts-history.md...
✅ Analyse insérée avec succès
   Fichier: /Users/you/training-logs/logs/workouts-history.md

# Check result
tail -50 ~/training-logs/logs/workouts-history.md

# Expected:
### S073-04-FOR-ForceEndurance-V001
Date: 2024-08-15

#### Métriques Pré-séance
CTL: 55
ATL: 40
TSB: +15

#### Exécution
IF: 0.65
TSS: 40
...

#### Analyse Coach IA

Cette séance de force-endurance montre une excellente exécution technique...
[Full AI analysis with insights, patterns, recommendations]
...
```

---

Ready to implement both fixes!
