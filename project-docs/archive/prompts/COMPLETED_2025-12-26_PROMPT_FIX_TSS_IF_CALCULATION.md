# MISSION: Fix WeeklyAggregator to Reuse DailyAggregator Logic

## CONTEXT

**Problem:** WeeklyAggregator fetches raw activities but doesn't calculate TSS/IF metrics.
**Root Cause:** Doesn't reuse existing DailyAggregator logic.
**Impact:** All reports show TSS=0, IF=0.00

**Evidence:**
```
S052-01: Durée: 76min | TSS: 0 | IF: 0.00
S052-02: Durée: 85min | TSS: 0 | IF: 0.00
S052-03: Durée: 63min | TSS: 0 | IF: 0.00
S052-04: Durée: 55min | TSS: 0 | IF: 0.00
```

**DailyAggregator already has working TSS/IF calculation logic.**

---

## TASK 1: Refactor WeeklyAggregator to Use DailyAggregator

**File:** `cyclisme_training_logs/analyzers/weekly_aggregator.py`

**Current structure (BROKEN):**
```python
def collect_raw_data(self) -> Dict:
    activities = self._fetch_activities()  # Raw data
    metrics = self._fetch_metrics()
    return {'activities': activities, ...}  # No TSS/IF calculation
```

**New structure (FIXED):**
```python
from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator
from datetime import timedelta

def collect_enriched_data(self) -> Dict:
    """Collect and enrich week data using DailyAggregator."""
    
    # 1. Get week date range
    week_dates = [
        self.start_date + timedelta(days=i)
        for i in range(7)
    ]
    
    # 2. Use DailyAggregator for each day (REUSE LOGIC)
    daily_results = []
    for date in week_dates:
        daily_agg = DailyAggregator(
            date=date,
            athlete_id=self.athlete_id,
            api_key=self.api_key
        )
        
        # Get enriched data with TSS/IF calculated
        daily_data = daily_agg.aggregate()
        if daily_data and daily_data.get('activities'):
            daily_results.extend(daily_data['activities'])
    
    # 3. Combine results
    return {
        'activities': daily_results,  # NOW with TSS/IF
        'week_metrics': self._aggregate_week_metrics(daily_results),
        'feedback': self._load_feedback()
    }

def _aggregate_week_metrics(self, activities: List[Dict]) -> Dict:
    """Aggregate metrics across the week."""
    total_tss = sum(a.get('tss', 0) for a in activities)
    avg_if = sum(a.get('if_value', 0) for a in activities) / len(activities) if activities else 0
    
    return {
        'total_tss': total_tss,
        'average_if': avg_if,
        'num_sessions': len(activities),
        # Add other weekly aggregations
    }
```

---

## TASK 2: Update WeeklyWorkflow to Use New Method

**File:** `cyclisme_training_logs/workflows/workflow_weekly.py`

**Find:**
```python
raw_data = aggregator.collect_raw_data()
```

**Replace with:**
```python
enriched_data = aggregator.collect_enriched_data()
```

---

## TASK 3: Verify DailyAggregator Interface

**File:** `cyclisme_training_logs/analyzers/daily_aggregator.py`

**Ensure it has:**
```python
class DailyAggregator:
    def __init__(self, date: date, athlete_id: str, api_key: str):
        """Initialize daily aggregator."""
        self.date = date
        self.athlete_id = athlete_id
        self.api_key = api_key
    
    def aggregate(self) -> Dict:
        """Return enriched data with TSS/IF calculated."""
        # Existing working logic
        pass
```

**If constructor signature different, adapt WeeklyAggregator accordingly.**

---

## TASK 4: Update WeeklyAggregator Docstring

**File:** `cyclisme_training_logs/analyzers/weekly_aggregator.py`

**Update module docstring:**
```python
"""
Weekly data aggregation using DailyAggregator.

Reuses DailyAggregator logic for each day of the week to ensure
consistent TSS/IF calculation across daily and weekly analyses.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2
```

---

## VALIDATION

**After changes:**
```bash
# 1. Test weekly analysis
poetry run weekly-analysis --week current

# Expected output (NO MORE TSS=0):
# S052-01: Durée: 76min | TSS: 45 | IF: 0.68
# S052-02: Durée: 85min | TSS: 62 | IF: 0.75
```
```bash
# 2. Verify report content
cat ~/training-logs/weekly-reports/S052/workout_history_s052.md

# Should show real TSS/IF values
```
```bash
# 3. Run tests
poetry run pytest tests/test_weekly_aggregator.py -v
```

---

## GIT WORKFLOW
```bash
git add cyclisme_training_logs/analyzers/weekly_aggregator.py
git add cyclisme_training_logs/workflows/workflow_weekly.py
git commit -m "fix(weekly): reuse DailyAggregator logic for TSS/IF calculation

- Refactor WeeklyAggregator.collect_raw_data() → collect_enriched_data()
- Use DailyAggregator for each day to calculate TSS/IF metrics
- Eliminate code duplication between daily/weekly analysis
- Add week-level metric aggregation

Fixes: TSS=0, IF=0.00 in weekly reports
GARTNER_TIME: I/P1"

git push origin main
```

---

## NOTES

**Benefits:**
- ✅ No code duplication
- ✅ Consistent TSS/IF across daily/weekly
- ✅ Single source of truth (DailyAggregator)
- ✅ Easier maintenance

**Files Modified:**
1. `weekly_aggregator.py` (refactor data collection)
2. `workflow_weekly.py` (use new method name)

**Estimated Time:** 25-30 minutes

**Complexity:** MEDIUM (requires understanding DailyAggregator interface)
