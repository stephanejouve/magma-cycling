"""Tests for cardiovascular decoupling calculation utilities."""

import pytest

from magma_cycling.utils.decoupling import analyze_overtime, calculate_decoupling


class TestCalculateDecoupling:
    """Tests for calculate_decoupling function."""

    def test_flat_streams_near_zero(self):
        """Constant power and HR → decoupling ~0%."""
        # 600 seconds of constant data
        watts = [200.0] * 600
        hr = [140.0] * 600

        result = calculate_decoupling(watts, hr)

        assert result is not None
        assert result == pytest.approx(0.0, abs=0.1)

    def test_hr_drift_negative_decoupling(self):
        """HR drifting up with constant power → negative decoupling (NP/HR ratio drops)."""
        n = 600
        watts = [200.0] * n
        # HR starts at 130 and drifts to 150 over the session
        hr = [130.0 + (20.0 * i / n) for i in range(n)]

        result = calculate_decoupling(watts, hr)

        assert result is not None
        # With constant power and rising HR:
        # ratio1 = NP/avg_hr_half1 (lower HR → higher ratio)
        # ratio2 = NP/avg_hr_half2 (higher HR → lower ratio)
        # result = (ratio2 - ratio1)/ratio1 → negative
        assert result < 0

    def test_power_drop_positive_decoupling(self):
        """Power dropping with constant HR → negative decoupling (fatigue)."""
        n = 600
        # Power drops from 220 to 180
        watts = [220.0 - (40.0 * i / n) for i in range(n)]
        hr = [140.0] * n

        result = calculate_decoupling(watts, hr)

        assert result is not None
        assert result < 0  # NP drops → ratio drops → negative

    def test_with_max_seconds_truncates(self):
        """max_seconds truncates streams before calculation."""
        # 1200 seconds total, but prescribed is 600
        watts = [200.0] * 600 + [100.0] * 600  # Power drops to 100W after 600s
        hr = [140.0] * 600 + [160.0] * 600  # HR jumps after 600s

        # Full calculation includes the bad second half
        full_result = calculate_decoupling(watts, hr)
        # Windowed to first 600s (constant data)
        windowed_result = calculate_decoupling(watts, hr, max_seconds=600)

        assert full_result is not None
        assert windowed_result is not None
        # Windowed should be closer to 0 (constant data in prescribed window)
        assert abs(windowed_result) < abs(full_result)

    def test_none_when_insufficient_data(self):
        """Less than 60 data points → None."""
        watts = [200.0] * 50
        hr = [140.0] * 50

        result = calculate_decoupling(watts, hr)

        assert result is None

    def test_none_when_no_hr(self):
        """All HR values are zero → None."""
        watts = [200.0] * 200
        hr = [0.0] * 200

        result = calculate_decoupling(watts, hr)

        assert result is None

    def test_none_when_empty_lists(self):
        """Empty input lists → None."""
        assert calculate_decoupling([], []) is None
        assert calculate_decoupling([200.0] * 100, []) is None
        assert calculate_decoupling([], [140.0] * 100) is None

    def test_none_when_insufficient_power_for_np(self):
        """Less than 30 points per half → NP can't be computed → None."""
        # 60 points total → 30 per half, NP needs 30 for rolling window
        # With 30 points, we get 1 rolling avg → NP works
        # But with fewer, it fails
        watts = [200.0] * 58  # 29 per half → can't compute NP
        hr = [140.0] * 58

        # 58 points → 29 per half → NP rolling window needs 30 → fails
        # Actually 60 is the minimum, 58 < 60 so it returns None from length check
        result = calculate_decoupling(watts, hr)
        assert result is None

    def test_different_length_streams_aligned(self):
        """Streams of different lengths are aligned to shortest."""
        watts = [200.0] * 800
        hr = [140.0] * 600

        result = calculate_decoupling(watts, hr)

        assert result is not None
        assert result == pytest.approx(0.0, abs=0.1)

    def test_max_seconds_zero_no_truncation(self):
        """max_seconds=0 is ignored (not a valid window), full data used."""
        watts = [200.0] * 600
        hr = [140.0] * 600

        result = calculate_decoupling(watts, hr, max_seconds=0)

        # 0 is not > 0, so no truncation, uses full constant data → ~0%
        assert result is not None
        assert result == pytest.approx(0.0, abs=0.1)


class TestAnalyzeOvertime:
    """Tests for analyze_overtime function."""

    def test_returns_metrics_for_extension(self):
        """Extension with data returns overtime metrics dict."""
        prescribed = 600
        total = 900  # 5 min extension
        watts = [200.0] * prescribed + [100.0] * (total - prescribed)
        hr = [140.0] * prescribed + [120.0] * (total - prescribed)

        result = analyze_overtime(watts, hr, prescribed)

        assert result is not None
        assert result["duration_extra_min"] == pytest.approx(5.0, abs=0.1)
        assert result["avg_power_watts"] == pytest.approx(100.0, abs=1.0)
        assert result["avg_hr_bpm"] == pytest.approx(120.0, abs=1.0)
        assert "estimated_tss" in result

    def test_none_when_no_extension(self):
        """Recording shorter than prescribed → None."""
        watts = [200.0] * 500
        hr = [140.0] * 500

        result = analyze_overtime(watts, hr, prescribed_seconds=600)

        assert result is None

    def test_none_when_extension_under_30s(self):
        """Extension under 30 seconds → None (not significant)."""
        prescribed = 600
        watts = [200.0] * (prescribed + 20)
        hr = [140.0] * (prescribed + 20)

        result = analyze_overtime(watts, hr, prescribed)

        assert result is None

    def test_none_when_exactly_prescribed(self):
        """Recording exactly prescribed duration → None."""
        prescribed = 600
        watts = [200.0] * prescribed
        hr = [140.0] * prescribed

        result = analyze_overtime(watts, hr, prescribed)

        assert result is None

    def test_none_when_empty_data(self):
        """Empty input → None."""
        assert analyze_overtime([], [], 600) is None

    def test_extension_with_zero_power(self):
        """Extension with all zero power still returns metrics."""
        prescribed = 600
        watts = [200.0] * prescribed + [0.0] * 120
        hr = [140.0] * prescribed + [110.0] * 120

        result = analyze_overtime(watts, hr, prescribed)

        assert result is not None
        assert result["avg_power_watts"] == 0.0
        assert result["avg_hr_bpm"] == pytest.approx(110.0, abs=1.0)

    def test_estimated_tss_reasonable(self):
        """TSS estimate is in a reasonable range for the extension."""
        prescribed = 3600  # 1h
        extra = 900  # 15min extension at ~200W
        watts = [200.0] * prescribed + [200.0] * extra
        hr = [140.0] * prescribed + [145.0] * extra

        result = analyze_overtime(watts, hr, prescribed)

        assert result is not None
        assert result["estimated_tss"] > 0
        # 15min at 200W (IF~1.0 with FTP=200) → TSS ~ 25
        assert result["estimated_tss"] == pytest.approx(25.0, abs=5.0)

    def test_different_length_streams(self):
        """Streams of different lengths use the shorter one."""
        prescribed = 600
        watts = [200.0] * 800
        hr = [140.0] * 700  # Shorter

        result = analyze_overtime(watts, hr, prescribed)

        assert result is not None
        assert result["duration_extra_min"] == pytest.approx((700 - 600) / 60, abs=0.1)
