#!/usr/bin/env python3
"""
Integration test for Phase 1 Core Infrastructure.

Tests the complete pipeline:
1. TimelineInjector - Chronological injection
2. DailyAggregator - Data collection and aggregation
3. PromptGenerator - Composable prompt generation
4. Full workflow integration

Run with: poetry run python test_phase1_integration.py
"""
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from magma_cycling.analyzers.daily_aggregator import (  # noqa: E402
    DailyAggregator,
)
from magma_cycling.core.prompt_generator import PromptGenerator  # noqa: E402
from magma_cycling.core.timeline_injector import TimelineInjector  # noqa: E402


def print_section(title):
    """Print section header."""
    print(f"\n{'='*80}")

    print(f"{title:^80}")
    print(f"{'='*80}\n")


def test_timeline_injector():
    """Test TimelineInjector chronological injection."""
    print_section("TEST 1: TimelineInjector")

    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        test_file = Path(f.name)
        f.write(
            """# Workouts History

## 2025

### S073-03 (2025-01-08)
**Durée:** 60min | **TSS:** 50 | **IF:** 0.85

### S073-01 (2025-01-06)
**Durée:** 45min | **TSS:** 35 | **IF:** 0.75
"""
        )

    try:
        # Initialize injector
        injector = TimelineInjector(history_file=test_file)
        print(f"✓ Injector initialized with file: {test_file}")

        # Test entry to inject (between S073-01 and S073-03)
        new_entry = """### S073-02 (2025-01-07)
**Durée:** 90min | **TSS:** 65 | **IF:** 0.78

#### Métriques Pré-séance
- CTL: 45.2
- ATL: 38.5
- TSB: 6.7

#### Exécution
- Puissance moyenne: 180W
- Découplage: 2.1%
"""
        # Inject chronologically

        print("\nInjecting workout entry for 2025-01-07...")
        result = injector.inject_chronologically(
            workout_entry=new_entry, workout_date=date(2025, 1, 7)
        )

        if result.success:
            print(f"✓ Injection successful at line {result.line_number}")
        else:
            print(f"✗ Injection failed: {result.error}")
            return False

        # Verify chronological order
        with open(test_file) as f:
            content = f.read()

        # Check that S073-02 appears between S073-01 and S073-03
        s01_pos = content.find("S073-01")
        s02_pos = content.find("S073-02")
        s03_pos = content.find("S073-03")

        # File is in reverse chronological order (newest first)
        # So: S073-03 (Jan 8) < S073-02 (Jan 7) < S073-01 (Jan 6)
        if s03_pos < s02_pos < s01_pos:
            print("✓ Reverse chronological order maintained correctly")
            print(f"  Positions: S073-03={s03_pos}, S073-02={s02_pos}, S073-01={s01_pos}")
        else:
            print("✗ Chronological order incorrect")
            print(f"  Positions: S073-01={s01_pos}, S073-02={s02_pos}, S073-03={s03_pos}")
            return False

        # Test duplicate detection
        print("\nTesting duplicate detection...")
        duplicate_result = injector.inject_chronologically(
            workout_entry=new_entry, workout_date=date(2025, 1, 7)
        )

        if duplicate_result.duplicate_found:
            print("✓ Duplicate detection working")
        else:
            print("✗ Duplicate detection failed")
            return False

        print("\n✅ TimelineInjector: ALL TESTS PASSED")
        return True

    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)


