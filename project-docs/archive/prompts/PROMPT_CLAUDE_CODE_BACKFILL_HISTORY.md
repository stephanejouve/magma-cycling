# TASK: Implement Complete Training History Backfill System

## Context

The cyclisme-training-logs project now has full automation capabilities (v2.0.3):
- ✅ 5 AI providers operational (Mistral, Claude, OpenAI, Ollama, Clipboard)
- ✅ `--auto` mode for zero-interaction workflow
- ✅ `manage-state` tool for state management
- ✅ 273/273 tests passing

**Current situation:**
- ~35 activities analyzed (November-December 2025)
- ~200-250 historical activities in Intervals.icu (2024-2025) NOT analyzed
- Need to backfill complete training history using automated workflow

**Goal:**
Create a robust `backfill-history` tool that analyzes ALL historical activities automatically.

## Required Implementation

### File 1: backfill_history.py (Main Script)

**Location:** `cyclisme-training-logs/backfill_history.py` (project root)

**Purpose:** Automated batch analysis of historical training data

**Core Features:**

1. **Fetch Activities from Intervals.icu**
   - Use `IntervalsClient` to get all activities in date range
   - Sort chronologically (oldest first)
   - Filter based on criteria

2. **Filter Unanalyzed**
   - Check against `config.analyzed_activities`
   - Skip already analyzed activities
   - Optional: skip activities with planned workouts

3. **Batch Processing**
   - Analyze activities using `workflow-coach --auto`
   - Process in configurable batches (default: 10)
   - Commit each batch to git
   - Rate limiting between batches

4. **Error Handling**
   - Timeout per activity (5 min max)
   - Retry logic optional
   - Continue on individual failures
   - Detailed error logging

5. **Progress Tracking**
   - Live progress display (X/N, percentage)
   - Estimated time remaining
   - Success/failure counts
   - Final statistics report

**Implementation Structure:**

