"""Tests for the shared YAML I/O primitives (TOCTOU-safe write helpers)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import yaml

from magma_cycling.config._yaml_io import atomic_write_yaml, read_yaml


class TestReadYaml:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path):
        assert read_yaml(tmp_path / "absent.yaml") == {}

    def test_valid_yaml_returns_dict(self, tmp_path: Path):
        p = tmp_path / "ok.yaml"
        p.write_text("foo: bar\nbaz: 1\n", encoding="utf-8")
        assert read_yaml(p) == {"foo": "bar", "baz": 1}

    def test_malformed_yaml_returns_empty_and_warns(self, tmp_path: Path, caplog):
        p = tmp_path / "bad.yaml"
        p.write_text("not: valid: yaml: [", encoding="utf-8")
        with caplog.at_level("WARNING"):
            assert read_yaml(p) == {}
        assert any("malformed" in r.message for r in caplog.records)

    def test_non_dict_root_returns_empty_dict(self, tmp_path: Path):
        p = tmp_path / "list.yaml"
        p.write_text("- one\n- two\n", encoding="utf-8")
        assert read_yaml(p) == {}


class TestAtomicWriteYaml:
    def test_creates_file_with_0o600_perms(self, tmp_path: Path):
        p = tmp_path / "out.yaml"
        atomic_write_yaml(p, {"foo": "bar"})
        assert p.is_file()
        mode = stat.S_IMODE(p.stat().st_mode)
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_creates_parent_dir_with_0o700_when_absent(self, tmp_path: Path):
        nested = tmp_path / "newdir" / "deeper"
        p = nested / "out.yaml"
        atomic_write_yaml(p, {"foo": "bar"})
        assert nested.is_dir()
        mode = stat.S_IMODE(nested.stat().st_mode)
        assert mode == 0o700, f"Expected 0o700 on new parent, got {oct(mode)}"

    def test_does_not_change_existing_parent_perms(self, tmp_path: Path):
        existing = tmp_path / "preexisting"
        existing.mkdir(mode=0o755)
        os.chmod(existing, 0o755)
        p = existing / "out.yaml"
        atomic_write_yaml(p, {"foo": "bar"})
        mode = stat.S_IMODE(existing.stat().st_mode)
        assert mode == 0o755, f"Existing parent perms must be preserved, got {oct(mode)}"

    def test_content_is_correct(self, tmp_path: Path):
        p = tmp_path / "out.yaml"
        atomic_write_yaml(p, {"foo": "bar", "nested": {"k": 1}})
        loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert loaded == {"foo": "bar", "nested": {"k": 1}}

    def test_overwrites_existing_file(self, tmp_path: Path):
        p = tmp_path / "out.yaml"
        atomic_write_yaml(p, {"v": 1})
        atomic_write_yaml(p, {"v": 2})
        assert yaml.safe_load(p.read_text(encoding="utf-8")) == {"v": 2}

    def test_temp_file_cleaned_up_on_success(self, tmp_path: Path):
        p = tmp_path / "out.yaml"
        atomic_write_yaml(p, {"v": 1})
        leftovers = [x for x in tmp_path.iterdir() if ".tmp" in x.name]
        assert leftovers == [], f"Unexpected temp leftovers: {leftovers}"

    def test_preserves_unicode(self, tmp_path: Path):
        p = tmp_path / "out.yaml"
        atomic_write_yaml(p, {"nom": "Les Copains 81km — préparation"})
        loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert loaded["nom"] == "Les Copains 81km — préparation"
