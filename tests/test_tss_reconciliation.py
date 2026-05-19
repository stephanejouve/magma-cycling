"""Tests for TSS reconciliation between local and remote values."""

from magma_cycling.utils.tss_reconciliation import (
    TssReconciliationResult,
    reconcile_session_tss,
    reconcile_week_tss,
)


class TestReconcileSessionTss:
    """Unit tests for reconcile_session_tss."""

    def test_remote_wins_above_threshold(self):
        """Remote TSS adopted when delta exceeds threshold."""
        r = reconcile_session_tss("S087-01", local_tss=72, remote_tss=85)
        assert r.reconciled_tss == 85
        assert r.action == "updated"
        assert r.delta == 13
        assert r.local_tss == 72
        assert r.remote_tss == 85

    def test_within_abs_threshold_skipped(self):
        """Delta within absolute threshold (5 TSS) is skipped."""
        r = reconcile_session_tss("S087-02", local_tss=72, remote_tss=74)
        assert r.reconciled_tss == 72  # local kept
        assert r.action == "skipped"
        assert r.delta == 2

    def test_within_pct_threshold_skipped(self):
        """Delta within percentage threshold (10%) is skipped."""
        # local=100, remote=108, delta=8 < threshold=max(5, 10)=10
        r = reconcile_session_tss("S087-03", local_tss=100, remote_tss=108)
        assert r.reconciled_tss == 100
        assert r.action == "skipped"
        assert r.delta == 8

    def test_remote_none_skipped_rest(self):
        """Remote None treated as rest day."""
        r = reconcile_session_tss("S087-04", local_tss=0, remote_tss=None)
        assert r.action == "skipped_rest"
        assert r.reconciled_tss == 0
        assert r.delta == 0

    def test_remote_zero_skipped_rest(self):
        """Remote 0 treated as rest day."""
        r = reconcile_session_tss("S087-05", local_tss=0, remote_tss=0)
        assert r.action == "skipped_rest"
        assert r.reconciled_tss == 0

    def test_negative_delta(self):
        """Remote lower than local — still adopted if above threshold."""
        r = reconcile_session_tss("S087-06", local_tss=85, remote_tss=72)
        assert r.reconciled_tss == 72
        assert r.action == "updated"
        assert r.delta == -13

    def test_clamp_upper_bound(self):
        """Remote TSS above 500 is clamped."""
        r = reconcile_session_tss("S087-07", local_tss=400, remote_tss=600)
        assert r.reconciled_tss == 500
        assert r.action == "updated"

    def test_result_is_frozen_dataclass(self):
        """Result is immutable."""
        r = reconcile_session_tss("S087-01", local_tss=72, remote_tss=85)
        assert isinstance(r, TssReconciliationResult)

    def test_custom_thresholds(self):
        """Custom thresholds override defaults."""
        # With default: delta=8, threshold=max(5,7.2)=7 → updated
        r_default = reconcile_session_tss("S087-08", local_tss=72, remote_tss=80)
        assert r_default.action == "updated"

        # With higher threshold: delta=8, threshold=max(10,7.2)=10 → skipped
        r_custom = reconcile_session_tss("S087-08", local_tss=72, remote_tss=80, threshold_abs=10)
        assert r_custom.action == "skipped"


