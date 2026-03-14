"""HTML scraping utilities for whatsonzwift.com workout data."""

import logging
import re

from bs4 import BeautifulSoup

from magma_cycling.external.zwift_models import (
    SegmentType,
    ZwiftCategory,
    ZwiftWorkout,
    ZwiftWorkoutSegment,
)

logger = logging.getLogger(__name__)

# Mapping background color in .textbar style → power zone
_COLOR_TO_ZONE = {
    "#7f7f7f": 1,  # Z1 gray (recovery)
    "#338cff": 2,  # Z2 blue (endurance)
    "#4dff4d": 3,  # Z3 green (tempo)
    "#ffcc3f": 4,  # Z4 yellow (threshold/sweet spot)
    "#ff6639": 5,  # Z5 orange (VO2max)
    "#ff330c": 6,  # Z6 red (anaerobic)
}

# Regex for parsing textbar content — handles all observed formats:
#   "8min @ 85rpm, from 50 to 75% FTP"   (ramp)
#   "2min @ 90rpm, 100% FTP"             (steady)
#   "30sec @ 110rpm, 120% FTP"           (steady, seconds)
#   "2min @ 85rpm, from 50 to 30% FTP"   (cooldown ramp)
#   "5min free ride"                      (free ride)
_SEGMENT_RE = re.compile(
    r"(?P<dur_val>\d+)(?P<dur_unit>min|sec|m|s)"
    r"(?:\s*@\s*(?P<cadence>\d+)rpm)?"
    r"(?:,?\s*(?:"
    r"from\s+(?P<pwr_from>\d+)\s+to\s+(?P<pwr_to>\d+)%\s*FTP"
    r"|(?P<pwr_steady>\d+)%\s*FTP"
    r"|free\s*ride"
    r"))?"
)


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

        Uses CSS selectors identified from whatsonzwift.com DOM analysis:
        - ``article > header``  → workout name (h1)
        - ``div.textbar``       → one per interval segment
        - ``p > strong``        → "Duration" and "Stress points" labels
        - ``.bg-zones-z1..z6``  → zone distribution (informational)

        Args:
            html: Raw HTML content from workout detail page
            workout_url: URL of the workout page

        Returns:
            ZwiftWorkout object if parsing successful, None otherwise
        """
        soup = BeautifulSoup(html, "html.parser")

        try:
            # --- Name ---
            article = soup.find("article")
            if article:
                header = article.find("header")
                name_elem = header.find("h1") if header else article.find("h1")
            else:
                name_elem = soup.find("h1")
            name = name_elem.get_text(strip=True) if name_elem else "Unknown Workout"

            # --- Duration & TSS from <p><strong>Duration</strong>: 30m</p> ---
            tss = None
            duration_minutes = None

            for strong in soup.find_all("strong"):
                label = strong.get_text(strip=True).lower()
                # The value is the text node right after the <strong> tag,
                # inside the same <p> parent
                parent_p = strong.parent
                if not parent_p:
                    continue
                sibling_text = parent_p.get_text(strip=True)

                if "duration" in label:
                    dur_match = re.search(r"(\d+)m(?:\s*(\d+)s)?", sibling_text)
                    if dur_match:
                        mins = int(dur_match.group(1))
                        secs = int(dur_match.group(2)) if dur_match.group(2) else 0
                        duration_minutes = mins + (1 if secs > 0 else 0)
                elif "stress" in label:
                    tss_match = re.search(r"(\d+)", sibling_text.replace(label, ""))
                    if tss_match:
                        tss = int(tss_match.group(1))

            # --- Description ---
            description = None
            # The description paragraph typically comes after the zone distribution
            # and contains actual sentences (> 40 chars, no "%" which is zone data)
            if article:
                for p in article.find_all("p"):
                    text = p.get_text(strip=True)
                    if len(text) > 40 and "%" not in text and "FTP" not in text:
                        description = text
                        break

            # --- Sport ---
            sport_match = re.search(r"dimensionSport\s*=\s*'(\w+)'", html)
            sport = sport_match.group(1) if sport_match else "bike"

            # --- Category ---
            page_text = soup.get_text()
            category = ZwiftWorkoutScraper._infer_category(name, page_text)

            # --- Segments (from DOM) ---
            segments = ZwiftWorkoutScraper._parse_segments_from_soup(soup)

            # Validate minimum required fields
            if not name or name == "Unknown Workout":
                logger.warning(f"Could not extract workout name from {workout_url}")
                return None

            if tss is None or duration_minutes is None:
                logger.warning(
                    f"Incomplete metadata for '{name}': tss={tss}, duration={duration_minutes}"
                )
                return None

            workout = ZwiftWorkout(
                name=name,
                category=category,
                duration_minutes=duration_minutes,
                tss=tss,
                url=workout_url,
                description=description or f"Zwift workout - {name}",
                segments=segments,
            )

            logger.info(
                f"Parsed workout: {name} ({duration_minutes}min, {tss} TSS, "
                f"{len(segments)} segments, {sport})"
            )
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
    def _parse_segments_from_soup(soup: BeautifulSoup) -> list[ZwiftWorkoutSegment]:
        """Parse workout segments from the DOM using CSS selectors.

        Each interval is a ``<div class="textbar">`` with:
        - Text content: ``"8min @ 85rpm, from 50 to 75% FTP"``
        - Style attribute with background color indicating zone

        Args:
            soup: BeautifulSoup object of the workout detail page

        Returns:
            List of ZwiftWorkoutSegment objects
        """
        segments: list[ZwiftWorkoutSegment] = []
        article = soup.find("article")
        if not article:
            logger.warning("No <article> element found on page")
            return segments

        # Only take textbars from the first <section> inside article
        # (the second section contains "similar workouts" with their own textbars)
        first_section = article.find("section")
        if not first_section:
            logger.warning("No <section> found inside <article>")
            return segments

        textbars = first_section.find_all("div", class_="textbar")
        if not textbars:
            logger.warning("No div.textbar elements found")
            return segments

        total = len(textbars)
        for idx, bar in enumerate(textbars):
            text = bar.get_text(strip=True)
            match = _SEGMENT_RE.search(text)
            if not match:
                logger.debug(f"Could not parse textbar: {text!r}")
                continue

            # Duration
            dur_val = int(match.group("dur_val"))
            dur_unit = match.group("dur_unit")
            if dur_unit in ("min", "m"):
                duration_seconds = dur_val * 60
            else:
                duration_seconds = dur_val

            # Cadence
            cadence = int(match.group("cadence")) if match.group("cadence") else None

            # Power & segment type
            pwr_from = match.group("pwr_from")
            pwr_to = match.group("pwr_to")
            pwr_steady = match.group("pwr_steady")

            if pwr_from and pwr_to:
                # Ramp segment
                power_low = int(pwr_from)
                power_high = int(pwr_to)
                if idx == 0:
                    seg_type = SegmentType.WARMUP
                elif idx == total - 1:
                    seg_type = SegmentType.COOLDOWN
                else:
                    seg_type = SegmentType.RAMP
            elif pwr_steady:
                power_val = int(pwr_steady)
                power_low = power_val
                power_high = None
                # Classify by power zone
                if power_val <= 55:
                    seg_type = SegmentType.RECOVERY
                elif power_val <= 75:
                    seg_type = SegmentType.STEADY  # endurance
                elif power_val <= 105:
                    seg_type = SegmentType.STEADY  # tempo/threshold
                else:
                    seg_type = SegmentType.INTERVAL  # above threshold
            elif "free ride" in text.lower():
                power_low = None
                power_high = None
                seg_type = SegmentType.FREE_RIDE
            else:
                logger.debug(f"No power data in textbar: {text!r}")
                continue

            segments.append(
                ZwiftWorkoutSegment(
                    segment_type=seg_type,
                    duration_seconds=duration_seconds,
                    power_low=power_low,
                    power_high=power_high,
                    cadence=cadence,
                )
            )

        logger.info(f"Parsed {len(segments)} segments from {total} textbar elements")
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