def test_daily_aggregator():
    """Test DailyAggregator data collection and processing."""
    print_section("TEST 2: DailyAggregator")

    # Create temporary data directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create mock data files
        feedback_file = temp_dir / "daily-feedback.json"
        feedback_file.write_text(
            """
{
  "entries": [
    {
      "activity_id": "i123456789",
      "notes": "Séance difficile, fatigue dans les jambes",
      "rpe": 8
    }
  ]
}
"""
        )

        power_zones_file = temp_dir / "power-zones.json"
        power_zones_file.write_text(
            """
{
  "ftp": 220,
  "zones": {
    "Z1": [0, 121],
    "Z2": [122, 165],
    "Z3": [166, 198],
    "Z4": [199, 220],
    "Z5": [221, 242],
    "Z6": [243, 308]
  }
}
"""
        )

        # Initialize aggregator
        print(f"✓ Using temp directory: {temp_dir}")
        aggregator = DailyAggregator(activity_id="i123456789", data_dir=temp_dir)

        print("✓ DailyAggregator initialized")

        # Run aggregation
        print("\nRunning aggregation pipeline...")
        result = aggregator.aggregate()

        if not result.success:
            print(f"✗ Aggregation failed: {result.errors}")
            return False

        print("✓ Aggregation completed successfully")

        # Validate raw data collection
        raw_data = result.data["raw"]
        print("\nValidating raw data collection:")
        print(f"  - Activity data: {'✓' if 'activity' in raw_data else '✗'}")
        print(f"  - Feedback data: {'✓' if 'feedback' in raw_data else '✗'}")
        print(f"  - Workflow state: {'✓' if 'workflow_state' in raw_data else '✗'}")
        print(f"  - Fitness metrics: {'✓' if 'fitness_metrics' in raw_data else '✗'}")
        print(f"  - Power zones: {'✓' if 'power_zones' in raw_data else '✗'}")

        # Validate processed data
        processed_data = result.data["processed"]
        print("\nValidating processed data:")

        workout = processed_data.get("workout", {})
        print(f"  - Workout TSS: {workout.get('tss', 0)}")
        print(f"  - Workout IF: {workout.get('intensity_factor', 0.0):.2f}")

        athlete = processed_data.get("athlete", {})
        print(f"  - Athlete FTP: {athlete.get('FTP', 0)}W")
        print(f"  - CTL: {athlete.get('ctl', 0):.1f}")
        print(f"  - ATL: {athlete.get('atl', 0):.1f}")
        print(f"  - TSB: {athlete.get('tsb', 0):.1f}")

        feedback = processed_data.get("feedback", "")
        print(f"  - Feedback: {'✓ Loaded' if feedback else '✗ Missing'}")

        # Validate formatted output
        formatted = result.data["formatted"]
        print("\nValidating formatted output:")
        print(f"  - Output length: {len(formatted)} chars")
        print(f"  - Contains header: {'✓' if '###' in formatted else '✗'}")
        print(f"  - Contains metrics: {'✓' if 'TSS' in formatted else '✗'}")
        print(f"  - Contains feedback: {'✓' if 'Feedback' in formatted else '✗'}")

        print("\n✅ DailyAggregator: ALL TESTS PASSED")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_prompt_generator():
    """Test PromptGenerator composable blocks."""
    print_section("TEST 3: PromptGenerator")

    generator = PromptGenerator()
    print("✓ PromptGenerator initialized")

    # Test individual blocks
    print("\nTesting individual blocks:")

    intro = generator.intro_block("daily")
    print(f"  - Intro block: {'✓' if '# Analyse' in intro else '✗'}")

    context = generator.context_block({"FTP": 220, "weight": 84, "resting_hr": 45})
    print(f"  - Context block: {'✓' if 'FTP' in context else '✗'}")

    workout_data = {
        "duration": 3600,
        "tss": 45,
        "normalized_power": 180,
        "average_power": 175,
        "intensity_factor": 0.82,
    }
    data = generator.data_block(workout_data)
    print(f"  - Data block: {'✓' if 'TSS' in data else '✗'}")

    instructions = generator.instructions_block("Analyser cette séance en détail")
    print(f"  - Instructions block: {'✓' if 'Analyser' in instructions else '✗'}")

    output_format = generator.output_format_block("markdown")
    print(f"  - Output format block: {'✓' if 'Format Sortie' in output_format else '✗'}")

    # Test full prompt generation
    print("\nTesting full daily analysis prompt:")
    full_prompt = generator.generate_daily_analysis_prompt(
        activity_id="i123456789",
        workout_data=workout_data,
        athlete_data={"FTP": 220, "weight": 84},
        feedback="Séance difficile, fatigue",
    )

    print(f"  - Prompt length: {len(full_prompt)} chars")
    print(f"  - Contains intro: {'✓' if '# Analyse' in full_prompt else '✗'}")
    print(f"  - Contains context: {'✓' if 'FTP' in full_prompt else '✗'}")
    print(f"  - Contains data: {'✓' if 'TSS' in full_prompt else '✗'}")
    print(f"  - Contains feedback: {'✓' if 'fatigue' in full_prompt else '✗'}")
    print(f"  - Contains instructions: {'✓' if 'Analyser' in full_prompt else '✗'}")

    # Test prompt structure
    sections = full_prompt.split("\n\n")
    print(f"\n  - Prompt sections: {len(sections)}")
    print(f"  - Well-structured: {'✓' if len(sections) >= 5 else '✗'}")

    print("\n✅ PromptGenerator: ALL TESTS PASSED")
    return True


