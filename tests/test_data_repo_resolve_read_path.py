"""Tests for DataRepoConfig.resolve_read_path (PR11a iso-config Phase 3 PR D).

Couvre :
- Mode legacy (writer_scoped=False) : no-op, fallback root_path
- Mode scoped (writer_scoped=True) : matching authority, résolution alias→hash
- Matching patterns : exact, glob /**, glob /*, conflit ordre déclaration
- Fallbacks : pas de match, alias non résolvable, .operators.yaml absent
- Helper statique : _match_authority_pattern (POSIX-style)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from magma_cycling.config.data_repo import DataRepoConfig


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Crée un repo training-logs minimal pour exercer DataRepoConfig."""
    (tmp_path / "workouts-history.md").touch()
    return tmp_path


@pytest.fixture
def writers_section() -> str:
    """3 writers conformes au .operators.yaml réel (ADR v5 §1.bis)."""
    return """
writers:
  b08921dae3e7:
    alias: mac
    host: tiresias
  5e6f282f9f03:
    alias: nas-prod
    host: synology-penelope
  8816403fa31c:
    alias: nas-preprod
    host: synology-penelope
"""


def _seed_operators_yaml(repo_root: Path, content: str) -> None:
    """Écrit ``.operators.yaml`` à la racine du repo."""
    (repo_root / ".operators.yaml").write_text(content, encoding="utf-8")


