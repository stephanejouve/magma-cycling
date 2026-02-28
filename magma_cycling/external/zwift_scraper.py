"""HTML scraping utilities for whatsonzwift.com workout data."""

import logging
import re

from bs4 import BeautifulSoup

from magma_cycling.external.zwift_models import (
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)

logger = logging.getLogger(__name__)


class ZwiftWorkoutScraper:
    """Scraper for whatsonzwift.com workout pages.

    Handles parsing of both collection listing pages and individual workout detail pages.
    """

    @staticmethod
    def parse_workout_metadata_from_listing(html: str, base_url: str) -> list[dict]:
        """Parse workout metadata from a collection listing page.

        Args:
            html: Raw HTML content from collection page
            base_url: Base URL for constructing full workout URLs

        Returns:
            List of dicts with basic workout metadata (name, duration, tss, url)
        """
        soup = BeautifulSoup(html, "html.parser")
        workouts = []

        # Find all workout links in the collection
        # Based on WebFetch analysis: links are in <a> tags with workout paths
        for link in soup.find_all("a", href=re.compile(r"/workouts/[\w-]+/[\w-]+")):
            workout_url = link.get("href")
            if not workout_url.startswith("http"):
                workout_url = f"{base_url}{workout_url}"

            # Extract workout name from link text or nearby elements
            workout_name = link.get_text(strip=True) or "Unknown Workout"

            # Try to find TSS and duration in surrounding elements
            # This is approximate - actual structure may vary
            parent = link.parent
            duration_text = None
            tss_text = None

            if parent:
                # Look for duration and TSS in parent siblings/children
                for elem in parent.find_all(string=True):
                    text = elem.strip()
                    # Duration patterns: "40m30s", "55m", etc.
                    if re.match(r"\d+m", text):
                        duration_text = text
                    # TSS patterns: number between 1-500
                    elif text.isdigit() and 1 <= int(text) <= 500:
                        tss_text = text

            workouts.append(
                {
                    "name": workout_name,
                    "url": workout_url,
                    "duration_text": duration_text,
                    "tss": int(tss_text) if tss_text else None,
                }
            )

        logger.info(f"Parsed {len(workouts)} workouts from collection listing")
        return workouts

    @staticmethod
    def parse_workout_detail(html: str, workout_url: str) -> ZwiftWorkout | None:
        """Parse complete workout details from an individual workout page.

        Args:
            html: Raw HTML content from workout detail page
            workout_url: URL of the workout page

        Returns:
            ZwiftWorkout object if parsing successful, None otherwise
        """
        soup = BeautifulSoup(html, "html.parser")

        try:
            # Extract workout name
            # Look for title or heading elements
            name_elem = soup.find("h1") or soup.find("title")
            name = name_elem.get_text(strip=True) if name_elem else "Unknown Workout"

            # Clean up name (remove "Zwift", "workout", etc.)
            name = re.sub(r"(?i)(zwift|workout|:|\|)", "", name).strip()

            # Extract TSS (look for "stress points" or "TSS" labels)
            tss = None
            tss_patterns = [r"(\d+)\s*(?:stress\s*points?|TSS)", r"TSS:\s*(\d+)"]
            page_text = soup.get_text()
            for pattern in tss_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    tss = int(match.group(1))
                    break

            # Extract duration (look for "XXm" or "XXmYYs" patterns)
            duration_minutes = None
            duration_match = re.search(r"(\d+)m(?:\s*(\d+)s)?", page_text)
            if duration_match:
                minutes = int(duration_match.group(1))
                seconds = int(duration_match.group(2)) if duration_match.group(2) else 0
                duration_minutes = minutes + (1 if seconds > 0 else 0)  # Round up

            # Try to infer category from workout name or description
            category = ZwiftWorkoutScraper._infer_category(name, page_text)

            # Parse workout segments
            segments = ZwiftWorkoutScraper._parse_segments_from_text(page_text)

            if not all([name, tss, duration_minutes]):
                logger.warning(
                    f"Incomplete workout metadata: name={name}, tss={tss}, duration={duration_minutes}"
                )
                return None

            workout = ZwiftWorkout(
                name=name,
                category=category,
                duration_minutes=duration_minutes,
                tss=tss,
                url=workout_url,
                description=f"Zwift - {name}",
                segments=segments,
            )

            logger.info(f"Successfully parsed workout: {name}")
            return workout

        except Exception as e:
            logger.error(f"Failed to parse workout from {workout_url}: {e}")
            return None

    @staticmethod
    def _infer_category(name: str, description: str) -> ZwiftCategory:
        """Infer workout category from name and description.

        Args:
            name: Workout name
            description: Workout description text

        Returns:
            Best-guess ZwiftCategory
        """
        text = (name + " " + description).lower()

        # Category keyword mapping
        category_keywords = {
            ZwiftCategory.FTP: ["ftp", "threshold", "sweet spot"],
            ZwiftCategory.INTERVALS: ["interval", "repeat"],
            ZwiftCategory.VO2MAX: ["vo2", "vo2max", "max"],
            ZwiftCategory.ENDURANCE: ["endurance", "base", "zone 2"],
            ZwiftCategory.RECOVERY: ["recovery", "easy", "active recovery"],
            ZwiftCategory.SPRINT: ["sprint", "burst"],
            ZwiftCategory.CLIMBING: ["climb", "hill"],
            ZwiftCategory.TEMPO: ["tempo"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category

        # Default to mixed if no clear category
        return ZwiftCategory.MIXED

    @staticmethod
    def _parse_segments_from_text(text: str) -> list[ZwiftWorkoutSegment]:
        """Parse workout segments from text description.

        This is a simplified implementation that tries to extract basic segment info.
        A full implementation would need more sophisticated parsing of workout structure.

        Args:
            text: Full page text content

        Returns:
            List of ZwiftWorkoutSegment objects
        """
        segments = []

        # This is a placeholder implementation
        # Full implementation would require more detailed HTML/text parsing
        # Would parse patterns like:
        # - "7min from 50 to 75% FTP" (ramps)
        # - "Xmin @ Y% FTP" (steady)
        # - "Xmin free ride" (free ride)
        logger.debug("Segment parsing from text is a simplified placeholder")

        return segments

    @staticmethod
    def parse_collection_url(
        collection_url: str, base_url: str = "https://whatsonzwift.com"
    ) -> str:
        """Ensure collection URL is fully qualified.

        Args:
            collection_url: Collection URL (may be relative or absolute)
            base_url: Base URL for whatsonzwift.com

        Returns:
            Fully qualified URL
        """
        if collection_url.startswith("http"):
            return collection_url
        if collection_url.startswith("/"):
            return f"{base_url}{collection_url}"
        return f"{base_url}/workouts/{collection_url}"