class TestReconcileWeekTss:
    """Unit tests for reconcile_week_tss."""

    def test_week_totals(self):
        """Verify weekly totals with mixed sessions including rest days."""
        sessions = [
            {"session_id": "S087-01", "local_tss": 72, "remote_tss": 85},  # updated
            {"session_id": "S087-02", "local_tss": 0, "remote_tss": None},  # rest
            {"session_id": "S087-03", "local_tss": 45, "remote_tss": 43},  # skipped (delta=2)
            {"session_id": "S087-04", "local_tss": 0, "remote_tss": 0},  # rest
            {"session_id": "S087-05", "local_tss": 100, "remote_tss": 120},  # updated
        ]
        result = reconcile_week_tss(sessions)

        assert result["tss_local_total"] == 217  # 72+0+45+0+100
        assert result["tss_remote_total"] == 248  # 85+0+43+0+120
        # reconciled: 85+0+45+0+120 = 250
        assert result["tss_reconciled_total"] == 250
        assert result["sessions_updated"] == 2
        assert result["sessions_skipped"] == 3  # 1 skipped + 2 rest

    def test_mixed_skip_and_update(self):
        """Verify counters for mixed skip/update."""
        sessions = [
            {"session_id": "S087-01", "local_tss": 72, "remote_tss": 85},  # updated (+13)
            {"session_id": "S087-02", "local_tss": 50, "remote_tss": 52},  # skipped (delta=2)
            {"session_id": "S087-03", "local_tss": 80, "remote_tss": 65},  # updated (-15)
        ]
        result = reconcile_week_tss(sessions)

        assert result["sessions_updated"] == 2
        assert result["sessions_skipped"] == 1
        assert len(result["results"]) == 3

    def test_empty_sessions(self):
        """Empty session list returns zero totals."""
        result = reconcile_week_tss([])
        assert result["tss_local_total"] == 0
        assert result["tss_reconciled_total"] == 0
        assert result["sessions_updated"] == 0
        assert result["sessions_skipped"] == 0
        assert result["results"] == []

    def test_all_rest_days(self):
        """All rest days produce zero updates."""
        sessions = [
            {"session_id": "S087-01", "local_tss": 0, "remote_tss": None},
            {"session_id": "S087-02", "local_tss": 0, "remote_tss": 0},
        ]
        result = reconcile_week_tss(sessions)
        assert result["sessions_updated"] == 0
        assert result["sessions_skipped"] == 2


class TestSuspiciousDivergence:
    """Tests for the suspicious divergence guard (Section N regression)."""

    def test_s094_04_regression_remote_3x_higher_skipped_suspicious(self):
        """S094-04 régression : local=60, remote=212 (3.53x) → skipped_suspicious, local kept."""
        r = reconcile_session_tss("S094-04", local_tss=60, remote_tss=212)
        assert r.action == "skipped_suspicious"
        assert r.reconciled_tss == 60
        assert r.delta == 152
        assert "Suspicious divergence" in r.reason
        assert "3.53x" in r.reason

    def test_s094_06_regression_modest_divergence_still_updated(self):
        """S094-06 régression : local=75, remote=92 (1.23x) → updated (under suspicious threshold)."""
        r = reconcile_session_tss("S094-06", local_tss=75, remote_tss=92)
        assert r.action == "updated"
        assert r.reconciled_tss == 92

    def test_remote_half_local_skipped_suspicious(self):
        """Symmetric guard: remote ≤ 0.5 × local → also flagged suspicious."""
        r = reconcile_session_tss("S094-XX", local_tss=100, remote_tss=40)
        assert r.action == "skipped_suspicious"
        assert r.reconciled_tss == 100

    def test_exactly_2x_threshold_is_suspicious(self):
        """Ratio exactly at 2.0x is flagged (boundary inclusive)."""
        r = reconcile_session_tss("S094-XX", local_tss=50, remote_tss=100)
        assert r.action == "skipped_suspicious"

    def test_just_below_2x_threshold_is_updated(self):
        """Ratio 1.95x is genuine correction (under suspicious threshold)."""
        r = reconcile_session_tss("S094-XX", local_tss=100, remote_tss=195)
        assert r.action == "updated"

    def test_custom_suspicious_ratio_more_lenient(self):
        """Custom suspicious_ratio=3.0 lets 2.5x through."""
        r = reconcile_session_tss("S094-XX", local_tss=60, remote_tss=150, suspicious_ratio=3.0)
        assert r.action == "updated"
        assert r.reconciled_tss == 150

    def test_custom_suspicious_ratio_more_strict(self):
        """Custom suspicious_ratio=1.5 catches 1.6x as suspicious."""
        r = reconcile_session_tss("S094-XX", local_tss=100, remote_tss=160, suspicious_ratio=1.5)
        assert r.action == "skipped_suspicious"

    def test_week_summary_includes_sessions_suspicious(self):
        """Weekly summary surfaces sessions_suspicious counter."""
        sessions = [
            {"session_id": "S094-01", "local_tss": 60, "remote_tss": 212},
            {"session_id": "S094-02", "local_tss": 75, "remote_tss": 92},
            {"session_id": "S094-03", "local_tss": 72, "remote_tss": 74},
        ]
        result = reconcile_week_tss(sessions)
        assert result["sessions_suspicious"] == 1
        assert result["sessions_updated"] == 1
        assert result["sessions_skipped"] == 1
        assert result["tss_reconciled_total"] == 60 + 92 + 72
