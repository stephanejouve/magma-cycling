"""Tests BT-027 / ADR v5 §7 — détection layout legacy training-logs.

Couvre :
- ``detect_legacy_layout`` — retourne True si ``.operators.yaml`` absent
  ET fichiers/dossiers présents en racine hors whitelist ; False sinon.
- ``raise_if_legacy_layout`` — lève ``LegacyLayoutError`` avec message
  actionnable si legacy détecté, no-op sinon.
- Intégration ``DataRepoConfig`` — writer-scoped + repo legacy →
  ``LegacyLayoutError`` early, avant même le check WRITER_ID.
- Non-régression : le mode legacy (writer_scoped=False, défaut) continue
  de fonctionner sur un repo flat sans lever.
"""

from __future__ import annotations

import pytest

from magma_cycling.config.data_repo import (
    DataRepoConfig,
    LegacyLayoutError,
    detect_legacy_layout,
    raise_if_legacy_layout,
)


@pytest.fixture
def empty_repo(tmp_path):
    """Repo vierge — juste `.git/`, aucun fichier."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def clean_whitelist_repo(tmp_path):
    """Repo racine 100% whitelist — pas de layout à migrer."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    (tmp_path / "README.md").write_text("# training-logs\n")
    return tmp_path


@pytest.fixture
def legacy_flat_repo(tmp_path):
    """Repo layout flat legacy — fichiers en racine hors whitelist,
    pas de ``.operators.yaml``. Cas typique d'un beta-tester qui a un
    clone historique."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    (tmp_path / "activities_tracking.json").write_text("{}")
    (tmp_path / "workouts-history.md").write_text("# history\n")
    weekly = tmp_path / "weekly-reports"
    weekly.mkdir()
    (weekly / "S099.md").write_text("weekly report S099\n")
    return tmp_path


@pytest.fixture
def migrated_repo(tmp_path):
    """Repo déjà migré — ``.operators.yaml`` présent + subdir writer hash."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    (tmp_path / ".operators.yaml").write_text(
        "shared_root_files:\n  - .gitignore\n"
        "  - README.md\n"
        "  - .operators.yaml\nwriters:\n"
        "  abc123def456:\n    alias: mac\n    host: tiresias\n"
        "    provisioned_at: 2026-08-13T21:00:00Z\n"
        "    decommissioned_at: null\n"
    )
    (tmp_path / "abc123def456").mkdir()
    (tmp_path / "abc123def456" / "activities_tracking.json").write_text("{}")
    return tmp_path


