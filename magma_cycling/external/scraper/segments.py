"""Parsing de segments workout (textbar CSS + texte) + constantes."""

import logging
import re

from bs4 import BeautifulSoup

from magma_cycling.external.zwift_models import SegmentType, ZwiftWorkoutSegment

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


def parse_segments_from_soup(soup: BeautifulSoup) -> list[ZwiftWorkoutSegment]:
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


def parse_duration_seconds(duration_str: str) -> int | None:
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


def parse_segments_from_text(text: str) -> list[ZwiftWorkoutSegment]:
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
            dur1 = parse_duration_seconds(m.group(2))
            cad1 = int(m.group(3)) if m.group(3) else None
            pwr1 = int(m.group(4))
            dur2 = parse_duration_seconds(m.group(5))
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
            dur = parse_duration_seconds(m.group(1))
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
