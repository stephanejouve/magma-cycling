# 🐛 Fix: Wellness and Metrics API Returns List Instead of Dict

## Context
Weekly analysis (wa) fails to parse wellness/metrics data:
```
WARNING: No metrics for 2025-12-22: 'list' object has no attribute 'get'
WARNING: No wellness for 2025-12-22: 'list' object has no attribute 'get'
```

The Intervals.icu API returns a **list of dicts** (one per day), not a single dict.

## Task 1: Locate Bug

Find where wellness/metrics are fetched and parsed:
```bash
cd ~/cyclisme-training-logs

# Find wellness parsing
grep -n "No wellness for" cyclisme_training_logs/**/*.py

# Find metrics parsing
grep -n "No metrics for" cyclisme_training_logs/**/*.py

# Show context (20 lines before/after)
grep -B 20 -A 10 "'list' object has no attribute 'get'" cyclisme_training_logs/**/*.py
```

## Task 2: Expected API Response Format

The API likely returns:
```json
[
  {
    "id": "2025-12-22",
    "ctl": 55.2,
    "atl": 63.4,
    "weight": 83.8,
    ...
  },
  {
    "id": "2025-12-23",
    ...
  }
]
```

NOT:
```json
{
  "2025-12-22": { "ctl": 55.2, ... }
}
```

## Task 3: Fix Pattern

**BEFORE (buggy):**
```python
# Assumes response is a dict
wellness_data = api.get_wellness(start_date, end_date)
daily_wellness = wellness_data.get(date_str)  # ❌ Fails: list has no .get()
```

**AFTER (fixed):**
```python
# Handle list response
wellness_data = api.get_wellness(start_date, end_date)

# Convert list to dict keyed by date
wellness_dict = {item['id']: item for item in wellness_data} if isinstance(wellness_data, list) else wellness_data

# Now safe
daily_wellness = wellness_dict.get(date_str)
```

## Task 4: Apply Fix

1. **Find all locations** where `.get(date)` is called on wellness/metrics data
2. **Add list-to-dict conversion** before `.get()` calls
3. **Test** with `wa --week S073 --start-date 2025-12-22`

## Expected Output After Fix
```
INFO: Fetching daily metrics evolution
INFO: Loaded metrics for 2025-12-22: CTL=55.2, ATL=63.4
INFO: Loaded metrics for 2025-12-23: CTL=55.5, ATL=62.1
...
INFO: Loaded wellness for 2025-12-22: weight=83.8kg
```

## Priority
P1 - Blocks weekly analysis reports
---

### **PROMPT 2: Fix Weekly Planner Credentials Loading**

```markdown
# 🐛 Fix: Weekly Planner Not Loading API Credentials

## Context
wp –week-id S074 –start-date 2025-12-29
⚠️ API non disponible : IntervalsAPI.init() missing 2 required positional arguments
The `weekly-planner` script doesn't load `.env` credentials.

## Task 1: Find Credentials Loading

```bash
cd ~/cyclisme-training-logs

# Find weekly_planner.py entry point
find . -name "weekly_planner.py" -type f

# Check how it loads credentials
grep -n "IntervalsAPI" cyclisme_training_logs/weekly_planner.py

# Compare with working script (weekly_analysis.py)
grep -B 5 -A 5 "IntervalsAPI" cyclisme_training_logs/weekly_analysis.py
Task 2: Expected Pattern (from working scripts)
Working example (weekly_analysis):
from cyclisme_training_logs.prepare_analysis import IntervalsAPI
from cyclisme_training_logs.utils import load_credentials

# Load credentials
athlete_id, api_key = load_credentials()

# Initialize API
api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)
Task 3: Apply Fix
In weekly_planner.py, ensure credentials are loaded before IntervalsAPI init:
# Add at top of main() or run():
from cyclisme_training_logs.utils import load_credentials

try:
    athlete_id, api_key = load_credentials()
    api = IntervalsAPI(athlete_id=athlete_id, api_key=api_key)
except Exception as e:
    logger.warning(f"⚠️ API non disponible : {e}")
    logger.warning("   Les métriques seront approximatives")
    api = None
Task 4: Test
cd ~/cyclisme-training-logs
poetry run weekly-planner --week-id S074 --start-date 2025-12-29

# Should show:
# ✅ API Intervals.icu connectée
# 📊 Collecte des métriques actuelles...
Priority
P2 - Affects planning workflow UX
---

### **PROMPT 3: Fix Git Commit Error**