@pytest.fixture
def hybrid_repo(tmp_path):
    """Repo hybride BT-030 : ``.operators.yaml`` présent + writer subdir
    provisionné + du contenu flat racine encore à absorber.

    Cas réel constaté sur prod NAS (2026-08-15) : Phase 1A de mai avait
    provisionné le writer ``88bc132e32a0`` avec quelques weekly-reports
    dedans, mais 99 % des écritures runtime (data/, weekly-reports S095+,
    monthly-reports, etc.) sont restées en racine parce que la migration
    complète n'avait jamais été bouclée. Le script BT-027 doit accepter
    ce cas et migrer le flat racine vers un nouveau (ou même) writer.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    (tmp_path / ".operators.yaml").write_text(
        "shared_root_files:\n  - .gitignore\n  - README.md\n"
        "  - .operators.yaml\nwriters:\n"
        "  88bc132e32a0:\n    alias: nas-prod\n    host: nas\n"
        "    provisioned_at: 2026-05-03T09:44:00Z\n"
        "    decommissioned_at: null\n"
    )
    # Writer déjà provisionné (Phase 1A) — partiellement rempli
    (tmp_path / "88bc132e32a0").mkdir()
    (tmp_path / "88bc132e32a0" / "workouts-history.md").write_text("legacy\n")
    # Contenu flat racine encore à absorber (écritures runtime post-Phase 1A).
    # NB : ``data/`` est whitelisté au toplevel donc pas listé ici.
    (tmp_path / "activities_tracking.json").write_text('{"live": true}')
    (tmp_path / "backups").mkdir()
    (tmp_path / "backups" / "S105-backup.md").write_text("backup\n")
    weekly = tmp_path / "weekly-reports"
    weekly.mkdir()
    (weekly / "S105.md").write_text("weekly S105\n")
    return tmp_path


class TestDetectLegacyLayout:
    def test_legacy_flat_repo_detected(self, legacy_flat_repo):
        assert detect_legacy_layout(legacy_flat_repo) is True

    def test_clean_whitelist_repo_not_legacy(self, clean_whitelist_repo):
        """Racine 100% whitelist → pas de migration nécessaire."""
        assert detect_legacy_layout(clean_whitelist_repo) is False

    def test_empty_repo_not_legacy(self, empty_repo):
        """Repo vierge (juste .git) → rien à migrer."""
        assert detect_legacy_layout(empty_repo) is False

    def test_migrated_repo_not_legacy(self, migrated_repo):
        """``.operators.yaml`` présent = layout déjà migré."""
        assert detect_legacy_layout(migrated_repo) is False

    def test_nonexistent_path_returns_false(self, tmp_path):
        """Path inexistant → False (pas de crash, pas de faux positif)."""
        assert detect_legacy_layout(tmp_path / "does-not-exist") is False

    def test_writer_hash_subdir_not_counted_as_legacy(self, tmp_path):
        """Un repo avec un writer subdir mais sans ``.operators.yaml``
        (état incohérent, mais on ne le considère pas legacy — le hash
        subdir suggère qu'une migration a commencé)."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "abc123def456").mkdir()
        (tmp_path / "abc123def456" / "data.json").write_text("{}")
        # Pas de .operators.yaml, mais aussi rien en racine hors whitelist
        # ni hors le writer hash → pas legacy.
        assert detect_legacy_layout(tmp_path) is False

    def test_hybrid_repo_detected_bt030(self, hybrid_repo):
        """BT-030 : repo hybride (``.operators.yaml`` + writer subdir +
        flat racine à absorber) doit être détecté comme nécessitant une
        migration. Avant BT-030, la présence de ``.operators.yaml``
        court-circuitait la détection et bloquait ``migrate_training_logs``
        (« not in legacy layout »)."""
        assert detect_legacy_layout(hybrid_repo) is True


class TestRaiseIfLegacyLayout:
    def test_raises_on_legacy(self, legacy_flat_repo):
        with pytest.raises(LegacyLayoutError) as exc_info:
            raise_if_legacy_layout(legacy_flat_repo)
        msg = str(exc_info.value)
        # Message actionnable : contient la commande à taper
        assert "poetry run setup --migrate-training-logs" in msg
        # Preview des items legacy dans le message
        assert "activities_tracking.json" in msg or "workouts-history.md" in msg
        # Référence à l'ADR
        assert "ADR v5" in msg

    def test_noop_on_migrated(self, migrated_repo):
        """Pas d'exception sur repo déjà migré."""
        raise_if_legacy_layout(migrated_repo)  # doit passer silencieusement

    def test_noop_on_clean_whitelist(self, clean_whitelist_repo):
        raise_if_legacy_layout(clean_whitelist_repo)

    def test_noop_on_empty(self, empty_repo):
        raise_if_legacy_layout(empty_repo)

    def test_preview_truncated_over_5_items(self, tmp_path):
        (tmp_path / ".git").mkdir()
        for i in range(10):
            (tmp_path / f"legacy_file_{i}.json").write_text("{}")
        with pytest.raises(LegacyLayoutError) as exc_info:
            raise_if_legacy_layout(tmp_path)
        # 5 items visibles + mention "+N autres"
        assert "autres" in str(exc_info.value)

    def test_raises_on_hybrid_with_specific_message(self, hybrid_repo):
        """BT-030 : le message doit distinguer hybride (``.operators.yaml``
        présent) de legacy pur pour aider au diagnostic. L'utilisateur sait
        immédiatement s'il a un repo pré-Phase 2 pur ou un writer déjà
        provisionné mais pas de migration complète."""
        with pytest.raises(LegacyLayoutError) as exc_info:
            raise_if_legacy_layout(hybrid_repo)
        msg = str(exc_info.value)
        assert "hybrid layout" in msg
        assert ".operators.yaml" in msg
        # Commande actionnable toujours présente
        assert "poetry run setup --migrate-training-logs" in msg
        # Items flat racine listés dans preview
        assert "activities_tracking.json" in msg or "data" in msg or "weekly-reports" in msg

    def test_raises_on_legacy_pure_with_specific_message(self, legacy_flat_repo):
        """BT-030 : symétrique du test précédent, le message doit dire
        « legacy layout » (pas « hybrid ») quand ``.operators.yaml`` est
        absent."""
        with pytest.raises(LegacyLayoutError) as exc_info:
            raise_if_legacy_layout(legacy_flat_repo)
        msg = str(exc_info.value)
        assert "legacy layout" in msg
        assert "hybrid" not in msg


class TestDataRepoConfigIntegration:
    def test_writer_scoped_on_legacy_repo_raises_early(self, legacy_flat_repo):
        """Beta-tester qui active WRITER_SCOPED sur un repo legacy →
        LegacyLayoutError levée AVANT même le check WRITER_ID absent."""
        with pytest.raises(LegacyLayoutError):
            DataRepoConfig(data_repo_path=None, writer_scoped=True)  # noqa: F841

    def test_writer_scoped_on_legacy_via_env(self, legacy_flat_repo, monkeypatch):
        monkeypatch.setenv("TRAINING_DATA_ROOT", str(legacy_flat_repo))
        monkeypatch.setenv("TRAINING_DATA_WRITER_SCOPED", "1")
        monkeypatch.delenv("TRAINING_DATA_WRITER_ID", raising=False)
        with pytest.raises(LegacyLayoutError):
            DataRepoConfig()

    def test_legacy_mode_default_on_legacy_repo_works(self, legacy_flat_repo, monkeypatch):
        """Non-régression : mode legacy (writer_scoped=False, défaut)
        sur un repo flat legacy → fonctionne, aucune exception. Le repo
        continue d'être utilisable en rétro-compat tant que le beta n'a
        pas activé le flag WRITER_SCOPED."""
        monkeypatch.setenv("TRAINING_DATA_ROOT", str(legacy_flat_repo))
        monkeypatch.delenv("TRAINING_DATA_WRITER_SCOPED", raising=False)
        config = DataRepoConfig()
        # data_repo_path = root en mode legacy
        assert config.data_repo_path == legacy_flat_repo.resolve()
        assert config.writer_id is None
        assert config.writer_scoped is False

    def test_writer_scoped_on_migrated_repo_needs_writer_id(self, migrated_repo, monkeypatch):
        """Non-régression : sur un repo migré, WRITER_ID reste requis
        en mode writer-scoped (la LegacyLayoutError ne masque pas le
        check WRITER_ID quand il n'y a rien à migrer)."""
        monkeypatch.setenv("TRAINING_DATA_ROOT", str(migrated_repo))
        monkeypatch.setenv("TRAINING_DATA_WRITER_SCOPED", "1")
        monkeypatch.delenv("TRAINING_DATA_WRITER_ID", raising=False)
        with pytest.raises(RuntimeError, match="TRAINING_DATA_WRITER_ID"):
            DataRepoConfig()

    def test_writer_scoped_warns_on_incomplete_whitelist_bt033(
        self, migrated_repo, monkeypatch, caplog
    ):
        """BT-033 : au boot writer_scoped, si ``.operators.yaml::shared_root_files``
        omet les patterns canoniques ADR V5, un warning explicite doit être
        loggé (non-blocking) pour signaler la config à corriger avant qu'un
        write runtime ne casse un tool en prod."""
        import logging

        monkeypatch.setenv("TRAINING_DATA_ROOT", str(migrated_repo))
        monkeypatch.setenv("TRAINING_DATA_WRITER_SCOPED", "1")
        monkeypatch.setenv("TRAINING_DATA_WRITER_ID", "abc123def456")
        # migrated_repo fixture a shared_root_files = [.gitignore, README.md,
        # .operators.yaml] — restrictif, omet data/{intelligence,wellness,decisions}/**
        # + config/athlete.yaml
        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            DataRepoConfig()
        # Warning émis pour au moins 1 des 4 patterns canoniques
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any(
            "shared_root_files" in r.message and "canonical" in r.message for r in warning_records
        ), f"Expected BT-033 warning, got: {[r.message for r in warning_records]}"
        assert any(
            "data/wellness/**" in r.message
            or "data/intelligence/**" in r.message
            or "data/decisions/**" in r.message
            for r in warning_records
        )
        # Warning mentionne l'action de fix + réf BT-033
        assert any("BT-033" in r.message for r in warning_records)

    def test_writer_scoped_no_warn_on_canonical_whitelist_bt033(
        self, tmp_path, monkeypatch, caplog
    ):
        """BT-033 : yaml avec whitelist canonique complète → aucun warning."""
        import logging

        from magma_cycling.config.data_repo import DEFAULT_SHARED_ROOT_FILES

        # Fixture repo avec whitelist canonique complète
        (tmp_path / ".git").mkdir()
        (tmp_path / ".gitignore").write_text("*.pyc\n")
        import yaml as yaml_mod

        ops = {
            "shared_root_files": list(DEFAULT_SHARED_ROOT_FILES),
            "writers": {
                "abc123def456": {
                    "alias": "mac",
                    "host": "tiresias",
                    "provisioned_at": "2026-08-13T21:00:00Z",
                    "decommissioned_at": None,
                }
            },
        }
        (tmp_path / ".operators.yaml").write_text(yaml_mod.safe_dump(ops), encoding="utf-8")
        (tmp_path / "abc123def456").mkdir()
        (tmp_path / "abc123def456" / "data.json").write_text("{}")

        monkeypatch.setenv("TRAINING_DATA_ROOT", str(tmp_path))
        monkeypatch.setenv("TRAINING_DATA_WRITER_SCOPED", "1")
        monkeypatch.setenv("TRAINING_DATA_WRITER_ID", "abc123def456")
        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            DataRepoConfig()
        # Zéro warning « canonical » sur ce boot
        bt033_warnings = [
            r for r in caplog.records if r.levelname == "WARNING" and "canonical" in r.message
        ]
        assert bt033_warnings == [], f"Expected no BT-033 warning, got: {bt033_warnings}"

    def test_writer_scoped_on_hybrid_repo_raises_bt030(self, hybrid_repo, monkeypatch):
        """BT-030 : activer writer_scoped sur un repo hybride doit lever
        ``LegacyLayoutError`` (AVANT le check WRITER_ID) pour empêcher un
        runtime qui écrirait dans un layout mal formé. Le message doit
        pointer sur la migration hybride, pas legacy pur."""
        monkeypatch.setenv("TRAINING_DATA_ROOT", str(hybrid_repo))
        monkeypatch.setenv("TRAINING_DATA_WRITER_SCOPED", "1")
        monkeypatch.setenv("TRAINING_DATA_WRITER_ID", "88bc132e32a0")  # writer déjà provisionné
        with pytest.raises(LegacyLayoutError, match="hybrid layout"):
            DataRepoConfig()
