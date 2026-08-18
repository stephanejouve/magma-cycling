"""Tests for planning models — version normalization."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from magma_cycling.planning.models import Session


class TestVersionNormalization:
    """Test version field_validator normalizes double-V prefix."""

    def _make_session(self, version: str) -> Session:
        return Session(
            session_id="S087-01",
            session_date=date(2026, 4, 6),
            name="EnduranceDouce",
            session_type="END",
            tss_planned=50,
            duration_min=60,
            version=version,
        )

    def test_version_normalization_VV001(self):
        """VV001 (double-V bug) is silently fixed to V001."""
        session = self._make_session("VV001")
        assert session.version == "V001"

    def test_version_valid_V001(self):
        """V001 remains V001 — no mutation."""
        session = self._make_session("V001")
        assert session.version == "V001"

    def test_version_V002_unchanged(self):
        """V002 remains V002."""
        session = self._make_session("V002")
        assert session.version == "V002"

    def test_version_invalid_rejected(self):
        """Invalid version pattern is rejected by pydantic."""
        with pytest.raises(ValidationError):
            self._make_session("X001")


class TestSessionTypeEnum:
    """Session.session_type accepts only the unified enum (15 types)."""

    ALL_VALID_TYPES = [
        "END",
        "INT",
        "REC",
        "RACE",
        "TEC",
        "SS",
        "FTP",
        "SPR",
        "CLM",
        "TT",
        "TMP",
        "MIX",
        "VO2",
        "KIN",
        "INJ",
    ]

    def _make_session(self, session_type: str) -> Session:
        # Off-bike sessions (KIN, INJ) must have tss_planned=0 (no training load)
        tss = 0 if session_type in ("KIN", "INJ") else 50
        return Session(
            session_id="S087-01",
            session_date=date(2026, 4, 6),
            name="TestSession",
            session_type=session_type,
            tss_planned=tss,
            duration_min=60,
        )

    @pytest.mark.parametrize("valid_type", ALL_VALID_TYPES)
    def test_all_valid_types_accepted(self, valid_type: str):
        """Each of the 14 unified enum types is accepted."""
        session = self._make_session(valid_type)
        assert session.session_type == valid_type

    @pytest.mark.parametrize("invalid_type", ["XYZ", "CAD", "ENDURO", "", "end"])
    def test_invalid_types_rejected(self, invalid_type: str):
        """Types outside the unified enum are rejected at Pydantic level.

        Regression : the TEC issue on S093-03 (2026-05-11) was caused by
        ``session_type: str`` being permissive. Now ``Literal[...]`` rejects
        anything not in the enum, providing the write-side guard rail
        requested in the bug report.
        """
        with pytest.raises(ValidationError):
            self._make_session(invalid_type)


class TestOffBikeTssConstraint:
    """Off-bike session_types (KIN, INJ) force tss_planned=0."""

    def _make_off_bike_session(self, session_type: str, tss: int) -> Session:
        return Session(
            session_id="S104-05",
            session_date=date(2026, 7, 30),
            name="OffBike",
            session_type=session_type,
            tss_planned=tss,
            duration_min=30,
        )

    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    def test_off_bike_with_zero_tss_accepted(self, off_bike_type: str):
        session = self._make_off_bike_session(off_bike_type, 0)
        assert session.session_type == off_bike_type
        assert session.tss_planned == 0

    @pytest.mark.parametrize("off_bike_type", ["KIN", "INJ"])
    @pytest.mark.parametrize("bad_tss", [1, 10, 50, 300])
    def test_off_bike_with_nonzero_tss_rejected(self, off_bike_type: str, bad_tss: int):
        with pytest.raises(
            ValidationError,
            match=f"{off_bike_type} session must have tss_planned=0",
        ):
            self._make_off_bike_session(off_bike_type, bad_tss)

    def test_non_off_bike_types_unaffected(self):
        """On-bike types keep their tss_planned freedom (regression guard)."""
        session = Session(
            session_id="S104-06",
            session_date=date(2026, 7, 31),
            name="Endurance",
            session_type="END",
            tss_planned=50,
            duration_min=60,
        )
        assert session.tss_planned == 50


class TestBT022BilateralAliases:
    """BT-022 : alias bilatéral sur les champs tss_* — préserve la
    capacité de renommage produit (marques déposées TSS/NP/IF appartenant
    désormais à Garmin/TrainingPeaks) sans casser les payloads MCP actuels.
    """

    def _base_kwargs(self):
        return dict(
            session_id="S087-01",
            session_date=date(2026, 4, 6),
            name="EnduranceDouce",
            session_type="END",
            duration_min=60,
        )

    def test_tss_planned_canonical_name_still_accepted(self):
        """Non-régression : le nom `tss_planned` continue de fonctionner."""
        session = Session(tss_planned=75, **self._base_kwargs())
        assert session.tss_planned == 75

    def test_tss_planned_alias_training_load_planned_accepted(self):
        """Le nom alias `training_load_planned` est aussi accepté."""
        from magma_cycling.planning.models import WeeklyPlan  # noqa

        session = Session(training_load_planned=75, **self._base_kwargs())
        assert session.tss_planned == 75

    def test_tss_planned_serialization_stays_on_canonical_name(self):
        """Sortie JSON reste `tss_planned` — pas de breaking change payload MCP."""
        session = Session(tss_planned=75, **self._base_kwargs())
        dumped = session.model_dump(by_alias=True)
        assert "tss_planned" in dumped
        assert dumped["tss_planned"] == 75
        assert "training_load_planned" not in dumped

    def test_tss_target_bilateral_alias(self):
        """WeeklyPlan.tss_target expose le même mécanisme d'alias.

        Utilise WeeklyPlan sans sessions (default_factory=list) pour
        éviter les artéfacts d'isolation Pydantic sur les instances
        Session partagées en suite.
        """
        from datetime import datetime

        from magma_cycling.planning.models import WeeklyPlan

        common = dict(
            week_id="S087",
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 12),
            created_at=datetime(2026, 4, 1, 12, 0),
            last_updated=datetime(2026, 4, 1, 12, 0),
            version=1,
            athlete_id="iXXXXXX",
        )

        # Accept ancien nom
        plan_canonical = WeeklyPlan(tss_target=350, **common)
        assert plan_canonical.tss_target == 350

        # Accept nouveau nom
        plan_alias = WeeklyPlan(training_load_target=350, **common)
        assert plan_alias.tss_target == 350

        # Serialization stable
        dumped = plan_alias.model_dump(by_alias=True)
        assert "tss_target" in dumped
        assert "training_load_target" not in dumped


class TestBT051TwoFieldsDesign:
    """BT-051 : ``tss_target_initial`` (write-once) + ``tss_target_current``
    (recompute chaque write) + ``finalized_at`` (timestamp handshake).

    Spec Coach AI 2026-08-17 : préserver l'intention historique
    (initial figé) tout en garantissant la fraîcheur d'une cible
    courante (current recompute).
    """

    def _base_plan(self, sessions=None, **overrides):
        from datetime import datetime

        from magma_cycling.planning.models import WeeklyPlan

        defaults = dict(
            week_id="S108",
            start_date=date(2026, 8, 24),
            end_date=date(2026, 8, 30),
            created_at=datetime(2026, 8, 24, 12, 0),
            last_updated=datetime(2026, 8, 24, 12, 0),
            version=1,
            athlete_id="iXXXXXX",
        )
        defaults.update(overrides)
        if sessions is not None:
            defaults["planned_sessions"] = sessions
        return WeeklyPlan(**defaults)

    def test_defaults_non_finalized(self):
        """Nouveau modèle : par défaut initial=None, current=None, finalized_at=None."""
        plan = self._base_plan()
        assert plan.tss_target_initial is None
        assert plan.tss_target_current is None
        assert plan.finalized_at is None

    def test_compute_current_tss_target_empty_returns_none(self):
        """Semaine vide → compute_current retourne None (signal distinct de 0)."""
        plan = self._base_plan()
        assert plan.compute_current_tss_target() is None

    def test_compute_current_tss_target_only_active(self):
        """compute_current somme uniquement les sessions non-cancelled."""
        from magma_cycling.planning.models import Session

        sessions = [
            Session(
                session_id="S108-01",
                date=date(2026, 8, 24),
                name="Endurance",
                type="END",
                version="V001",
                tss_planned=100,
                duration_min=60,
                description="test",
                status="completed",
            ),
            Session(
                session_id="S108-02",
                date=date(2026, 8, 25),
                name="Repos",
                type="END",
                version="V001",
                tss_planned=50,  # ignoré car rest_day
                duration_min=45,
                description="rest",
                status="rest_day",
            ),
            Session(
                session_id="S108-03",
                date=date(2026, 8, 26),
                name="Skip",
                type="END",
                version="V001",
                tss_planned=30,  # ignoré car skipped
                duration_min=45,
                description="skip",
                status="skipped",
                skip_reason="test fatigue",
            ),
            Session(
                session_id="S108-04",
                date=date(2026, 8, 27),
                name="Endurance2",
                type="END",
                version="V001",
                tss_planned=80,
                duration_min=60,
                description="test",
                status="planned",
            ),
        ]
        plan = self._base_plan(sessions=sessions)
        # Seules S108-01 (100) et S108-04 (80) contribuent = 180
        assert plan.compute_current_tss_target() == 180

    def test_to_json_recomputes_current(self, tmp_path: Path):
        """``to_json`` doit recompute ``tss_target_current`` avant écriture."""
        from magma_cycling.planning.models import Session, WeeklyPlan

        sessions = [
            Session(
                session_id="S108-01",
                date=date(2026, 8, 24),
                name="Endurance",
                type="END",
                version="V001",
                tss_planned=100,
                duration_min=60,
                description="test",
                status="completed",
            ),
        ]
        plan = self._base_plan(sessions=sessions)
        # Avant write : current pas encore calculé (default None)
        assert plan.tss_target_current is None
        # Écrire → recompute
        json_file = tmp_path / "week_planning_S108.json"
        plan.to_json(json_file)
        # Après write : current a été mis à 100
        assert plan.tss_target_current == 100
        # Vérif sur le disque
        reloaded = WeeklyPlan.from_json(json_file)
        assert reloaded.tss_target_current == 100
        # Initial pas touché
        assert reloaded.tss_target_initial is None
