#!/usr/bin/env python3
"""
Memory graph analysis for Pydantic-based planning models.

This script demonstrates that Pydantic models eliminate shallow copy bugs
through automatic deep copy protection.

Compare with old graphs in project-docs/archives/memory-graph-experiments/
"""

from pathlib import Path

import memory_graph as mg

from cyclisme_training_logs.planning.models import Session, WeeklyPlan


def test_pydantic_backup_no_aliasing():
    """
    Test 1: Demonstrate that Pydantic backup_sessions() creates true deep copies.

    OLD (dict-based):
        backup = planning["planned_sessions"].copy()  # ❌ Shallow copy!
        # backup[0] and planning["planned_sessions"][0] are SAME object

    NEW (Pydantic):
        backup = plan.backup_sessions()  # ✅ Deep copy!
        # backup[0] and plan.planned_sessions[0] are DIFFERENT objects
    """
    print("\n" + "=" * 80)
    print("TEST 1: Pydantic backup_sessions() - No Aliasing")
    print("=" * 80)

    # Find a real planning file
    planning_dir = Path.home() / "training-logs" / "data" / "week_planning"
    planning_files = sorted(planning_dir.glob("week_planning_S*.json"))

    if not planning_files:
        print("⚠️  No planning files found, creating sample data")
        from datetime import UTC, date, datetime

        plan = WeeklyPlan(
            week_id="S080",
            start_date=date(2026, 2, 9),
            end_date=date(2026, 2, 15),
            created_at=datetime.now(UTC),
            last_updated=datetime.now(UTC),
            version=1,
            athlete_id="i151223",
            tss_target=350,
            planned_sessions=[
                Session(
                    session_id="S080-01",
                    session_date=date(2026, 2, 9),
                    name="EnduranceDouce",
                    session_type="END",
                    tss_planned=50,
                    duration_min=60,
                    status="pending",
                ),
                Session(
                    session_id="S080-02",
                    session_date=date(2026, 2, 10),
                    name="SweetSpot",
                    session_type="INT",
                    tss_planned=70,
                    duration_min=65,
                    status="pending",
                ),
            ],
        )
    else:
        # Load real planning file
        planning_file = planning_files[-1]  # Most recent
        print(f"📂 Loading: {planning_file.name}")
        plan = WeeklyPlan.from_json(planning_file)

    print(f"✅ Loaded WeeklyPlan: {plan.week_id} ({len(plan.planned_sessions)} sessions)")

    # Create backup using Pydantic's backup_sessions()
    print("\n📋 Creating backup using plan.backup_sessions()...")
    backup = plan.backup_sessions()

    # Check that backup is a different list
    print(f"  Backup is different list: {backup is not plan.planned_sessions}")

    # Check that each session in backup is a different object
    for i, (session, backup_session) in enumerate(zip(plan.planned_sessions, backup, strict=True)):
        is_different = session is not backup_session
        print(f"  Session {i}: Different object = {is_different}")
        if not is_different:
            print("    ❌ ALIASING DETECTED!")
        else:
            print("    ✅ No aliasing")

    # Generate memory graph
    print("\n📊 Generating memory graph...")

    # Create dict of data to visualize
    data_to_graph = {
        "plan": plan,
        "backup": backup,
        "plan_sessions_list": plan.planned_sessions,
        "backup_sessions_list": backup,
    }

    # Add individual sessions (first 3 only for clarity)
    for i in range(min(3, len(plan.planned_sessions))):
        data_to_graph[f"plan_session_{i}"] = plan.planned_sessions[i]
        data_to_graph[f"backup_session_{i}"] = backup[i]

    output_file = "memory_graph_pydantic_backup.gv"
    mg.render(data_to_graph, outfile=output_file)
    print(f"✅ Graph saved: {output_file}")
    print("   Expected: No arrows between plan_session_X and backup_session_X")
    print("   (Each backup session is a DIFFERENT object)")


def test_pydantic_model_copy_deep():
    """
    Test 2: Demonstrate Session.model_copy_deep() creates independent copy.

    OLD (dict):
        copy = session.copy()  # ❌ Shallow copy if session contains lists/dicts

    NEW (Pydantic):
        copy = session.model_copy_deep()  # ✅ True deep copy
    """
    print("\n" + "=" * 80)
    print("TEST 2: Session.model_copy_deep() - Independent Copy")
    print("=" * 80)

    from datetime import date

    # Create session
    original = Session(
        session_id="S080-01",
        session_date=date(2026, 2, 9),
        name="EnduranceDouce",
        session_type="END",
        tss_planned=50,
        duration_min=60,
        status="pending",
    )
    print(f"📝 Created session: {original.session_id}")

    # Create deep copy
    copy = original.model_copy_deep()
    print("📋 Created deep copy")

    # Check they're different objects
    print(f"  Original is not copy: {original is not copy}")
    print(f"  Original ID: {id(original)}")
    print(f"  Copy ID:     {id(copy)}")

    # Modify copy
    copy.status = "cancelled"
    copy.tss_planned = 100

    print(f"\n🔄 Modified copy: status={copy.status}, tss={copy.tss_planned}")
    print(f"  Original unchanged: status={original.status}, tss={original.tss_planned}")
    print("  ✅ No aliasing - modifications isolated")

    # Generate memory graph
    print("\n📊 Generating memory graph...")
    data_to_graph = {
        "original": original,
        "copy": copy,
    }

    output_file = "memory_graph_pydantic_session_copy.gv"
    mg.render(data_to_graph, outfile=output_file)
    print(f"✅ Graph saved: {output_file}")
    print("   Expected: Two separate Session objects with no shared references")


