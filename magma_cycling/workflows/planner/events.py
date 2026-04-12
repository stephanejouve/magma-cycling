"""Events loading and formatting for WeeklyPlanner."""

import logging
import sys

from magma_cycling.race_knowledge import RaceKnowledge

logger = logging.getLogger(__name__)

# Event categories to exclude from the planning prompt
_EXCLUDED_CATEGORIES = {"WORKOUT"}


class EventsMixin:
    """Load and format upcoming events for prompt injection."""

    def _load_week_events_section(self) -> str:
        """Fetch events, enrich with KB, return formatted markdown.

        Returns:
            Formatted markdown section or empty string if no events.
        """
        events = self._fetch_week_events()
        if not events:
            return ""

        kb = self._load_race_kb()
        formatted = self._format_events(events, kb)
        return formatted

    def _fetch_week_events(self) -> list[dict]:
        """Fetch events from Intervals.icu for the planned week."""
        if not self.api:
            return []

        oldest = self.start_date.strftime("%Y-%m-%d")
        newest = self.end_date.strftime("%Y-%m-%d")

        try:
            events = self.api.get_events(oldest=oldest, newest=newest)
        except Exception as e:
            print(f"  \u26a0\ufe0f Events API error: {e}", file=sys.stderr)
            return []

        # Filter out workouts, keep RACE, TARGET, NOTE, etc.
        return [e for e in events if e.get("category", "") not in _EXCLUDED_CATEGORIES]

    def _load_race_kb(self) -> RaceKnowledge | None:
        """Load race knowledge base from data repo."""
        try:
            from magma_cycling.config import get_data_config

            config = get_data_config()
            kb_path = config.data_repo_path / "data" / "race_knowledge" / "circuits.json"
            if kb_path.exists():
                return RaceKnowledge(kb_path)
        except Exception as e:
            logger.debug("Race KB unavailable: %s", e)
        return None

    def _format_events(self, events: list[dict], kb: RaceKnowledge | None) -> str:
        """Format events into a markdown section for the prompt."""
        # Sort by start date
        events_sorted = sorted(events, key=lambda e: e.get("start_date_local", ""))

        lines = ["\n## Competitions & Evenements cette semaine\n"]

        for event in events_sorted:
            enriched = kb.enrich_event(event) if kb else event
            lines.append(self._format_single_event(enriched))

        return "\n".join(lines)

    def _format_single_event(self, event: dict) -> str:
        """Format a single event as markdown."""
        name = event.get("name", "Evenement sans nom")
        date_str = event.get("start_date_local", "")[:10]
        category = event.get("category", "")
        description = event.get("description", "")

        # Format date to dd/mm
        display_date = date_str
        if len(date_str) == 10:
            parts = date_str.split("-")
            display_date = f"{parts[2]}/{parts[1]}"

        header = f"### {display_date} — {name}"
        if category:
            header += f" ({category})"

        lines = [header]

        circuit = event.get("circuit")
        if circuit:
            world = circuit.get("world", "")
            region = circuit.get("region", "")
            location = f"{region} ({world})" if world and region else world or region
            if location:
                lines.append(f"- **Circuit** : {location}")

            dist = circuit.get("distance_km")
            elev = circuit.get("elevation_m")
            if dist is not None:
                lines.append(f"- **Distance/tour** : {dist} km / {elev} m D+")

            profile = circuit.get("profile")
            grade = circuit.get("grade_avg_pct")
            if profile:
                profile_str = f"- **Profil** : {profile.capitalize()}"
                if grade is not None:
                    profile_str += f" (grade moyen {grade}%)"
                lines.append(profile_str)

            segments = circuit.get("segments", [])
            if segments:
                lines.append(f"- **Segments** : {', '.join(segments)}")

            tactical = circuit.get("tactical_notes")
            if tactical:
                lines.append(f"- **Tactique** : {tactical}")

        if description:
            lines.append(f"- **Notes** : {description}")

        lines.append(
            "\n> **Impact planification** : Repos ou activation legere J-1, "
            "recuperation J+1. Pre-fatigue a eviter sur les 48h precedentes.\n"
        )

        return "\n".join(lines)
