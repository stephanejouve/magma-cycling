"""Parsing de pages collection (listing) whatsonzwift.com."""

import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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
