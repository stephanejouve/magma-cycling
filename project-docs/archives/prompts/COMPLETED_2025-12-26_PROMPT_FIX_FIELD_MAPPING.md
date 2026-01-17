# MISSION: Fix TSS/IF Field Mapping in WeeklyAnalyzer

## CONTEXT

**Problem:** Weekly reports show TSS=0, IF=0.00 despite enriched data being available.

**Root Cause:** Field name mismatch between data structure and report generation.

**Evidence from Debug:**
```python
# Available fields (ICU prefix):
icu_training_load: 45.67    # ✅ TSS data exists
icu_intensity: 66.36364     # ✅ IF data exists

# Fields being read (wrong names):
training_load: None         # ❌ Wrong field
if: None                    # ❌ Wrong field
```

**Activities ARE enriched** (log shows "Successfully enriched 4 activities")
**But WeeklyAnalyzer reads wrong field names.**

---

## TASK 1: Fix WeeklyAnalyzer Field Mapping

**File:** `cyclisme_training_logs/analyzers/weekly_analyzer.py`

**Find the section that generates workout history** (likely around line 100-150):
```python
# CURRENT (BROKEN)
def _generate_workout_history(self, data: Dict) -> str:
    for activity in activities:
        tss = activity.get('training_load', 0)      # ❌ Wrong field
        if_value = activity.get('icu_intensity', 0.0)  # ❌ Wrong field name usage
```

**Replace with (FIXED):**
```python
def _generate_workout_history(self, data: Dict) -> str:
    for activity in activities:
        # Use ICU-prefixed fields (actual field names from API)
        tss = activity.get('icu_training_load', 0)      # ✅ Correct field
        if_value = activity.get('icu_intensity', 0.0)   # ✅ Already correct

        # Normalize IF (icu_intensity is in %, divide by 100)
        if_value = if_value / 100 if if_value > 10 else if_value
```

---

## TASK 2: Fix All TSS/IF References in WeeklyAnalyzer

**Search pattern:** Look for ALL occurrences of:
- `activity.get('training_load'`
- `activity.get('tss'`
- `activity.get('if'`

**Replace with:**
- `activity.get('icu_training_load'`
- `activity.get('icu_training_load'`  (tss is same as icu_training_load)
- `activity.get('icu_intensity') / 100`  (normalize percentage)

**Typical locations:**
1. `_generate_workout_history()` - Main report generation
2. `_generate_metrics_evolution()` - Weekly stats
3. `_generate_bilan_final()` - Summary stats
4. Any helper methods calculating averages

---

## TASK 3: Add Field Mapping Documentation

**File:** `cyclisme_training_logs/analyzers/weekly_analyzer.py`

**Add to class docstring:**
```python
"""
Weekly report generation from aggregated data.

Field Mapping (Intervals.icu API):
    - TSS: activity['icu_training_load']
    - IF: activity['icu_intensity'] / 100  (API returns percentage)
    - NP: activity['icu_weighted_avg_watts']
    - Average Power: activity['icu_average_watts']

Note: All power/intensity metrics use 'icu_' prefix from Intervals.icu API.
"""
```

---

## TASK 4: Fix Metrics Evolution Report

**Likely in `_generate_metrics_evolution()` method:**
```python
# CURRENT (BROKEN)
total_tss = sum(a.get('training_load', 0) for a in activities)
avg_if = sum(a.get('icu_intensity', 0) for a in activities) / len(activities)

# FIXED
total_tss = sum(a.get('icu_training_load', 0) for a in activities)
avg_if = sum(a.get('icu_intensity', 0) for a in activities) / len(activities) / 100
```

---

## TASK 5: Fix Bilan Final Report

**Likely in `_generate_bilan_final()` method:**
```python
# CURRENT (BROKEN)
total_tss = sum(a.get('training_load', 0) for a in activities)

# FIXED
total_tss = sum(a.get('icu_training_load', 0) for a in activities)
avg_tss = total_tss / len(activities) if activities else 0
avg_if = sum(a.get('icu_intensity', 0) for a in activities) / len(activities) / 100 if activities else 0
```

---

## VALIDATION

**After changes:**
```bash
# 1. Regenerate reports
poetry run weekly-analysis --week current

# 2. Verify TSS/IF values (should NOT be zero)
cat ~/training-logs/weekly-reports/S052/workout_history_s052.md

# Expected output:
# S052-01: Durée: 76min | TSS: 45 | IF: 0.66
# S052-02: Durée: 85min | TSS: 62 | IF: 0.71
```
```bash
# 3. Verify bilan final
cat ~/training-logs/weekly-reports/S052/bilan_final_s052.md

# Expected output:
# TSS total: 204
# TSS moyen: 51.0
# IF moyen: 0.68
```
```bash
# 4. Run tests
poetry run pytest tests/test_weekly_analyzer.py -v
```

---

## GIT WORKFLOW
```bash
git add cyclisme_training_logs/analyzers/weekly_analyzer.py
git commit -m "fix(weekly): use correct ICU field names for TSS/IF in reports

- Map training_load → icu_training_load (TSS)
- Normalize icu_intensity from percentage (divide by 100)
- Fix all TSS/IF references across report generators
- Add field mapping documentation to class docstring

Fixes: TSS=0, IF=0.00 display despite enriched data available
Related: 3d79a50 (enrichment working, but wrong field names)"

git push origin main
```

---

## NOTES

**Key Insights:**
- ✅ Enrichment works (3d79a50)
- ❌ Field mapping wrong in analyzer
- 🔑 Intervals.icu uses `icu_` prefix for calculated fields
- 🔑 `icu_intensity` is percentage (needs /100 for IF)

**Files Modified:**
1. `cyclisme_training_logs/analyzers/weekly_analyzer.py` (field mapping)

**Estimated Time:** 15-20 minutes

**Complexity:** LOW (search & replace + normalization)
```

---
