"""Race circuit knowledge base: load, match, and enrich events."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RaceKnowledge:
    """Load and query the circuit knowledge base."""

    def __init__(self, kb_path: Path):
        """Initialize from a circuits.json file.

        Args:
            kb_path: Path to the circuits.json knowledge base file.
        """
        self.kb_path = kb_path
        self.circuits: dict[str, dict] = {}
        self._load(kb_path)

    def _load(self, kb_path: Path) -> None:
        """Load circuits from JSON file."""
        try:
            self.circuits = json.loads(kb_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("Circuit KB not found: %s", kb_path)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in circuit KB %s: %s", kb_path, e)

    def find_circuit(self, event_name: str) -> dict | None:
        """Match event name against circuits by name/aliases.

        Uses case-insensitive substring matching: if a circuit name or
        any of its aliases appears within the event_name, it's a match.

        Args:
            event_name: The event name from Intervals.icu (e.g. "ZRL - The Classic").

        Returns:
            Circuit dict if found, None otherwise.
        """
        if not event_name:
            return None

        name_lower = event_name.lower()

        for key, circuit in self.circuits.items():
            # Check canonical name
            if circuit.get("name", "").lower() in name_lower:
                return circuit

            # Check aliases
            for alias in circuit.get("aliases", []):
                if alias.lower() in name_lower:
                    return circuit

        return None

    def enrich_event(self, event: dict) -> dict:
        """Add circuit metadata to a raw Intervals.icu event dict.

        Args:
            event: Raw event dict from get_events().

        Returns:
            Enriched event dict with 'circuit' key if match found.
        """
        enriched = dict(event)
        event_name = event.get("name", "")
        circuit = self.find_circuit(event_name)
        if circuit:
            enriched["circuit"] = circuit
        return enriched
