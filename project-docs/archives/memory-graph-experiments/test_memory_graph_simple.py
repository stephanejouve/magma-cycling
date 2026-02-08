#!/usr/bin/env python3
"""
Simple memory_graph examples showing references and aliasing.
"""
import memory_graph as mg

print("Example 1: List aliasing")
print("=" * 50)

# Create a list and alias it
workouts_week1 = ["END", "INT", "REC"]
workouts_week2 = workouts_week1  # Alias - points to same object!
workouts_week3 = workouts_week1.copy()  # Shallow copy - new object

# Modify through one reference
workouts_week2.append("VO2")

print(f"workouts_week1: {workouts_week1}")
print(f"workouts_week2: {workouts_week2}")
print(f"workouts_week3: {workouts_week3}")
print()

mg.render(locals(), "example1_aliasing.gv")
print("✅ Visualization saved to: example1_aliasing.gv\n")

print("Example 2: Nested structure sharing")
print("=" * 50)

# Create nested structure (common pattern in planning)
session_template = {"type": "END", "duration": 60}
week_planning = {
    "monday": session_template,
    "wednesday": session_template,  # Both point to same dict!
    "friday": session_template.copy(),  # This one is different
}

# Modify one - affects others that share reference
week_planning["monday"]["duration"] = 90

print(f"Monday duration: {week_planning['monday']['duration']}")
print(f"Wednesday duration: {week_planning['wednesday']['duration']}")
print(f"Friday duration: {week_planning['friday']['duration']}")
print()

mg.render(locals(), "example2_nested.gv")
print("✅ Visualization saved to: example2_nested.gv\n")

print("Example 3: Session status tracking (real scenario)")
print("=" * 50)

# Simulate session tracking scenario
all_sessions = [
    {"id": "S080-01", "status": "pending"},
    {"id": "S080-02", "status": "pending"},
    {"id": "S080-03", "status": "completed"},
]

# Create views of the data (references)
pending_sessions = [s for s in all_sessions if s["status"] == "pending"]
completed_sessions = [s for s in all_sessions if s["status"] == "completed"]

# The lists are new, but they contain references to the same dicts!
pending_sessions[0]["status"] = "completed"  # Changes the original dict

print(f"all_sessions: {all_sessions}")
print(f"pending_sessions: {pending_sessions}")
print(f"completed_sessions: {completed_sessions}")
print()

mg.render(locals(), "example3_session_tracking.gv")
print("✅ Visualization saved to: example3_session_tracking.gv\n")

print("All examples generated! You can visualize them at:")
print("https://dreampuf.github.io/GraphvizOnline/")
