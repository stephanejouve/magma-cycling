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
            category = ZwiftWorkoutScraper._infer_category(name, page_text, workout_url)

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
            segments = ZwiftWorkoutScraper._parse_segments_from_text(segment_text)

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
            pattern = ZwiftWorkoutScraper.detect_pattern(segments)

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

    @staticmethod
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
    def _parse_duration_seconds(duration_str: str) -> int | None:
        """Parse duration string to seconds.

        Handles: '7min', '30sec', '1min', '1h2m', '2:00', '0:30'
        """
        # Pattern: Xmin or XmYs
        m = re.match(r"(\d+)\s*min", duration_str)
        if m:
            return int(m.group(1)) * 60

        m = re.match(r"(\d+)\s*sec", duration_str)
        if m:
            return int(m.group(1))

        # Pattern: X:YY (minutes:seconds)
        m = re.match(r"(\d+):(\d+)", duration_str)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))

        return None

    @staticmethod
    def _parse_segments_from_text(text: str) -> list[ZwiftWorkoutSegment]:
        """Parse workout segments from whatsonzwift.com text description.

        Handles formats:
        - "7min from 50 to 75% FTP" (ramps)
        - "12min @ 90rpm, 90% FTP" (steady with cadence)
        - "2min @ 55% FTP" (steady without cadence)
        - "6x 1min @ 60rpm, 90% FTP, 1min @ 90rpm, 90% FTP" (intervals)
        - "30sec free ride" (free ride)

        Args:
            text: Workout text description

        Returns:
            List of ZwiftWorkoutSegment objects
        """
        segments: list[ZwiftWorkoutSegment] = []

        # Note: whatsonzwift.com uses <span> for power values, causing extra
        # spaces like "55 % FTP" instead of "55% FTP". All regexes use \s*%
        # to tolerate this.

        # Ramp pattern: "Xmin from Y to Z% FTP" or "Xmin @ Yrpm, from Z to W% FTP"
        ramp_re = re.compile(
            r"(\d+)\s*min\s+(?:@\s*\d+\s*rpm\s*,\s*)?from\s+(\d+)\s+to\s+(\d+)\s*%\s*FTP",
            re.IGNORECASE,
        )

        # Steady pattern: "Xmin/Xsec [@ [Yrpm,]] Z% FTP" (@ is optional)
        steady_re = re.compile(
            r"(\d+(?:min|sec))\s*(?:@\s*)?(?:(\d+)\s*rpm\s*,\s*)?(\d+)\s*%\s*FTP",
            re.IGNORECASE,
        )

        # Interval pattern: "Nx dur1 @ [cad1,] pwr1% FTP, dur2 @ [cad2,] pwr2% FTP"
        interval_re = re.compile(
            r"(\d+)x\s+"
            r"(\d+(?:min|sec))\s*@\s*(?:(\d+)\s*rpm\s*,\s*)?(\d+)\s*%\s*FTP"
            r"\s*,\s*"
            r"(\d+(?:min|sec))\s*@\s*(?:(\d+)\s*rpm\s*,\s*)?(\d+)\s*%\s*FTP",
            re.IGNORECASE,
        )

        # Free ride pattern: "Xmin free ride"
        freeride_re = re.compile(
            r"(\d+)\s*min\s+free\s+ride",
            re.IGNORECASE,
        )

        # Process line by line
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try interval pattern first (contains "Nx")
            m = interval_re.search(line)
            if m:
                repeat = int(m.group(1))
                dur1 = ZwiftWorkoutScraper._parse_duration_seconds(m.group(2))
                cad1 = int(m.group(3)) if m.group(3) else None
                pwr1 = int(m.group(4))
                dur2 = ZwiftWorkoutScraper._parse_duration_seconds(m.group(5))
                cad2 = int(m.group(6)) if m.group(6) else None
                pwr2 = int(m.group(7))

                if dur1 and dur2:
                    segments.append(
                        ZwiftWorkoutSegment(
                            segment_type=SegmentType.INTERVAL,
                            duration_seconds=dur1,
                            power_low=pwr1,
                            cadence=cad1,
                            repeat_count=repeat,
                        )
                    )
                    segments.append(
                        ZwiftWorkoutSegment(
                            segment_type=SegmentType.RECOVERY,
                            duration_seconds=dur2,
                            power_low=pwr2,
                            cadence=cad2,
                            repeat_count=repeat,
                        )
                    )
                continue

            # Ramp pattern
            m = ramp_re.search(line)
            if m:
                duration_sec = int(m.group(1)) * 60
                pwr_low = int(m.group(2))
                pwr_high = int(m.group(3))
                seg_type = (
                    SegmentType.WARMUP
                    if pwr_low < pwr_high and not segments
                    else (SegmentType.COOLDOWN if pwr_low > pwr_high else SegmentType.RAMP)
                )
                segments.append(
                    ZwiftWorkoutSegment(
                        segment_type=seg_type,
                        duration_seconds=duration_sec,
                        power_low=pwr_low,
                        power_high=pwr_high,
                    )
                )
                continue

            # Free ride pattern
            m = freeride_re.search(line)
            if m:
                segments.append(
                    ZwiftWorkoutSegment(
                        segment_type=SegmentType.FREE_RIDE,
                        duration_seconds=int(m.group(1)) * 60,
                        power_low=None,
                    )
                )
                continue

            # Steady pattern (check after interval to avoid partial matches)
            m = steady_re.search(line)
            if m:
                dur = ZwiftWorkoutScraper._parse_duration_seconds(m.group(1))
                cadence = int(m.group(2)) if m.group(2) else None
                power = int(m.group(3))
                if dur:
                    if power <= 55:
                        seg_type = SegmentType.RECOVERY
                    elif power <= 105:
                        seg_type = SegmentType.STEADY
                    else:
                        seg_type = SegmentType.INTERVAL
                    segments.append(
                        ZwiftWorkoutSegment(
                            segment_type=seg_type,
                            duration_seconds=dur,
                            power_low=power,
                            cadence=cadence,
                        )
                    )
                continue

        return segments

    @staticmethod
    def _extract_work_segments(
        segments: list[ZwiftWorkoutSegment],
    ) -> list[ZwiftWorkoutSegment]:
        """Extract main-set work segments, excluding warmup/cooldown/recovery.

        Filters out:
        - First ascending ramp (warmup)
        - Last descending ramp (cooldown)
        - WARMUP, COOLDOWN, FREE_RIDE, RECOVERY segments
        """
        if not segments:
            return []

        filtered = list(segments)

        # Remove first segment if it's a warmup ramp (ascending power)
        if filtered and filtered[0].segment_type in (
            SegmentType.WARMUP,
            SegmentType.RAMP,
        ):
            if filtered[0].power_high and filtered[0].power_low:
                if filtered[0].power_high > filtered[0].power_low:
                    filtered = filtered[1:]

        # Remove last segment if it's a cooldown ramp (descending power)
        if filtered and filtered[-1].segment_type in (
            SegmentType.COOLDOWN,
            SegmentType.RAMP,
        ):
            if filtered[-1].power_high and filtered[-1].power_low:
                if filtered[-1].power_high < filtered[-1].power_low:
                    filtered = filtered[:-1]

        # Keep only work segments (exclude recovery and free ride)
        work = [
            s
            for s in filtered
            if s.segment_type
            not in (
                SegmentType.WARMUP,
                SegmentType.COOLDOWN,
                SegmentType.FREE_RIDE,
                SegmentType.RECOVERY,
            )
        ]

        # Filter out leading short opener/primer segments (< 2min)
        # Only remove consecutive short segments at the START of the work set
        if len(work) >= 4:
            first_long_idx = next(
                (i for i, s in enumerate(work) if s.duration_seconds >= 120),
                len(work),
            )
            if first_long_idx > 0 and len(work) - first_long_idx >= 3:
                work = work[first_long_idx:]
        return work

    @staticmethod
    def _find_repeating_block(
        powers: list[int],
        min_block_len: int = 3,
        min_repeats: int = 3,
    ) -> list[int] | None:
        """Find shortest repeating block in a power sequence.

        Args:
            powers: List of power values
            min_block_len: Minimum block length to consider
            min_repeats: Minimum number of consecutive repetitions

        Returns:
            The repeating block if found, None otherwise
        """
        n = len(powers)
        if n < min_block_len * min_repeats:
            return None

        for block_len in range(min_block_len, n // min_repeats + 1):
            block = powers[:block_len]
            repeats = 0
            for i in range(0, n, block_len):
                chunk = powers[i : i + block_len]
                if len(chunk) == block_len and chunk == block:
                    repeats += 1
                else:
                    break
            if repeats >= min_repeats:
                return block
        return None

    @staticmethod
    def detect_pattern(segments: list[ZwiftWorkoutSegment]) -> str:
        """Detect structural pattern from workout segments.

        Patterns:
        - over-under: alternating above/below threshold (~95-100% FTP)
        - pyramide: ascending then descending power in main set
        - progressif: ascending power through the workout
        - blocs-repetes: identical interval blocks repeated
        - libre: no clear pattern

        Args:
            segments: List of workout segments

        Returns:
            Pattern name string
        """
        if not segments:
            return "libre"

        # Extract all non-warmup/cooldown segments (including recovery)
        all_main = [
            s
            for s in segments
            if s.segment_type
            not in (SegmentType.WARMUP, SegmentType.COOLDOWN, SegmentType.FREE_RIDE)
        ]

        # Also strip leading/trailing ramps used as warmup/cooldown
        if all_main and all_main[0].segment_type == SegmentType.RAMP:
            if (
                all_main[0].power_high
                and all_main[0].power_low
                and all_main[0].power_high > all_main[0].power_low
            ):
                all_main = all_main[1:]
        if all_main and all_main[-1].segment_type == SegmentType.RAMP:
            if (
                all_main[-1].power_high
                and all_main[-1].power_low
                and all_main[-1].power_high < all_main[-1].power_low
            ):
                all_main = all_main[:-1]

        if len(all_main) < 2:
            return "libre"

        # Check for over-under FIRST (before blocs-repetes)
        # Pattern 1: repeated interval+recovery with over/under powers
        repeated = [s for s in all_main if s.repeat_count and s.repeat_count > 1]
        if len(repeated) >= 2:
            interval_segs = [s for s in repeated if s.segment_type == SegmentType.INTERVAL]
            recovery_segs = [
                s for s in repeated if s.segment_type in (SegmentType.RECOVERY, SegmentType.STEADY)
            ]
            if interval_segs and recovery_segs:
                hi = max(s.power_low for s in interval_segs if s.power_low)
                near_threshold = [
                    s.power_low for s in recovery_segs if s.power_low and s.power_low >= 80
                ]
                if hi >= 100 and near_threshold and 85 <= min(near_threshold) <= 97:
                    return "over-under"

        # Pattern 2: alternating steady segments above/below threshold
        work = ZwiftWorkoutScraper._extract_work_segments(segments)
        work_powers = [s.power_low for s in work if s.power_low]
        if len(work_powers) >= 4:
            has_over = any(p >= 100 for p in work_powers)
            has_under = any(85 <= p <= 97 for p in work_powers)
            if has_over and has_under:
                alternating = all(
                    (work_powers[i] >= 98) != (work_powers[i + 1] >= 98)
                    for i in range(len(work_powers) - 1)
                )
                if alternating:
                    return "over-under"

        # Pattern 3: repeating block with over-under within each repetition
        # Handles workouts listed as individual segments without repeat_count
        repeating_block = ZwiftWorkoutScraper._find_repeating_block(work_powers)
        if repeating_block:
            has_over = any(p >= 100 for p in repeating_block)
            has_under = any(85 <= p <= 97 for p in repeating_block)
            if has_over and has_under:
                return "over-under"

        # Check for blocs-repetes: repeat_count > 1 or repeating power block
        if repeated or repeating_block:
            return "blocs-repetes"

        # Use work segments (no recovery) for shape analysis
        if len(work_powers) >= 3:
            # Check for pyramid: ascending then descending power
            mid = len(work_powers) // 2
            ascending = all(work_powers[i] <= work_powers[i + 1] for i in range(mid))
            descending = all(
                work_powers[i] >= work_powers[i + 1] for i in range(mid, len(work_powers) - 1)
            )
            if ascending and descending and work_powers[0] < work_powers[mid]:
                return "pyramide"

            # Check for progressive: strictly ascending power
            strictly_ascending = all(
                work_powers[i] < work_powers[i + 1] for i in range(len(work_powers) - 1)
            )
            if strictly_ascending:
                return "progressif"

        return "libre"

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