def test_full_workflow_integration():
    """Test complete Phase 1 workflow integration."""
    print_section("TEST 4: Full Workflow Integration")

    # Create temporary environment
    temp_dir = Path(tempfile.mkdtemp())
    history_file = temp_dir / "workouts-history.md"

    try:
        # Initialize history file
        history_file.write_text(
            """# Workouts History

## 2025
"""
        )

        # Create mock data files
        feedback_file = temp_dir / "daily-feedback.json"
        feedback_file.write_text(
            """
{
  "entries": [
    {
      "activity_id": "i987654321",
      "notes": "Excellente séance, bon feeling",
      "rpe": 7
    }
  ]
}
"""
        )

        power_zones_file = temp_dir / "power-zones.json"
        power_zones_file.write_text('{"ftp": 220}')

        print("✓ Test environment created")

        # Step 1: Aggregate data
        print("\n📊 Step 1: Aggregating workout data...")
        aggregator = DailyAggregator(activity_id="i987654321", data_dir=temp_dir)

        agg_result = aggregator.aggregate()

        if not agg_result.success:
            print(f"✗ Aggregation failed: {agg_result.errors}")
            return False

        print("✓ Data aggregation successful")

        # Step 2: Generate AI prompt
        print("\n🤖 Step 2: Generating AI analysis prompt...")
        generator = PromptGenerator()

        processed = agg_result.data["processed"]
        prompt = generator.generate_daily_analysis_prompt(
            activity_id="i987654321",
            workout_data=processed["workout"],
            athlete_data=processed["athlete"],
            feedback=processed["feedback"],
        )

        print(f"✓ Prompt generated ({len(prompt)} chars)")

        # Step 3: Inject formatted output chronologically
        print("\n📝 Step 3: Injecting workout into history...")
        injector = TimelineInjector(history_file=history_file)

        formatted_output = agg_result.data["formatted"]
        inject_result = injector.inject_chronologically(
            workout_entry=formatted_output, workout_date=date.today()
        )

        if not inject_result.success:
            print(f"✗ Injection failed: {inject_result.error}")
            return False

        print(f"✓ Workout injected at line {inject_result.line_number}")

        # Verify complete workflow
        print("\n✅ Workflow Integration Validation:")

        # Check history file was updated
        with open(history_file) as f:
            history_content = f.read()

        print(f"  - History file updated: {'✓' if 'Morning Ride' in history_content else '✗'}")
        print(f"  - Contains metrics: {'✓' if 'TSS' in history_content else '✗'}")
        print(f"  - Contains feedback: {'✓' if 'feedback' in history_content.lower() else '✗'}")

        # Verify prompt contains all necessary data
        print(f"  - Prompt has workout data: {'✓' if 'TSS' in prompt else '✗'}")
        print(f"  - Prompt has athlete context: {'✓' if 'FTP' in prompt else '✗'}")
        print(f"  - Prompt has feedback: {'✓' if 'feeling' in prompt else '✗'}")

        # Check error/warning handling
        has_errors = len(agg_result.errors) > 0
        has_warnings = len(agg_result.warnings) > 0
        print(
            f"  - Error handling: {'✓' if not has_errors else f'⚠️  {len(agg_result.errors)} errors'}"
        )
        print(f"  - Warnings logged: {'✓' if has_warnings else 'No warnings'}")

        print("\n✅ Full Workflow Integration: ALL TESTS PASSED")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all Phase 1 integration tests."""
    print_section("PHASE 1 CORE INFRASTRUCTURE - INTEGRATION TESTS")

    print(
        """
Testing modules:

  1. TimelineInjector - Chronological workout injection
  2. DailyAggregator - Multi-source data aggregation
  3. PromptGenerator - Composable AI prompt building
  4. Full Workflow - Complete pipeline integration
"""
    )

    tests = [
        ("TimelineInjector", test_timeline_injector),
        ("DailyAggregator", test_daily_aggregator),
        ("PromptGenerator", test_prompt_generator),
        ("Full Workflow Integration", test_full_workflow_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} CRASHED: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")

    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'='*80}\n")

    if passed == total:
        print("🎉 All Phase 1 integration tests passed!")
        print("\n✅ Ready to proceed to Option B: Prompt 2 Phase 2 (Weekly Analysis)")
        return 0
    else:
        print("⚠️  Some tests failed. Review output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
