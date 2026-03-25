"""StorageMixin — JSON persistence for intelligence state."""

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from magma_cycling.intelligence.models import (
    AnalysisLevel,
    ConfidenceLevel,
    Pattern,
    ProtocolAdaptation,
    TrainingLearning,
)


class StorageMixin:
    """JSON file persistence for the three intelligence stores."""

    def save_to_file(self, file_path: Path) -> None:
        """Save intelligence state to JSON file.

        Args:
            file_path: Path to save file (in-memory, no hardcoded paths)

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> from pathlib import Path
            >>> intelligence.save_to_file(Path("/tmp/intelligence_state.json"))
        """

        def serialize_obj(obj: Any) -> Any:
            """Serialize dataclass objects to dict."""
            if isinstance(obj, TrainingLearning | Pattern | ProtocolAdaptation):
                data = asdict(obj)
                # Convert enums to strings
                if "level" in data and isinstance(data["level"], AnalysisLevel):
                    data["level"] = data["level"].value
                if "confidence" in data and isinstance(data["confidence"], ConfidenceLevel):
                    data["confidence"] = data["confidence"].value
                # Convert datetime/date to ISO format
                if "timestamp" in data and isinstance(data["timestamp"], datetime):
                    data["timestamp"] = data["timestamp"].isoformat()
                if "first_seen" in data and isinstance(data["first_seen"], date):
                    data["first_seen"] = data["first_seen"].isoformat()
                if "last_seen" in data and isinstance(data["last_seen"], date):
                    data["last_seen"] = data["last_seen"].isoformat()
                return data
            return obj

        state = {
            "learnings": {lid: serialize_obj(lrn) for lid, lrn in self.learnings.items()},
            "patterns": {pid: serialize_obj(p) for pid, p in self.patterns.items()},
            "adaptations": {aid: serialize_obj(a) for aid, a in self.adaptations.items()},
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "StorageMixin":
        """Load intelligence state from JSON file.

        Args:
            file_path: Path to load file (in-memory, no hardcoded paths)

        Returns:
            TrainingIntelligence: Loaded instance

        Example:
            >>> from pathlib import Path
            >>> intelligence = TrainingIntelligence.load_from_file(
            ...     Path("/tmp/intelligence_state.json")
            ... )
        """
        with open(file_path, encoding="utf-8") as f:
            state = json.load(f)

        intelligence = cls()

        # Load learnings
        for learning_id, learning_data in state.get("learnings", {}).items():
            learning_data["level"] = AnalysisLevel(learning_data["level"])
            learning_data["confidence"] = ConfidenceLevel(learning_data["confidence"])
            learning_data["timestamp"] = datetime.fromisoformat(learning_data["timestamp"])
            intelligence.learnings[learning_id] = TrainingLearning(**learning_data)

        # Load patterns
        for pattern_id, pattern_data in state.get("patterns", {}).items():
            pattern_data["confidence"] = ConfidenceLevel(pattern_data["confidence"])
            pattern_data["first_seen"] = date.fromisoformat(pattern_data["first_seen"])
            pattern_data["last_seen"] = date.fromisoformat(pattern_data["last_seen"])
            intelligence.patterns[pattern_id] = Pattern(**pattern_data)

        # Load adaptations
        for adaptation_id, adaptation_data in state.get("adaptations", {}).items():
            adaptation_data["confidence"] = ConfidenceLevel(adaptation_data["confidence"])
            intelligence.adaptations[adaptation_id] = ProtocolAdaptation(**adaptation_data)

        return intelligence
