"""Cardiovascular decoupling calculation with windowing support.

Extracts the NP/HR decoupling logic into reusable functions that support:
- Windowed calculation (prescribed duration vs full recording)
- Overtime analysis (extension beyond prescribed duration)

Limitation connue (v1):
    Le fenêtrage utilise une troncature temporelle simple (0 → prescribed_seconds).
    Cela ne couvre pas le cas d'un warmup allongé en début de séance (ex: 25min de
    warmup au lieu de 10min prescrits pour finir sur la ligne d'arrivée Zwift). Dans
    ce cas, la fenêtre 0→prescribed_seconds capture le warmup étendu et tronque le
    cooldown, produisant un découplage tout aussi invalide que l'overtime post-séance.

    TODO(v2): Utiliser les bornes start_index/end_index des intervalles prescrits
    détectés (via apply-workout-intervals en dry_run) comme fenêtre de calcul, plutôt
    qu'une troncature temporelle simple. Couvrirait warmup allongé ET overtime.

References:
    - Friel (2009) — Pw:Hr decoupling: <5% aerobic fitness validated
    - Coggan — Normalized Power (30s rolling average, 4th power)
"""

from __future__ import annotations


def _calc_np(watts: list[float]) -> float | None:
    """Compute Normalized Power from a watts stream.

    Uses 30-second rolling average raised to the 4th power.

    Args:
        watts: Per-second power data.

    Returns:
        Normalized power value, or None if insufficient data (<30 points).
    """
    if len(watts) < 30:
        return None
    rolling_avgs = []
    for i in range(len(watts) - 29):
        window = watts[i : i + 30]
        rolling_avgs.append(sum(window) / 30)
    if not rolling_avgs:
        return None
    fourth_powers = [p**4 for p in rolling_avgs]
    avg_fourth = sum(fourth_powers) / len(fourth_powers)
    return avg_fourth ** (1 / 4)


def calculate_decoupling(
    watts_data: list[float],
    hr_data: list[float],
    max_seconds: int | None = None,
) -> float | None:
    """Calculate NP/HR cardiovascular decoupling over a window.

    Splits the data into two halves and compares the NP:HR ratio
    between the first and second half.

    Args:
        watts_data: Per-second power data.
        hr_data: Per-second heart rate data.
        max_seconds: If provided, truncate streams to this length before
            calculation (for prescribed-duration windowing).

    Returns:
        Decoupling percentage (positive = cardiac drift), or None if
        insufficient data (< 60 points or no valid HR).
    """
    if not watts_data or not hr_data:
        return None

    # Truncate to max_seconds if specified
    if max_seconds is not None and max_seconds > 0:
        watts_data = watts_data[:max_seconds]
        hr_data = hr_data[:max_seconds]

    # Align lengths
    min_len = min(len(watts_data), len(hr_data))
    if min_len < 60:
        return None

    watts_data = watts_data[:min_len]
    hr_data = hr_data[:min_len]

    midpoint = min_len // 2

    # Split into halves
    watts_half1 = watts_data[:midpoint]
    hr_half1 = hr_data[:midpoint]
    watts_half2 = watts_data[midpoint:]
    hr_half2 = hr_data[midpoint:]

    # Calculate NP for each half
    np_half1 = _calc_np(watts_half1)
    np_half2 = _calc_np(watts_half2)

    if not np_half1 or not np_half2:
        return None

    # Average HR (excluding zeros)
    hr_half1_valid = [hr for hr in hr_half1 if hr > 0]
    hr_half2_valid = [hr for hr in hr_half2 if hr > 0]

    if not hr_half1_valid or not hr_half2_valid:
        return None

    avg_hr_half1 = sum(hr_half1_valid) / len(hr_half1_valid)
    avg_hr_half2 = sum(hr_half2_valid) / len(hr_half2_valid)

    if avg_hr_half1 <= 0:
        return None

    # Decoupling = (ratio_half2 - ratio_half1) / ratio_half1 * 100
    ratio_half1 = np_half1 / avg_hr_half1
    ratio_half2 = np_half2 / avg_hr_half2

    return round(((ratio_half2 - ratio_half1) / ratio_half1) * 100, 1)


def analyze_overtime(
    watts_data: list[float],
    hr_data: list[float],
    prescribed_seconds: int,
) -> dict | None:
    """Analyze the extension beyond prescribed duration.

    Args:
        watts_data: Full per-second power data.
        hr_data: Full per-second heart rate data.
        prescribed_seconds: Prescribed session duration in seconds.

    Returns:
        Dict with overtime metrics, or None if no significant extension (<30s):
        - duration_extra_min: Extension duration in minutes (rounded to 1 decimal)
        - avg_power_watts: Average power during extension (non-zero only)
        - avg_hr_bpm: Average heart rate during extension (non-zero only)
        - estimated_tss: Rough TSS estimate for the extension (NP-based, FTP=200W default)
    """
    if not watts_data or not hr_data:
        return None

    min_len = min(len(watts_data), len(hr_data))
    if min_len <= prescribed_seconds:
        return None

    extra_seconds = min_len - prescribed_seconds
    if extra_seconds < 30:
        return None

    # Extract overtime portion
    watts_extra = watts_data[prescribed_seconds:min_len]
    hr_extra = hr_data[prescribed_seconds:min_len]

    # Average power (non-zero)
    non_zero_watts = [w for w in watts_extra if w > 0]
    avg_power = round(sum(non_zero_watts) / len(non_zero_watts), 1) if non_zero_watts else 0.0

    # Average HR (non-zero)
    non_zero_hr = [hr for hr in hr_extra if hr > 0]
    avg_hr = round(sum(non_zero_hr) / len(non_zero_hr), 1) if non_zero_hr else 0.0

    # Rough TSS estimate: (duration_h * NP^2) / (FTP^2 * 3600) * 100
    # Using a simplified approach: TSS ~ (seconds * IF^2) / 36
    # With IF ~ NP/FTP, and we approximate FTP = 200W for the estimate
    np_extra = _calc_np(watts_extra)
    estimated_tss = 0.0
    if np_extra and np_extra > 0:
        ftp_estimate = 200  # Conservative estimate for TSS calculation
        intensity_factor = np_extra / ftp_estimate
        estimated_tss = round((extra_seconds * intensity_factor**2) / 36, 1)

    return {
        "duration_extra_min": round(extra_seconds / 60, 1),
        "avg_power_watts": avg_power,
        "avg_hr_bpm": avg_hr,
        "estimated_tss": estimated_tss,
    }