```python
#!/usr/bin/env python3
"""
Backfill complete training history from Intervals.icu.

Usage:
    poetry run backfill-history [options]
    
Options:
    --start-date YYYY-MM-DD    Start date (default: 2024-01-01)
    --end-date YYYY-MM-DD      End date (default: today)
    --provider PROVIDER        AI provider (default: mistral_api)
    --batch-size N             Activities per git commit (default: 10)
    --dry-run                  Show what would be analyzed
    --skip-planned             Skip activities with planned workouts
    --limit N                  Max activities to analyze (testing)
    --help                     Show help message
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
import subprocess
import time
from typing import List, Dict, Set

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cyclisme_training_logs.config import get_config
from cyclisme_training_logs.intervals_client import IntervalsClient


class HistoryBackfiller:
    """Backfill training history with AI analysis."""
    
    def __init__(
        self,
        provider: str = "mistral_api",
        batch_size: int = 10,
        dry_run: bool = False
    ):
        self.provider = provider
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.config = get_config()
        self.client = IntervalsClient(self.config)
        
        # Statistics tracking
        self.total_activities = 0
        self.already_analyzed = 0
        self.to_analyze = 0
        self.analyzed_success = 0
        self.analyzed_failed = 0
        self.start_time = None
    
    def get_analyzed_activities(self) -> Set[str]:
        """Get set of already analyzed activity IDs."""
        return self.config.analyzed_activities
    
    def fetch_activities(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Fetch all activities from Intervals.icu in date range.
        
        Returns list sorted chronologically (oldest first).
        """
        print(f"\n📥 Récupération activités {start_date} → {end_date}...")
        
        activities = self.client.get_activities(
            oldest=start_date,
            newest=end_date
        )
        
        # Sort by date (oldest first for chronological backfill)
        activities.sort(key=lambda a: a['start_date_local'])
        
        print(f"✅ {len(activities)} activités trouvées")
        return activities
    
    def filter_unanalyzed(
        self,
        activities: List[Dict],
        skip_planned: bool = False
    ) -> List[Dict]:
        """
        Filter activities that need analysis.
        
        Args:
            activities: All activities from API
            skip_planned: If True, skip activities with planned workouts
            
        Returns:
            List of activities needing analysis
        """
        analyzed = self.get_analyzed_activities()
        
        to_analyze = []
        for activity in activities:
            activity_id = activity['id']
            
            # Skip if already analyzed
            if activity_id in analyzed:
                self.already_analyzed += 1
                continue
            
            # Skip if has planned workout (optional)
            if skip_planned and activity.get('workout_id'):
                print(f"⏭️  Skip {activity_id}: has planned workout")
                continue
            
            to_analyze.append(activity)
        
        return to_analyze
    
    def analyze_activity(self, activity: Dict) -> bool:
        """
        Analyze single activity using workflow-coach --auto.
        
        Returns:
            True if analysis succeeded, False otherwise
        """
        activity_id = activity['id']
        activity_name = activity.get('name', 'Unknown')
        activity_date = activity.get('start_date_local', '')[:10]
        
        print(f"\n{'='*70}")
        print(f"📊 Analyse: {activity_name}")
        print(f"   ID: {activity_id}")
        print(f"   Date: {activity_date}")
        print(f"{'='*70}")
        
        if self.dry_run:
            print("🔍 DRY RUN - Skipping actual analysis")
            return True
        
        try:
            # Build command
            cmd = [
                'poetry', 'run', 'workflow-coach',
                '--activity-id', activity_id,
                '--provider', self.provider,
                '--auto',              # Fully automated
                '--skip-feedback',     # No manual feedback
                '--skip-git'           # Batch commits later
            ]
            
            # Run workflow with timeout
            print(f"🚀 Lancement analyse automatique...")
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout per activity
            )
            
            if result.returncode == 0:
                print(f"✅ Analyse réussie: {activity_id}")
                self.analyzed_success += 1
                return True
            else:
                print(f"❌ Échec analyse: {activity_id}")
                print(f"   Return code: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}")
                self.analyzed_failed += 1
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT: {activity_id} (>5min)")
            self.analyzed_failed += 1
            return False
            
        except Exception as e:
            print(f"❌ EXCEPTION: {activity_id}: {e}")
            self.analyzed_failed += 1
            return False
    
    def commit_batch(self, batch_num: int, activities: List[Dict]):
        """
        Commit analyzed activities to git.
        
        Args:
            batch_num: Batch number for commit message
            activities: Activities in this batch
        """
        if self.dry_run:
            print(f"\n🔍 DRY RUN - Would commit batch {batch_num}")
            return
        
        print(f"\n💾 Commit batch {batch_num}...")
        
        try:
            # Get date range for commit message
            dates = [a.get('start_date_local', '')[:10] for a in activities]
            date_min = min(dates) if dates else 'unknown'
            date_max = max(dates) if dates else 'unknown'
            date_range = f"{date_min} → {date_max}"
            
            # Git add
            cmd = ['git', 'add', 'logs/workouts-history.md']
            subprocess.run(cmd, cwd=str(project_root), check=True)
            
            # Git commit
            commit_msg = (
                f"Backfill: Batch {batch_num} "
                f"({len(activities)} séances, {date_range})"
            )
            cmd = ['git', 'commit', '-m', commit_msg]
            subprocess.run(cmd, cwd=str(project_root), check=True)
            
            print(f"✅ Batch {batch_num} committé: {commit_msg}")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Échec commit batch {batch_num}: {e}")
            print("   Continuant quand même...")
    
    def estimate_resources(self, count: int) -> Dict[str, float]:
        """
        Estimate time and cost for analyzing N activities.
        
        Returns:
            Dict with 'time_minutes' and 'cost_usd' estimates
        """
        # Time estimates per provider (minutes per activity)
        time_per_activity = {
            'mistral_api': 1.0,
            'claude_api': 0.7,
            'openai': 0.8,
            'ollama': 4.0,
            'clipboard': 4.0  # Manual
        }
        
        # Cost estimates per provider (USD per activity)
        cost_per_activity = {
            'mistral_api': 0.02,
            'claude_api': 0.08,
            'openai': 0.05,
            'ollama': 0.0,
            'clipboard': 0.0
        }
        
        time_minutes = count * time_per_activity.get(self.provider, 1.0)
        cost_usd = count * cost_per_activity.get(self.provider, 0.0)
        
        return {
            'time_minutes': time_minutes,
            'time_hours': time_minutes / 60,
            'cost_usd': cost_usd
        }
    
    def run(
        self,
        start_date: str,
        end_date: str,
        skip_planned: bool = False,
        limit: int = None
    ):
        """
        Run complete backfill process.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            skip_planned: Skip activities with planned workouts
            limit: Max activities to analyze (for testing)
        """
        self.start_time = time.time()
        
        # Print header
        print("\n" + "="*70)
        print("  🚀 BACKFILL HISTORIQUE COMPLET")
        print("="*70)
        print(f"\n📅 Période: {start_date} → {end_date}")
        print(f"🤖 Provider: {self.provider}")
        print(f"📦 Batch size: {self.batch_size}")
        print(f"🔍 Dry run: {self.dry_run}")
        if limit:
            print(f"⚠️  Limit: {limit} activités max")
        print()
        
        # Fetch all activities
        activities = self.fetch_activities(start_date, end_date)
        self.total_activities = len(activities)
        
        # Filter unanalyzed
        to_analyze = self.filter_unanalyzed(activities, skip_planned)
        self.to_analyze = len(to_analyze)
        
        # Print summary
        print(f"\n📊 RÉSUMÉ:")
        print(f"   Total activités: {self.total_activities}")
        print(f"   Déjà analysées: {self.already_analyzed}")
        print(f"   À analyser: {self.to_analyze}")
        
        # Apply limit if specified
        if limit and self.to_analyze > limit:
            print(f"\n⚠️  Limite activée: {limit} activités max")
            to_analyze = to_analyze[:limit]
            self.to_analyze = limit
        
        # Nothing to do?
        if self.to_analyze == 0:
            print("\n✅ Rien à faire!")
            print("   Toutes les activités sont déjà analysées.")
            return
        
        # Estimate resources
        estimates = self.estimate_resources(self.to_analyze)
        
        print(f"\n⏱️  ESTIMATIONS:")
        print(f"   Temps: ~{estimates['time_hours']:.1f}h "
              f"({estimates['time_minutes']:.0f} min)")
        print(f"   Coût: ${estimates['cost_usd']:.2f} "
              f"({self.provider})")
        
        # Confirm if not dry run
        if not self.dry_run:
            print(f"\n⚠️  CONFIRMATION REQUISE")
            print(f"   Cela va analyser {self.to_analyze} activités")
            print(f"   avec le provider '{self.provider}'")
            print()
            
            response = input("   Continuer? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("\n❌ Annulé par l'utilisateur")
                return
        
        # Process activities in batches
        batch = []
        batch_num = 1
        
        for i, activity in enumerate(to_analyze, 1):
            # Progress header
            progress_pct = int(i * 100 / self.to_analyze)
            print(f"\n{'='*70}")
            print(f"📈 Progression: {i}/{self.to_analyze} ({progress_pct}%)")
            
            # Estimate remaining time
            if self.start_time and i > 1:
                elapsed = time.time() - self.start_time
                avg_time_per_activity = elapsed / (i - 1)
                remaining_activities = self.to_analyze - i + 1
                eta_seconds = avg_time_per_activity * remaining_activities
                eta_minutes = eta_seconds / 60
                print(f"⏱️  ETA: ~{eta_minutes:.1f} min")
            
            print(f"{'='*70}")
            
            # Analyze activity
            success = self.analyze_activity(activity)
            
            # Add to batch if successful
            if success:
                batch.append(activity)
            
            # Commit batch if full
            if len(batch) >= self.batch_size:
                self.commit_batch(batch_num, batch)
                batch = []
                batch_num += 1
                
                # Rate limiting (avoid API throttling)
                if not self.dry_run and i < self.to_analyze:
                    print("\n⏸️  Pause 5s (rate limiting)...")
                    time.sleep(5)
        
        # Commit remaining activities
        if batch:
            self.commit_batch(batch_num, batch)
        
        # Final report
        self.print_final_report()
    
    def print_final_report(self):
        """Print final statistics and summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        print("\n" + "="*70)
        print("  ✅ BACKFILL TERMINÉ!")
        print("="*70)
        
        print(f"\n📊 STATISTIQUES FINALES:")
        print(f"   Total activités: {self.total_activities}")
        print(f"   Déjà analysées: {self.already_analyzed}")
        print(f"   À analyser: {self.to_analyze}")
        print(f"   ✅ Succès: {self.analyzed_success}")
        print(f"   ❌ Échecs: {self.analyzed_failed}")
        
        if self.analyzed_success > 0:
            success_rate = (self.analyzed_success / self.to_analyze) * 100
            print(f"   📈 Taux réussite: {success_rate:.1f}%")
        
        print(f"\n⏱️  TEMPS:")
        print(f"   Total: {elapsed/60:.1f} min ({elapsed/3600:.2f}h)")
        if self.analyzed_success > 0:
            avg_time = elapsed / self.analyzed_success
            print(f"   Moyenne: {avg_time:.1f}s par activité")
        
        if self.analyzed_success > 0:
            num_commits = (self.analyzed_success // self.batch_size) + 1
            print(f"\n💾 GIT:")
            print(f"   Commits créés: {num_commits}")
            print(f"   Activités par commit: ~{self.batch_size}")
        
        print("\n" + "="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill complete training history from Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be analyzed
  poetry run backfill-history --dry-run --limit 10
  
  # Test with 10 activities
  poetry run backfill-history --limit 10 --provider mistral_api
  
  # Backfill complete 2024
  poetry run backfill-history --start-date 2024-01-01 --end-date 2024-12-31
  
  # Backfill all with Claude API
  poetry run backfill-history --start-date 2024-01-01 --provider claude_api
  
  # Backfill with Ollama (free but slow)
  poetry run backfill-history --start-date 2024-01-01 --provider ollama
        """
    )
    
    parser.add_argument(
        '--start-date',
        default='2024-01-01',
        help='Start date in YYYY-MM-DD format (default: 2024-01-01)'
    )
    
    parser.add_argument(
        '--end-date',
        default=datetime.now().strftime('%Y-%m-%d'),
        help='End date in YYYY-MM-DD format (default: today)'
    )
    
    parser.add_argument(
        '--provider',
        default='mistral_api',
        choices=['mistral_api', 'claude_api', 'openai', 'ollama', 'clipboard'],
        help='AI provider to use (default: mistral_api)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of activities per git commit (default: 10)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be analyzed without actually doing it'
    )
    
    parser.add_argument(
        '--skip-planned',
        action='store_true',
        help='Skip activities that have planned workouts'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of activities to analyze (for testing)'
    )
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Use YYYY-MM-DD format")
        sys.exit(1)
    
    # Create and run backfiller
    backfiller = HistoryBackfiller(
        provider=args.provider,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    try:
        backfiller.run(
            start_date=args.start_date,
            end_date=args.end_date,
            skip_planned=args.skip_planned,
            limit=args.limit
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur (Ctrl+C)")
        print(f"\n📊 Progression avant interruption:")
        print(f"   Analysées: {backfiller.analyzed_success}")
        print(f"   Échecs: {backfiller.analyzed_failed}")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```

