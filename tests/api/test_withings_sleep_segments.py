"""Tests for Withings sleep segment aggregation."""

from magma_cycling.api.withings_client import WithingsClient


def _make_segment(
    date_str,
    start_dt,
    end_dt,
    hours,
    *,
    deep=None,
    light=None,
    rem=None,
    wakeup_count=0,
    wakeup_minutes=None,
    sleep_score=None,
    sleep_efficiency=None,
    hr_average=None,
    hr_min=None,
    hr_max=None,
    rr_average=None,
    rr_min=None,
    rr_max=None,
    sleep_latency_min=None,
    out_of_bed_count=None,
    breathing_disturbances=None,
):
    """Build a raw sleep segment dict as returned by get_sleep() before aggregation."""
    return {
        "date": date_str,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "total_sleep_hours": hours,
        "deep_sleep_minutes": deep,
        "light_sleep_minutes": light,
        "rem_sleep_minutes": rem,
        "wakeup_count": wakeup_count,
        "wakeup_minutes": wakeup_minutes,
        "sleep_score": sleep_score,
        "sleep_efficiency": sleep_efficiency,
        "hr_average": hr_average,
        "hr_min": hr_min,
        "hr_max": hr_max,
        "rr_average": rr_average,
        "rr_min": rr_min,
        "rr_max": rr_max,
        "sleep_latency_min": sleep_latency_min,
        "out_of_bed_count": out_of_bed_count,
        "breathing_disturbances": breathing_disturbances,
    }


class TestSingleSegment:
    def test_single_segment_has_count_1(self):
        seg = _make_segment("2026-03-07", "2026-03-06T22:30:00", "2026-03-07T06:30:00", 7.5)
        result = WithingsClient._aggregate_sleep_segments([seg])
        assert len(result) == 1
        assert result[0]["segments_count"] == 1
        assert result[0].get("segments_detail") is None


class TestMultiSegmentAggregation:
    def _two_segments(self):
        seg1 = _make_segment(
            "2026-03-07",
            "2026-03-06T22:08:00",
            "2026-03-07T01:30:00",
            3.2,
            deep=30.0,
            light=60.0,
            rem=20.0,
            wakeup_count=1,
            wakeup_minutes=5.0,
            sleep_score=78,
            sleep_efficiency=92,
            hr_average=55,
            hr_min=48,
            hr_max=68,
            rr_average=14.5,
            rr_min=12.0,
            rr_max=17.0,
            sleep_latency_min=8.5,
            out_of_bed_count=1,
        )
        seg2 = _make_segment(
            "2026-03-07",
            "2026-03-07T01:30:00",
            "2026-03-07T07:09:00",
            5.5,
            deep=45.0,
            light=90.0,
            rem=35.0,
            wakeup_count=2,
            wakeup_minutes=10.0,
            hr_average=52,
            hr_min=45,
            hr_max=62,
            rr_average=13.8,
            rr_min=11.5,
            rr_max=16.0,
            out_of_bed_count=0,
        )
        return [seg1, seg2]

    def test_multi_segment_same_date_aggregated(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert len(result) == 1
        assert result[0]["segments_count"] == 2

    def test_multi_segment_duration_sum(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert result[0]["total_sleep_hours"] == 8.7  # 3.2 + 5.5

    def test_multi_segment_stages_sum(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert result[0]["deep_sleep_minutes"] == 75.0  # 30 + 45
        assert result[0]["light_sleep_minutes"] == 150.0  # 60 + 90
        assert result[0]["rem_sleep_minutes"] == 55.0  # 20 + 35

    def test_multi_segment_wakeup_sum(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert result[0]["wakeup_count"] == 3  # 1 + 2
        assert result[0]["wakeup_minutes"] == 15.0  # 5 + 10

    def test_multi_segment_detail_format(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        detail = result[0]["segments_detail"]
        assert len(detail) == 2
        assert detail[0] == {"start": "22:08", "end": "01:30", "duration_hours": 3.2}
        assert detail[1] == {"start": "01:30", "end": "07:09", "duration_hours": 5.5}

    def test_multi_segment_hr_aggregation(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        merged = result[0]
        assert merged["hr_min"] == 45  # min(48, 45)
        assert merged["hr_max"] == 68  # max(68, 62)
        # Weighted avg: (55*3.2 + 52*5.5) / 8.7 ≈ 53.1 → 53
        assert merged["hr_average"] == 53

    def test_multi_segment_rr_aggregation(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        merged = result[0]
        assert merged["rr_min"] == 11.5
        assert merged["rr_max"] == 17.0
        # Weighted: (14.5*3.2 + 13.8*5.5) / 8.7 ≈ 14.06
        assert merged["rr_average"] == 14.1

    def test_multi_segment_scores_first_non_none(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        merged = result[0]
        assert merged["sleep_score"] == 78
        assert merged["sleep_efficiency"] == 92

    def test_multi_segment_sleep_latency_from_first(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert result[0]["sleep_latency_min"] == 8.5

    def test_multi_segment_start_end_range(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        merged = result[0]
        assert merged["start_datetime"] == "2026-03-06T22:08:00"
        assert merged["end_datetime"] == "2026-03-07T07:09:00"

    def test_multi_segment_out_of_bed_sum(self):
        result = WithingsClient._aggregate_sleep_segments(self._two_segments())
        assert result[0]["out_of_bed_count"] == 1  # 1 + 0 (0 is falsy, skipped)


class TestDifferentDates:
    def test_different_dates_not_merged(self):
        seg1 = _make_segment("2026-03-06", "2026-03-05T23:00:00", "2026-03-06T06:00:00", 7.0)
        seg2 = _make_segment("2026-03-07", "2026-03-06T23:00:00", "2026-03-07T06:30:00", 7.5)
        result = WithingsClient._aggregate_sleep_segments([seg1, seg2])
        assert len(result) == 2
        assert result[0]["segments_count"] == 1
        assert result[1]["segments_count"] == 1