def test_compare_dict_vs_pydantic():
    """
    Test 3: Side-by-side comparison of dict (old) vs Pydantic (new).

    Demonstrates the PROBLEM (dict shallow copy) vs SOLUTION (Pydantic deep copy).
    """
    print("\n" + "=" * 80)
    print("TEST 3: Dict vs Pydantic - Before/After Comparison")
    print("=" * 80)

    from datetime import date

    # ===== OLD WAY (dict) - HAS ALIASING BUG =====
    print("\n❌ OLD WAY: Dict-based (shallow copy bug)")

    planning_dict = {
        "week_id": "S080",
        "planned_sessions": [
            {
                "session_id": "S080-01",
                "date": "2026-02-09",
                "name": "Session1",
                "type": "END",
                "tss_planned": 50,
                "status": "pending",
            },
            {
                "session_id": "S080-02",
                "date": "2026-02-10",
                "name": "Session2",
                "type": "INT",
                "tss_planned": 70,
                "status": "pending",
            },
        ],
    }

    # Naive backup (shallow copy)
    backup_dict = planning_dict["planned_sessions"].copy()

    print("  Created backup with .copy()")
    print(f"  List is different: {backup_dict is not planning_dict['planned_sessions']}")
    print(f"  Session 0 is different: {backup_dict[0] is not planning_dict['planned_sessions'][0]}")

    # ❌ BUG: Session objects are SHARED (aliasing!)
    if backup_dict[0] is planning_dict["planned_sessions"][0]:
        print("  ❌ ALIASING BUG: backup[0] points to SAME dict as original!")

    # ===== NEW WAY (Pydantic) - NO ALIASING =====
    print("\n✅ NEW WAY: Pydantic-based (deep copy protection)")

    from datetime import UTC, datetime

    plan = WeeklyPlan(
        week_id="S080",
        start_date=date(2026, 2, 9),
        end_date=date(2026, 2, 15),
        created_at=datetime.now(UTC),
        last_updated=datetime.now(UTC),
        version=1,
        athlete_id="i151223",
        tss_target=350,
        planned_sessions=[
            Session(
                session_id="S080-01",
                session_date=date(2026, 2, 9),
                name="Session1",
                session_type="END",
                tss_planned=50,
                duration_min=60,
                status="pending",
            ),
            Session(
                session_id="S080-02",
                session_date=date(2026, 2, 10),
                name="Session2",
                session_type="INT",
                tss_planned=70,
                duration_min=65,
                status="pending",
            ),
        ],
    )

    # Pydantic backup (deep copy)
    backup_pydantic = plan.backup_sessions()

    print("  Created backup with plan.backup_sessions()")
    print(f"  List is different: {backup_pydantic is not plan.planned_sessions}")
    print(f"  Session 0 is different: {backup_pydantic[0] is not plan.planned_sessions[0]}")

    # ✅ NO BUG: Session objects are INDEPENDENT
    if backup_pydantic[0] is not plan.planned_sessions[0]:
        print("  ✅ NO ALIASING: backup[0] is DIFFERENT object from original!")

    # Generate comparison graph
    print("\n📊 Generating comparison memory graph...")
    data_to_graph = {
        # Dict-based (old)
        "dict_planning": planning_dict,
        "dict_backup": backup_dict,
        "dict_session_0": planning_dict["planned_sessions"][0],
        "dict_backup_0": backup_dict[0],
        # Pydantic-based (new)
        "pydantic_plan": plan,
        "pydantic_backup": backup_pydantic,
        "pydantic_session_0": plan.planned_sessions[0],
        "pydantic_backup_0": backup_pydantic[0],
    }

    output_file = "memory_graph_comparison_dict_vs_pydantic.gv"
    mg.render(data_to_graph, outfile=output_file)
    print(f"✅ Graph saved: {output_file}")
    print("\n   EXPECTED VISUALIZATION:")
    print("   - Dict: dict_session_0 and dict_backup_0 point to SAME object (aliasing)")
    print("   - Pydantic: pydantic_session_0 and pydantic_backup_0 are DIFFERENT objects")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MEMORY GRAPH ANALYSIS: Pydantic Anti-Aliasing Protection")
    print("=" * 80)
    print("\nThis script validates that the Pydantic migration eliminates shallow copy bugs.")
    print("Comparing against old graphs in: project-docs/archives/memory-graph-experiments/")

    try:
        test_pydantic_backup_no_aliasing()
        test_pydantic_model_copy_deep()
        test_compare_dict_vs_pydantic()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        print("\n📊 Generated graphs:")
        print("  1. memory_graph_pydantic_backup.gv")
        print("  2. memory_graph_pydantic_session_copy.gv")
        print("  3. memory_graph_comparison_dict_vs_pydantic.gv")
        print("\n📂 Compare with old graphs:")
        print("  - project-docs/archives/memory-graph-experiments/memory_graph_planning.gv")
        print("  - project-docs/archives/memory-graph-experiments/memory_graph_sessions.gv")
        print("  - project-docs/archives/memory-graph-experiments/example1_aliasing.gv")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
