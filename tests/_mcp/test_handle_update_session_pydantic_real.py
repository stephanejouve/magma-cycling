"""Tests for ``update-session`` handler — PYDANTIC REAL Session (no mock).

Background
----------
PR #309 v1 (mergée 2026-05-03 ~12h00) prétendait fixer le bug B2 (skip_reason
persistant après transition skipped → pending). Les tests régression de la PR
mockaient `Session = MagicMock()` et ne déclenchaient donc PAS le
``model_validator(mode="after")`` Pydantic qui impose
``status in (skipped, cancelled, replaced) ⇒ skip_reason not None``.

Le TNR preprod 2026-05-03 (~17h00) a détecté que PR #309 v1 introduisait en
réalité une **régression bloquante** : ``update-session`` plantait avec
``ValidationError`` pour TOUTE transition ``skipped → pending`` (clear de
skip_reason appliqué AVANT update du status, validator déclenché sur l'état
transitoire incohérent).

PR #318 v2 (ce hotfix) corrige l'ordre d'affectation selon la direction de
la transition. Ces tests utilisent une **VRAIE Session Pydantic** pour
exercer effectivement le validator — c'est ce qui aurait dû être fait dans
PR #309 v1.

Leçon retenue : les tests sur des objets sujets à validators Pydantic ne
doivent PAS utiliser MagicMock pour cette portion-là. Mock le repo I/O,
pas le model.
"""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from magma_cycling.planning.models import Session

pytest_plugins = ("pytest_asyncio",)

TOWER_PATCH = "magma_cycling.planning.control_tower.planning_tower"


def _make_real_session(
    status: str = "pending",
    skip_reason: str | None = None,
    session_id: str = "S091-03",
) -> Session:
    """Construit une vraie Session Pydantic avec le validator actif."""
    return Session(
        session_id=session_id,
        date=date(2026, 4, 29),
        name="CadenceTechnique",
        type="TEC",
        version="V001",
        tss_planned=40,
        duration_min=20,
        description="Technique Cadence",
        status=status,
        skip_reason=skip_reason,
        intervals_id=106564911,
    )


def _make_tower_with_session(session: Session) -> MagicMock:
    """Mock un planning_tower qui yield un plan contenant `session`."""
    plan = MagicMock()
    plan.planned_sessions = [session]
    tower = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=plan)
    ctx.__exit__ = Mock(return_value=False)
    tower.modify_week.return_value = ctx
    return tower


class TestRegressionPR309V1:
    """Régression bloquante détectée TNR preprod 2026-05-03."""

    @pytest.mark.asyncio
    async def test_skipped_to_pending_does_not_crash_with_real_session(self):
        """skipped(reason) → pending DOIT passer le validator Pydantic.

        C'est LE test qui aurait détecté la régression PR #309 v1.
        """
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(
            status="skipped", skip_reason="test-orphan-from-prod-midi"
        )
        tower = _make_tower_with_session(real_session)

        args = {"week_id": "S091", "session_id": "S091-03", "status": "pending"}
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        # Invariant B2 : pending ne doit JAMAIS porter skip_reason
        assert real_session.status == "pending"
        assert real_session.skip_reason is None, (
            f"skip_reason doit être cleared sur transition vers pending, "
            f"got {real_session.skip_reason!r}"
        )

    @pytest.mark.asyncio
    async def test_skipped_to_completed_does_not_crash_with_real_session(self):
        """Idem pour transition vers completed."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(status="skipped", skip_reason="Sick")
        tower = _make_tower_with_session(real_session)

        args = {"week_id": "S091", "session_id": "S091-03", "status": "completed"}
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "completed"
        assert real_session.skip_reason is None

    @pytest.mark.asyncio
    async def test_skipped_to_planned_does_not_crash_with_real_session(self):
        """Cas du TNR preprod : transition vers planned (état initial test synthétique)."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(
            status="skipped", skip_reason="test-tnr-preprod-2026-05-03"
        )
        tower = _make_tower_with_session(real_session)

        args = {"week_id": "S091", "session_id": "S091-03", "status": "planned"}
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "planned"
        assert real_session.skip_reason is None

    @pytest.mark.asyncio
    async def test_planned_to_skipped_with_reason_real_session(self):
        """Direction nominale : pending/planned → skipped avec reason."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(status="planned", skip_reason=None)
        tower = _make_tower_with_session(real_session)

        args = {
            "week_id": "S091",
            "session_id": "S091-03",
            "status": "skipped",
            "reason": "test-reason",
        }
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "skipped"
        assert real_session.skip_reason == "test-reason"

    @pytest.mark.asyncio
    async def test_skipped_with_reason_a_to_skipped_with_reason_b_real_session(self):
        """skipped(A) → skipped(B) : nouvelle reason écrase l'ancienne, validator OK."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(status="skipped", skip_reason="reason-A")
        tower = _make_tower_with_session(real_session)

        args = {
            "week_id": "S091",
            "session_id": "S091-03",
            "status": "skipped",
            "reason": "reason-B",
        }
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "skipped"
        assert real_session.skip_reason == "reason-B"

    @pytest.mark.asyncio
    async def test_skipped_with_reason_to_skipped_no_new_reason_preserves_real_session(
        self,
    ):
        """skipped(A) → skipped (sans nouvelle reason) : préserve l'ancienne."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(status="skipped", skip_reason="original")
        tower = _make_tower_with_session(real_session)

        args = {"week_id": "S091", "session_id": "S091-03", "status": "skipped"}
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "skipped"
        assert (
            real_session.skip_reason == "original"
        ), "skipped→skipped sans nouvelle reason doit préserver l'existante"

    @pytest.mark.asyncio
    async def test_pending_to_pending_no_change_real_session(self):
        """pending → pending (idempotent) : pas de side-effect."""
        from magma_cycling.mcp_server import handle_update_session

        real_session = _make_real_session(status="pending", skip_reason=None)
        tower = _make_tower_with_session(real_session)

        args = {"week_id": "S091", "session_id": "S091-03", "status": "pending"}
        with patch(TOWER_PATCH, tower):
            await handle_update_session(args)

        assert real_session.status == "pending"
        assert real_session.skip_reason is None