```markdown
# 🐛 Fix: Git Commit Fails After Skipped Session Documentation

## Context
⚠️ Erreur git : Command ‘[‘git’, ‘commit’, …]’ returned non-zero exit status 1.
After inserting skipped session into workouts-history.md.

## Task 1: Diagnose Git State

```bash
cd ~/cyclisme-training-logs

# Check git status
git status

# Check if file was actually modified
git diff training-logs/workouts-history.md

# Check git config
git config user.name
git config user.email
Task 2: Common Causes
Cause A: Nothing to commit (file already staged)
	∙	Fix: Check git diff --cached before commit
Cause B: File not staged
	∙	Fix: git add before commit
Cause C: Git user config missing
	∙	Fix: Set user.name/user.email
Task 3: Find Git Commit Code
cd ~/cyclisme-training-logs

# Find where git commit is called
grep -n "git.*commit" cyclisme_training_logs/workflow_coach.py

# Show context
grep -B 10 -A 10 "git.*commit" cyclisme_training_logs/workflow_coach.py
Task 4: Add Defensive Checks
BEFORE (buggy):
subprocess.run(['git', 'commit', '-m', message], check=True)
AFTER (fixed):
# Check if there's something to commit
status = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)

if not status.stdout.strip():
    logger.info("✅ Rien à commiter (déjà à jour)")
    return True

# Stage changes
subprocess.run(['git', 'add', 'training-logs/workouts-history.md'], check=True)

# Commit
result = subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)

if result.returncode != 0:
    logger.error(f"⚠️ Erreur commit: {result.stderr}")
    return False

logger.info("✅ Commit réussi")
return True
Priority
P3 - Workflow continues despite error
---

### **PROMPT 4: Fix Missing get_events Method**

```markdown
# 🐛 Fix: IntervalsAPI Missing get_events() Method

## Context
WARNING: Failed to fetch planned workouts: ‘IntervalsAPI’ object has no attribute ‘get_events’
## Task 1: Locate Bug

```bash
cd ~/cyclisme-training-logs

# Find where get_events is called
grep -n "get_events" cyclisme_training_logs/**/*.py

# Check IntervalsAPI class definition
grep -n "class IntervalsAPI" cyclisme_training_logs/prepare_analysis.py
sed -n '/class IntervalsAPI/,/^class /p' cyclisme_training_logs/prepare_analysis.py
Task 2: Check Method Existence
List all methods in IntervalsAPI:
grep -n "    def " cyclisme_training_logs/prepare_analysis.py | grep -A 2 IntervalsAPI
Task 3: Add Missing Method (if needed)
If get_events() doesn’t exist, add it:
class IntervalsAPI:
    # ... existing methods ...

    def get_events(self, oldest: str, newest: str, category: str = None):
        """Fetch events (workouts, notes, etc.) for date range

        Args:
            oldest: Start date YYYY-MM-DD
            newest: End date YYYY-MM-DD
            category: Optional filter (WORKOUT, NOTE, etc.)

        Returns:
            list: Events matching criteria
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
        params = {
            'oldest': oldest,
            'newest': newest
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        events = response.json()

        # Filter by category if specified
        if category:
            events = [e for e in events if e.get('category') == category]

        return events
class IntervalsAPI:
    # ... existing methods ...

    def get_events(self, oldest: str, newest: str, category: str = None):
        """Fetch events (workouts, notes, etc.) for date range

        Args:
            oldest: Start date YYYY-MM-DD
            newest: End date YYYY-MM-DD
            category: Optional filter (WORKOUT, NOTE, etc.)

        Returns:
            list: Events matching criteria
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
        params = {
            'oldest': oldest,
            'newest': newest
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        events = response.json()

        # Filter by category if specified
        if category:
            events = [e for e in events if e.get('category') == category]

        return events
Task 4: Test
cd ~/cyclisme-training-logs

# Re-run weekly analysis
poetry run weekly-analysis --week S073 --start-date 2025-12-22

# Should see:
# INFO: Fetching planned workouts
# INFO: Found 7 planned workouts for S073
Priority
P2 - Affects weekly reports completeness
---

## 🎯 **RÉSUMÉ PRIORITÉS**

| Bug | Impact | Priorité |
|-----|--------|----------|
| **Wellness/Metrics list parsing** | ❌ Bloque rapports | **P1** |
| **Weekly Planner credentials** | ⚠️ UX dégradée | **P2** |
| **get_events missing** | ⚠️ Données incomplètes | **P2** |
| **Git commit error** | ℹ️ Workflow continue | **P3** |

---

## 📝 **ACTION IMMÉDIATE**

**Envoie les 4 prompts à Claude Code dans l'ordre P1 → P2 → P3.**

Chaque prompt est autonome et testable indépendamment! 🚀​​​​​​​​​​​​​​​​