**Key implementation details:**
- Full argparse with help and examples
- Progress tracking with ETA
- Resource estimation (time + cost)
- User confirmation before processing
- Batch git commits
- Error handling with continue-on-failure
- Keyboard interrupt handling
- Final statistics report
- Dry-run mode for testing

---

### File 2: pyproject.toml (Add Entry Point)

**Modification required:**

Add to `[tool.poetry.scripts]` section:

```toml
[tool.poetry.scripts]
workflow-coach = "cyclisme_training_logs.workflow_coach:main"
manage-state = "cyclisme_training_logs.tools.manage_state:main"
backfill-history = "backfill_history:main"  # NEW
```

This allows running: `poetry run backfill-history`

---

### File 3: docs/BACKFILL_GUIDE.md (Documentation)

**Location:** `docs/BACKFILL_GUIDE.md`

**Content:**

```markdown
# Backfill History Guide

## Overview

The `backfill-history` tool analyzes all historical training activities from Intervals.icu using the automated AI workflow.

## Quick Start

```bash
# 1. Test with dry run (see what would be analyzed)
poetry run backfill-history --dry-run --limit 10

# 2. Test with 10 real activities
poetry run backfill-history --limit 10 --provider mistral_api

# 3. Backfill complete history
poetry run backfill-history --start-date 2024-01-01 --provider mistral_api
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--start-date` | 2024-01-01 | Start date (YYYY-MM-DD) |
| `--end-date` | today | End date (YYYY-MM-DD) |
| `--provider` | mistral_api | AI provider |
| `--batch-size` | 10 | Activities per git commit |
| `--dry-run` | false | Test mode (no actual analysis) |
| `--skip-planned` | false | Skip activities with planned workouts |
| `--limit` | none | Max activities (for testing) |

## Providers Comparison

| Provider | Time/Activity | Cost/Activity | Quality | Recommendation |
|----------|---------------|---------------|---------|----------------|
| mistral_api | ~1 min | $0.02 | Good | ✅ Best for backfill |
| claude_api | ~40s | $0.08 | Excellent | High cost |
| ollama | ~4 min | $0 | Good | Free but slow |
| openai | ~50s | $0.05 | Excellent | Good balance |

## Examples

### Test Mode

```bash
# Dry run - see what would happen
poetry run backfill-history --dry-run --limit 5

