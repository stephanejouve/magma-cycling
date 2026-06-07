"""Tests for priority_objective injection in load_periodization_context.

PR 1 of issue #401 — câblage de la lecture `priority_objective` au sein du
contexte de périodisation. Couvre le helper isolé `_load_priority_objective_dict`
(unitaire) puis la propagation dans le dict final retourné par
``PeriodizationMixin.load_periodization_context`` (intégration légère).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import yaml

from magma_cycling.workflows.planner import periodization as periodization_mod


@pytest.fixture
def athlete_yaml(tmp_path, monkeypatch):
    """Empty user athlete YAML pointed at by ATHLETE_CONFIG_PATH (no objective)."""
    yaml_path = tmp_path / "athlete.yaml"
    yaml_path.write_text("athlete: {}\n", encoding="utf-8")
    monkeypatch.setenv("ATHLETE_CONFIG_PATH", str(yaml_path))
    return yaml_path


def _write_objective(yaml_path, target_date: date, **extra):
    data = {
        "athlete": {
            "priority_objective": {
                "name": extra.get("name", "Test Fondo"),
                "type": extra.get("type", "granfondo"),
                "target_date": target_date.isoformat(),
                "priority": extra.get("priority", "A"),
                **{k: v for k, v in extra.items() if k in {"distance_km", "notes"}},
            }
        }
    }
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


class TestLoadPriorityObjectiveDict:
    """Helper `_load_priority_objective_dict` — covers all branches in isolation."""

    def test_returns_none_when_no_objective_set(self, athlete_yaml):
        assert periodization_mod._load_priority_objective_dict() is None

    def test_returns_dict_with_days_until_target_future(self, athlete_yaml):
        target = date.today() + timedelta(days=27)
        _write_objective(athlete_yaml, target, distance_km=81, notes="Build + taper")
        result = periodization_mod._load_priority_objective_dict()
        assert result is not None
        assert result["name"] == "Test Fondo"
        assert result["type"] == "granfondo"
        assert result["target_date"] == target.isoformat()
        assert result["priority"] == "A"
        assert result["distance_km"] == 81.0
        assert result["notes"] == "Build + taper"
        assert result["days_until_target"] == 27

    def test_days_until_target_zero_on_event_day(self, athlete_yaml):
        _write_objective(athlete_yaml, date.today())
        result = periodization_mod._load_priority_objective_dict()
        assert result["days_until_target"] == 0

    def test_days_until_target_negative_when_event_passed(self, athlete_yaml):
        target = date.today() - timedelta(days=3)
        _write_objective(athlete_yaml, target)
        result = periodization_mod._load_priority_objective_dict()
        assert result["days_until_target"] == -3

    def test_silent_none_when_loader_raises(self, monkeypatch, caplog):
        """If `load_priority_objective` raises, helper logs and returns None."""

        def boom(*_a, **_kw):
            raise RuntimeError("simulated YAML loader failure")

        monkeypatch.setattr(
            "magma_cycling.config.objectives.load_priority_objective",
            boom,
        )
        with caplog.at_level("WARNING", logger="magma_cycling.workflows.planner.periodization"):
            assert periodization_mod._load_priority_objective_dict() is None
        assert any("priority_objective loading failed" in r.message for r in caplog.records)


class TestPeriodizationContextInjection:
    """`load_periodization_context` integrates the helper into its returned dict."""

    @staticmethod
    def _build_planner_stub():
        """Create a minimal stub with the PeriodizationMixin behaviour we exercise."""
        stub = periodization_mod.PeriodizationMixin()
        stub.current_metrics = {"ctl": 65.0}
        return stub

    def test_context_carries_none_when_objective_absent(self, athlete_yaml, monkeypatch):
        """No objective in YAML → context.priority_objective is None."""
        stub = self._build_planner_stub()
        # Patch the heavy deps to focus on priority_objective injection.
        fake_profile = type("P", (), {"ftp": 250, "ftp_target": 270, "age": 40})()
        monkeypatch.setattr(
            "magma_cycling.config.athlete_profile.AthleteProfile.from_env",
            lambda: fake_profile,
        )
        fake_phase = type(
            "Phase",
            (),
            {
                "phase": type("Enum", (), {"value": "consolidation"})(),
                "ctl_target": 80.0,
                "ctl_deficit": 15.0,
                "weeks_to_rebuild": 6,
                "weekly_tss_load": 350,
                "weekly_tss_recovery": 250,
                "recovery_week_frequency": 4,
                "intensity_distribution": {"Endurance": 0.65},
                "rationale": "stub",
            },
        )()
        monkeypatch.setattr(
            "magma_cycling.planning.peaks_phases.determine_training_phase",
            lambda **_kw: fake_phase,
        )
        fake_integrated = type("I", (), {"override_active": False, "mode": None})()
        monkeypatch.setattr(
            "magma_cycling.workflows.pid_peaks_integration.compute_integrated_correction",
            lambda **_kw: fake_integrated,
        )
        context = stub.load_periodization_context()
        assert context is not None
        assert "priority_objective" in context
        assert context["priority_objective"] is None

    def test_context_carries_full_dict_when_objective_present(self, athlete_yaml, monkeypatch):
        """Objective in YAML → context.priority_objective contains payload + days_until_target."""
        target = date.today() + timedelta(days=10)
        _write_objective(athlete_yaml, target, distance_km=120, notes="Race week taper")
        stub = self._build_planner_stub()
        fake_profile = type("P", (), {"ftp": 250, "ftp_target": 270, "age": 40})()
        monkeypatch.setattr(
            "magma_cycling.config.athlete_profile.AthleteProfile.from_env",
            lambda: fake_profile,
        )
        fake_phase = type(
            "Phase",
            (),
            {
                "phase": type("Enum", (), {"value": "consolidation"})(),
                "ctl_target": 80.0,
                "ctl_deficit": 15.0,
                "weeks_to_rebuild": 6,
                "weekly_tss_load": 350,
                "weekly_tss_recovery": 250,
                "recovery_week_frequency": 4,
                "intensity_distribution": {"Endurance": 0.65},
                "rationale": "stub",
            },
        )()
        monkeypatch.setattr(
            "magma_cycling.planning.peaks_phases.determine_training_phase",
            lambda **_kw: fake_phase,
        )
        fake_integrated = type("I", (), {"override_active": False, "mode": None})()
        monkeypatch.setattr(
            "magma_cycling.workflows.pid_peaks_integration.compute_integrated_correction",
            lambda **_kw: fake_integrated,
        )
        context = stub.load_periodization_context()
        po = context["priority_objective"]
        assert po["name"] == "Test Fondo"
        assert po["target_date"] == target.isoformat()
        assert po["days_until_target"] == 10
        assert po["distance_km"] == 120.0
