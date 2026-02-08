#!/usr/bin/env python3
"""
Test memory_graph visualization tool on cyclisme-training-logs data structures.
"""
import json
from pathlib import Path

import memory_graph as mg

# Load real planning data
planning_file = Path(
    "/Users/stephanejouve/training-logs/data/week_planning/week_planning_S079.json"
)

with open(planning_file) as f:
    planning_data = json.load(f)

# Extract key structures
week_id = planning_data["week_id"]
tss_target = planning_data["tss_target"]
sessions = planning_data["planned_sessions"]

# Create some references to show aliasing
first_session = sessions[0]
last_session = sessions[-1]

# Create a shallow copy to demonstrate difference
sessions_copy = sessions.copy()

# Visualize the local variables - use .gv format (doesn't require Graphviz binary)
print("Generating memory graph visualization...")
try:
    mg.render(locals(), "memory_graph_planning.gv")
    print("✅ Visualization saved to: memory_graph_planning.gv")
    print(
        "   (Graphviz source format - can be viewed at https://dreampuf.github.io/GraphvizOnline/)"
    )
except Exception as e:
    print(f"❌ Error: {e}")

# Now let's test with a more complex structure showing session references
session_dict = {
    "pending": [s for s in sessions if s["status"] == "pending"],
    "completed": [s for s in sessions if s["status"] == "completed"],
    "skipped": [s for s in sessions if s["status"] == "skipped"],
}

print("\nGenerating session status graph...")
try:
    mg.render(locals(), "memory_graph_sessions.gv")
    print("✅ Visualization saved to: memory_graph_sessions.gv")
except Exception as e:
    print(f"❌ Error: {e}")