# Test with 10 activities
poetry run backfill-history --limit 10 --provider mistral_api
```

### Production Backfill

```bash
# Full 2024 backfill with Mistral
poetry run backfill-history \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --provider mistral_api \
  --batch-size 10

# Full history with Claude (better quality, higher cost)
poetry run backfill-history \
  --start-date 2024-01-01 \
  --provider claude_api \
  --batch-size 5

# Free backfill with Ollama (slow)
poetry run backfill-history \
  --start-date 2024-01-01 \
  --provider ollama \
  --batch-size 20
```

### Specific Periods

```bash
# Q1 2024
poetry run backfill-history \
  --start-date 2024-01-01 \
  --end-date 2024-03-31

# November 2024
poetry run backfill-history \
  --start-date 2024-11-01 \
  --end-date 2024-11-30
```

## Process

1. **Fetch activities** from Intervals.icu API
2. **Filter** already analyzed (via manage-state)
3. **Estimate** time and cost
4. **Confirm** with user
5. **Analyze** each activity with `workflow-coach --auto`
6. **Commit** in batches to git
7. **Report** final statistics

## Output

```
📊 RÉSUMÉ:
   Total activités: 234
   Déjà analysées: 35
   À analyser: 199

⏱️  ESTIMATIONS:
   Temps: ~3.3h (199 min)
   Coût: $3.98 (mistral_api)

