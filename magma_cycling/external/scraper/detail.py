"""Parsing de page workout individuel whatsonzwift.com."""

import logging
import re

from bs4 import BeautifulSoup

from magma_cycling.external.scraper.patterns import detect_pattern
from magma_cycling.external.scraper.segments import parse_segments_from_text
from magma_cycling.external.zwift_models import ZwiftCategory, ZwiftWorkout

logger = logging.getLogger(__name__)


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
            parent_p = strong.parent
            if not parent_p:
                continue
            sibling_text = parent_p.get_text(strip=True)

            if "duration" in label:
                # Try hour+minute format: "1h30m"
                dur_match = re.search(r"(\d+)h\s*(\d+)m", sibling_text)
                if dur_match:
                    duration_minutes = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
                else:
                    dur_match = re.search(r"(\d+)m(?:\s*(\d+)s)?", sibling_text)
                    if dur_match:
                        mins = int(dur_match.group(1))
                        secs = int(dur_match.group(2)) if dur_match.group(2) else 0
                        duration_minutes = mins + (1 if secs > 0 else 0)
            elif "stress" in label:
                tss_match = re.search(r"(\d+)", sibling_text.replace(label, ""))
                if tss_match:
                    tss = int(tss_match.group(1))

        # Fallback: regex on page text if DOM extraction missed values
        page_text = soup.get_text(separator="\n")
        if tss is None:
            tss_patterns = [
                r"(\d+)\s*(?:stress\s*points?|TSS)",
                r"(?:stress\s*points?|TSS)\s*:?\s*(\d+)",
            ]
            for pat in tss_patterns:
                match = re.search(pat, page_text, re.IGNORECASE)
                if match:
                    tss = int(match.group(1))
                    break

        if duration_minutes is None:
            dur_match = re.search(r"(\d+)h\s*(\d+)m", page_text)
            if dur_match:
                duration_minutes = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
            else:
                dur_match = re.search(r"(\d+)m(?:\s*(\d+)s)?", page_text)
                if dur_match:
                    minutes = int(dur_match.group(1))
                    seconds = int(dur_match.group(2)) if dur_match.group(2) else 0
                    duration_minutes = minutes + (1 if seconds > 0 else 0)

        # --- Description ---
        description = None
        if article:
            for p in article.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 40 and "%" not in text and "FTP" not in text:
                    description = text
                    break

        # --- Sport ---
        sport_match = re.search(r"dimensionSport\s*=\s*'(\w+)'", html)
        sport = sport_match.group(1) if sport_match else "bike"

        # --- Category (URL-based inference takes priority) ---
        category = _infer_category(name, page_text, workout_url)

        # --- Segments from textbar containers (first section only) ---
        # The second <section> inside <article> contains "Similar Workouts"
        search_scope = soup
        if article:
            first_section = article.find("section")
            if first_section:
                search_scope = first_section
        textbars = search_scope.find_all("div", class_="textbar")
        if textbars:
            segment_lines = [tb.get_text(separator=" ").strip() for tb in textbars]
            segment_text = "\n".join(segment_lines)
        else:
            segment_text = page_text
        segments = parse_segments_from_text(segment_text)

        # Validate minimum required fields
        if not name or name == "Unknown Workout":
            logger.warning(f"Could not extract workout name from {workout_url}")
            return None

        if tss is None or duration_minutes is None:
            logger.warning(
                f"Incomplete metadata for '{name}': tss={tss}, duration={duration_minutes}"
            )
            return None

        # Detect structural pattern from parsed segments
        pattern = detect_pattern(segments)

        workout = ZwiftWorkout(
            name=name,
            category=category,
            duration_minutes=duration_minutes,
            tss=tss,
            url=workout_url,
            description=description or f"Zwift workout - {name}",
            segments=segments,
            pattern=pattern,
        )

        logger.info(
            f"Parsed workout: {name} ({duration_minutes}min, {tss} TSS, "
            f"{len(segments)} segments, {sport})"
        )
        return workout

    except Exception as e:
        logger.error(f"Failed to parse workout from {workout_url}: {e}")
        return None


def _infer_category(name: str, description: str, url: str = "") -> ZwiftCategory:
    """Infer workout category from URL path, name and description.

    URL-based inference takes priority over keyword matching to avoid
    false positives from navigation links in the page text.

    Args:
        name: Workout name
        description: Workout description text
        url: Workout URL for path-based inference

    Returns:
        Best-guess ZwiftCategory
    """
    # Priority 1: URL path-based inference (most reliable)
    url_mapping = {
        "/endurance/": ZwiftCategory.ENDURANCE,
        "/sweet-spot/": ZwiftCategory.FTP,
        "/threshold/": ZwiftCategory.THRESHOLD,
        "/vo2-max/": ZwiftCategory.VO2MAX,
        "/recovery/": ZwiftCategory.RECOVERY,
        "/sprinting/": ZwiftCategory.SPRINT,
        "/climbing/": ZwiftCategory.CLIMBING,
        "/ftp-tests/": ZwiftCategory.FTP,
        "/ftp-builder/": ZwiftCategory.FTP,
    }
    url_lower = url.lower()
    for path, category in url_mapping.items():
        if path in url_lower:
            return category

    # Priority 2: keyword matching on name only (not full page text)
    text = name.lower()

    # Category keyword mapping
    category_keywords = {
        ZwiftCategory.FTP: ["ftp", "threshold", "sweet spot"],
        ZwiftCategory.INTERVALS: ["interval", "repeat"],
        ZwiftCategory.VO2MAX: ["vo2", "vo2max"],
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
