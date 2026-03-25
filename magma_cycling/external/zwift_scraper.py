"""HTML scraping utilities for whatsonzwift.com workout data.

Façade preserving the original ``ZwiftWorkoutScraper`` public API.
Implementation is split across :pymod:`magma_cycling.external.scraper`.
"""

from magma_cycling.external.scraper.detail import _infer_category, parse_workout_detail
from magma_cycling.external.scraper.listing import (
    parse_collection_url,
    parse_workout_metadata_from_listing,
)
from magma_cycling.external.scraper.patterns import (
    _extract_work_segments,
    _find_repeating_block,
    detect_pattern,
)
from magma_cycling.external.scraper.segments import (
    parse_duration_seconds,
    parse_segments_from_soup,
    parse_segments_from_text,
)


class ZwiftWorkoutScraper:
    """Scraper for whatsonzwift.com workout pages.

    Handles parsing of both collection listing pages and individual workout detail pages.
    """

    # Public API
    parse_workout_metadata_from_listing = staticmethod(parse_workout_metadata_from_listing)
    parse_workout_detail = staticmethod(parse_workout_detail)
    detect_pattern = staticmethod(detect_pattern)
    parse_collection_url = staticmethod(parse_collection_url)

    # Private helpers (preserved for backward compatibility)
    _infer_category = staticmethod(_infer_category)
    _parse_segments_from_soup = staticmethod(parse_segments_from_soup)
    _parse_duration_seconds = staticmethod(parse_duration_seconds)
    _parse_segments_from_text = staticmethod(parse_segments_from_text)
    _extract_work_segments = staticmethod(_extract_work_segments)
    _find_repeating_block = staticmethod(_find_repeating_block)