class TestResolveReadPathLegacyMode:
    """Mode legacy (writer_scoped=False) : helper no-op."""

    def test_no_writer_scoped_returns_root_path(self, tmp_repo: Path):
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        result = cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
        assert result == tmp_repo / "weekly-reports/S094/bilan_final.md"

    def test_no_writer_scoped_ignores_operators_yaml(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  weekly-reports/**: nas-prod
""",
        )
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        result = cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
        assert result == tmp_repo / "weekly-reports/S094/bilan_final.md"


class TestResolveReadPathScopedMode:
    """Mode scoped (writer_scoped=True) : résolution via authority+writers."""

    def _make_scoped_cfg(self, tmp_repo: Path) -> DataRepoConfig:
        (tmp_repo / "b08921dae3e7").mkdir(exist_ok=True)
        return DataRepoConfig(data_repo_path=tmp_repo, writer_scoped=True, writer_id="b08921dae3e7")

    def test_glob_recursive_authority_routes_to_writer_hash(
        self, tmp_repo: Path, writers_section: str
    ):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  weekly-reports/**: nas-prod
  workouts/**: mac
""",
        )
        cfg = self._make_scoped_cfg(tmp_repo)
        assert (
            cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
            == tmp_repo / "5e6f282f9f03/weekly-reports/S094/bilan_final.md"
        )
        assert (
            cfg.resolve_read_path("workouts/MyWorkout.zwo")
            == tmp_repo / "b08921dae3e7/workouts/MyWorkout.zwo"
        )

    def test_exact_match_authority(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  workouts-history.md: nas-prod
""",
        )
        cfg = self._make_scoped_cfg(tmp_repo)
        result = cfg.resolve_read_path("workouts-history.md")
        assert result == tmp_repo / "5e6f282f9f03/workouts-history.md"

    def test_first_match_wins_on_overlapping_rules(self, tmp_repo: Path, writers_section: str):
        """L'ordre de déclaration YAML est respecté — premier match gagne."""
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  data/backups/**: mac
  data/**: nas-prod
""",
        )
        cfg = self._make_scoped_cfg(tmp_repo)
        result = cfg.resolve_read_path("data/backups/2026-05-25/snapshot.json")
        assert result == tmp_repo / "b08921dae3e7/data/backups/2026-05-25/snapshot.json"

    def test_no_match_falls_back_to_root_path(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  weekly-reports/**: nas-prod
""",
        )
        cfg = self._make_scoped_cfg(tmp_repo)
        result = cfg.resolve_read_path(".gitignore")
        assert result == tmp_repo / ".gitignore"

    def test_alias_not_resolvable_falls_back_to_root_path(
        self, tmp_repo: Path, writers_section: str, caplog
    ):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  ghost-reports/**: ghost-writer
""",
        )
        cfg = self._make_scoped_cfg(tmp_repo)
        import logging

        with caplog.at_level(logging.WARNING, logger="magma_cycling.config.data_repo"):
            result = cfg.resolve_read_path("ghost-reports/foo.md")
        assert result == tmp_repo / "ghost-reports/foo.md"
        assert any("ghost-writer" in r.message for r in caplog.records)

    def test_missing_operators_yaml_falls_back_to_root_path(self, tmp_repo: Path):
        cfg = self._make_scoped_cfg(tmp_repo)
        result = cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
        assert result == tmp_repo / "weekly-reports/S094/bilan_final.md"

    def test_authority_section_missing_falls_back_to_root_path(
        self, tmp_repo: Path, writers_section: str
    ):
        _seed_operators_yaml(tmp_repo, writers_section)
        cfg = self._make_scoped_cfg(tmp_repo)
        result = cfg.resolve_read_path("weekly-reports/S094/bilan_final.md")
        assert result == tmp_repo / "weekly-reports/S094/bilan_final.md"


class TestAuthorityRulesProperty:
    """Property authority_rules : extraction ordonnée du .operators.yaml."""

    def test_empty_when_no_operators_yaml(self, tmp_repo: Path):
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        assert cfg.authority_rules == []

    def test_empty_when_no_authority_section(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(tmp_repo, writers_section)
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        assert cfg.authority_rules == []

    def test_preserves_yaml_declaration_order(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  data/backups/**: mac
  data/**: nas-prod
  weekly-reports/**: nas-prod
""",
        )
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        rules = cfg.authority_rules
        assert rules == [
            ("data/backups/**", "mac"),
            ("data/**", "nas-prod"),
            ("weekly-reports/**", "nas-prod"),
        ]

    def test_filters_non_string_entries(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(
            tmp_repo,
            writers_section
            + """
authority:
  weekly-reports/**: nas-prod
  invalid_key: [list, value]
  data/backups/**: mac
""",
        )
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        rules = cfg.authority_rules
        assert ("weekly-reports/**", "nas-prod") in rules
        assert ("data/backups/**", "mac") in rules
        assert all(isinstance(v, str) for _, v in rules)


class TestMatchAuthorityPattern:
    """Helper statique _match_authority_pattern (POSIX-style)."""

    def test_recursive_glob_double_star(self):
        assert DataRepoConfig._match_authority_pattern("workouts/foo.zwo", "workouts/**")
        assert DataRepoConfig._match_authority_pattern("workouts/sub/dir/bar.zwo", "workouts/**")

    def test_recursive_glob_single_star(self):
        assert DataRepoConfig._match_authority_pattern("workouts/foo.zwo", "workouts/*")
        assert DataRepoConfig._match_authority_pattern("workouts/sub/bar.zwo", "workouts/*")

    def test_glob_does_not_match_sibling_paths(self):
        assert not DataRepoConfig._match_authority_pattern("other/foo.zwo", "workouts/**")

    def test_exact_match(self):
        assert DataRepoConfig._match_authority_pattern("workouts-history.md", "workouts-history.md")
        assert not DataRepoConfig._match_authority_pattern(
            "workouts-history.md.bak", "workouts-history.md"
        )

    def test_fnmatch_wildcard_no_slash(self):
        assert DataRepoConfig._match_authority_pattern("S094_planning.json", "S*_planning.json")
        assert not DataRepoConfig._match_authority_pattern("planning.json", "S*_planning.json")


class TestResolveWriterAliasToHash:
    """Helper _resolve_writer_alias_to_hash."""

    def test_resolves_known_alias(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(tmp_repo, writers_section)
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        assert cfg._resolve_writer_alias_to_hash("mac") == "b08921dae3e7"
        assert cfg._resolve_writer_alias_to_hash("nas-prod") == "5e6f282f9f03"
        assert cfg._resolve_writer_alias_to_hash("nas-preprod") == "8816403fa31c"

    def test_unknown_alias_returns_none(self, tmp_repo: Path, writers_section: str):
        _seed_operators_yaml(tmp_repo, writers_section)
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        assert cfg._resolve_writer_alias_to_hash("ghost") is None

    def test_no_operators_yaml_returns_none(self, tmp_repo: Path):
        cfg = DataRepoConfig(data_repo_path=tmp_repo)
        assert cfg._resolve_writer_alias_to_hash("mac") is None