⚠️  CONFIRMATION REQUISE
   Cela va analyser 199 activités
   avec le provider 'mistral_api'

   Continuer? (yes/no): yes

[... progress ...]

✅ BACKFILL TERMINÉ!

📊 STATISTIQUES FINALES:
   Total activités: 234
   Déjà analysées: 35
   À analyser: 199
   ✅ Succès: 195
   ❌ Échecs: 4
   📈 Taux réussite: 98.0%

⏱️  TEMPS:
   Total: 187.3 min (3.12h)
   Moyenne: 57.2s par activité

💾 GIT:
   Commits créés: 20
   Activités par commit: ~10
```

## Troubleshooting

### Analysis Failures

If some activities fail:
1. Check provider API keys in `.env`
2. Verify network connectivity
3. Check Intervals.icu API limits
4. Review error messages in output

### Resume After Interruption

The tool can be safely interrupted (Ctrl+C). Already analyzed activities are marked and won't be re-analyzed on next run.

```bash
# Same command - will skip already analyzed
poetry run backfill-history --start-date 2024-01-01
```

### Re-analyze Failed Activities

```bash
# Get failed activity IDs from output
# Remove from analyzed set
poetry run manage-state --remove i12345678

# Re-run backfill (will pick up failed activities)
poetry run backfill-history --start-date 2024-01-01 --limit 20
```

## Best Practices

1. **Start with dry-run** to estimate scope
2. **Test with limit** (10-20 activities) before full backfill
3. **Use Mistral API** for best cost/quality ratio
4. **Batch size 10** is good default
5. **Monitor progress** - can take several hours
6. **Use screen/tmux** if running remotely

## Integration

After backfill:

```bash
# Verify complete history
poetry run manage-state --show --list 100

