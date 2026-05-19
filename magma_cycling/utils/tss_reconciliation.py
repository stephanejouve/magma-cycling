"""TSS reconciliation between local planning and remote platform values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TssReconciliationResult:
    """Result of TSS reconciliation for a single session."""

    session_id: str
    local_tss: int
    remote_tss: int | None
    reconciled_tss: int
    delta: int  # remote - local (signed)
    action: str  # "updated" | "skipped" | "skipped_rest"
    reason: str


def reconcile_session_tss(
    session_id: str,
    local_tss: int,
    remote_tss: int | None,
    *,
    threshold_abs: int = 5,
    threshold_pct: float = 0.10,
    suspicious_ratio: float = 2.0,
) -> TssReconciliationResult:
    """Reconcile TSS for a single session.

    Remote-wins strategy with two thresholds:
    1. Below `max(threshold_abs, local * threshold_pct)` → skip (LLM rounding)
    2. Above `suspicious_ratio` factor (default 2x) → skipped_suspicious
       (likely remote parser bug, e.g. power range "67-72%" misinterpreted
       as borne haute multiplied — observed S094-04 with local=60 vs remote=212)
    3. Between the two → adopt remote (genuine Intervals correction)

    Args:
        session_id: Session identifier (e.g. "S087-01").
        local_tss: TSS from local planning (LLM header).
        remote_tss: TSS from remote platform (icu_training_load), None for rest days.
        threshold_abs: Absolute threshold in TSS (default 5).
        threshold_pct: Percentage threshold of local TSS (default 10%).
        suspicious_ratio: Ratio above which divergence is flagged as aberrant
            (default 2.0 → flags if remote ≥ 2× local OR remote ≤ 0.5× local).

    Returns:
        TssReconciliationResult with reconciled value and action taken.
    """
    if remote_tss is None or remote_tss == 0:
        return TssReconciliationResult(
            session_id=session_id,
            local_tss=local_tss,
            remote_tss=remote_tss,
            reconciled_tss=local_tss,
            delta=0,
            action="skipped_rest",
            reason="Remote TSS absent or zero (rest day)",
        )

    delta = remote_tss - local_tss
    threshold = max(threshold_abs, int(local_tss * threshold_pct))

    if abs(delta) <= threshold:
        return TssReconciliationResult(
            session_id=session_id,
            local_tss=local_tss,
            remote_tss=remote_tss,
            reconciled_tss=local_tss,
            delta=delta,
            action="skipped",
            reason=f"Delta {delta} within threshold {threshold}",
        )

    if local_tss > 0:
        ratio = remote_tss / local_tss
        if ratio >= suspicious_ratio or ratio <= (1.0 / suspicious_ratio):
            return TssReconciliationResult(
                session_id=session_id,
                local_tss=local_tss,
                remote_tss=remote_tss,
                reconciled_tss=local_tss,
                delta=delta,
                action="skipped_suspicious",
                reason=(
                    f"Suspicious divergence: remote/local ratio {ratio:.2f}x outside "
                    f"[{1.0 / suspicious_ratio:.2f}x, {suspicious_ratio:.2f}x] "
                    f"(likely remote parser bug, e.g. power range misinterpretation). "
                    f"Local TSS kept."
                ),
            )

    reconciled = max(0, min(500, remote_tss))
    return TssReconciliationResult(
        session_id=session_id,
        local_tss=local_tss,
        remote_tss=remote_tss,
        reconciled_tss=reconciled,
        delta=delta,
        action="updated",
        reason=f"Delta {delta} exceeds threshold {threshold}",
    )


def reconcile_week_tss(
    sessions: list[dict],
    **kwargs,
) -> dict:
    """Reconcile TSS for an entire week.

    Args:
        sessions: List of dicts with keys {session_id, local_tss, remote_tss}.
        **kwargs: Forwarded to reconcile_session_tss (threshold_abs, threshold_pct).

    Returns:
        Dict with keys: results, tss_local_total, tss_remote_total,
        tss_reconciled_total, sessions_updated, sessions_skipped.
    """
    results = []
    for s in sessions:
        result = reconcile_session_tss(
            session_id=s["session_id"],
            local_tss=s["local_tss"],
            remote_tss=s.get("remote_tss"),
            **kwargs,
        )
        results.append(result)

    tss_local_total = sum(r.local_tss for r in results)
    tss_remote_total = sum(r.remote_tss or 0 for r in results)
    tss_reconciled_total = sum(r.reconciled_tss for r in results)
    sessions_updated = sum(1 for r in results if r.action == "updated")
    sessions_skipped = sum(1 for r in results if r.action in ("skipped", "skipped_rest"))
    sessions_suspicious = sum(1 for r in results if r.action == "skipped_suspicious")

    return {
        "results": results,
        "tss_local_total": tss_local_total,
        "tss_remote_total": tss_remote_total,
        "tss_reconciled_total": tss_reconciled_total,
        "sessions_updated": sessions_updated,
        "sessions_skipped": sessions_skipped,
        "sessions_suspicious": sessions_suspicious,
    }