# Check git log
git log --oneline -20

# Review latest analyses
tail -500 logs/workouts-history.md
```
```

---

## Validation Tests

After implementation, validate with:

### Test 1: Script Exists and Runs

```bash
poetry run backfill-history --help

# Expected: Help message displayed with all options
```

### Test 2: Dry Run Works

```bash
poetry run backfill-history --dry-run --limit 5

# Expected:
# - Fetches activities
# - Shows what would be analyzed
# - No actual analysis
# - No git commits
```

### Test 3: Real Backfill (Small Test)

```bash
poetry run backfill-history --limit 3 --provider mistral_api

# Expected:
# - 3 activities analyzed
# - Analyses inserted in workouts-history.md
# - Git commit created
# - Statistics reported
```

### Test 4: State Management Integration

```bash
# Before backfill
poetry run manage-state --show

# Run backfill
poetry run backfill-history --limit 5

# After backfill
poetry run manage-state --show

# Expected: 5 more activities in analyzed set
```

### Test 5: Git Integration

```bash
git log --oneline -5

# Expected: Batch commits visible with format:
# "Backfill: Batch N (X séances, DATE → DATE)"
```

## Success Criteria

✅ **Script Created**
- `backfill_history.py` in project root
- Executable with `poetry run backfill-history`
- Full argparse with help

✅ **Core Features**
- Fetches activities from Intervals.icu
- Filters already analyzed
- Batch processing with configurable size
- Git commits per batch
- Progress tracking with ETA
- Resource estimation (time + cost)

✅ **Error Handling**
- Timeout per activity (5 min)
- Continue on individual failures
- Keyboard interrupt handling
- Detailed error messages

✅ **Documentation**
- Help message (--help)
- BACKFILL_GUIDE.md complete
- Examples in both places

✅ **Integration**
- Works with manage-state
- Uses workflow-coach --auto
- Respects analyzed_activities state
- Proper git commits

✅ **Tests**
- Dry-run works
- Small backfill works (--limit 3)
- Statistics accurate
- Git history clean

## Constraints

- **DO NOT** modify existing workflow-coach or manage-state
- **DO NOT** break existing functionality
- **MAINTAIN** state consistency with manage-state
- **USE** existing IntervalsClient (don't rewrite)
- **PRESERVE** analyzed_activities tracking
- **KEEP** git history clean (meaningful commit messages)

## Expected Usage Pattern

```bash
# Phase 1: Discovery (1 min)
poetry run backfill-history --dry-run

# Phase 2: Test (5 min)
poetry run backfill-history --limit 10 --provider mistral_api

# Phase 3: Production (2-4 hours)
poetry run backfill-history --start-date 2024-01-01 --provider mistral_api

# Result: Complete training history analyzed and committed
```

## Final Notes

- Designed for one-time bulk backfill
- Can be run multiple times safely (skips analyzed)
- Interruptible and resumable
- Compatible with all AI providers
- Production-ready error handling
- Clean git history

Ready to implement?
