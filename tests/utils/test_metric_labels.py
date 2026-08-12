"""Tests pour magma_cycling.utils.metric_labels (BT-022)."""

from __future__ import annotations

import pytest

from magma_cycling.utils import metric_labels
from magma_cycling.utils.metric_labels import get_description, get_label


@pytest.fixture(autouse=True)
def _clear_labels_cache():
    """Invalide le cache lru avant/après chaque test pour l'isolation."""
    metric_labels._load_labels.cache_clear()
    yield
    metric_labels._load_labels.cache_clear()


class TestGetLabel:
    """Comportement de get_label sur le YAML canonique du repo."""

    def test_returns_fr_by_default(self):
        assert get_label("tss") == "TSS"
        assert get_label("normalized_power") == "Puissance normalisée"
        assert get_label("intensity_factor") == "Facteur d'intensité"

    def test_locale_en(self):
        assert get_label("normalized_power", locale="en") == "Normalized Power"
        assert get_label("intensity_factor", locale="en") == "Intensity Factor"

    def test_short_form(self):
        assert get_label("normalized_power", form="short") == "NP"
        assert get_label("intensity_factor", form="short") == "IF"
        assert get_label("tss_planned", form="short") == "TSS plan."

    def test_fallback_to_default_locale_if_missing(self, tmp_path, monkeypatch):
        """Si la locale demandée n'existe pas, retour sur locale par défaut (fr)."""
        yaml_content = "some_metric:\n  fr: 'Métrique'\n"
        fake_file = tmp_path / "metric_labels.yaml"
        fake_file.write_text(yaml_content, encoding="utf-8")
        monkeypatch.setattr(metric_labels, "_LABELS_FILE", fake_file)
        metric_labels._load_labels.cache_clear()

        assert get_label("some_metric", locale="de") == "Métrique"

    def test_unknown_key_returns_key_as_fallback(self, caplog):
        """Clé absente → retour clé technique + warning log."""
        with caplog.at_level("WARNING"):
            result = get_label("bogus_metric_that_does_not_exist")
        assert result == "bogus_metric_that_does_not_exist"
        assert any("clé inconnue" in r.message for r in caplog.records)


class TestGetDescription:
    """Comportement de get_description (glose optionnelle)."""

    def test_returns_description_when_present(self):
        desc = get_description("ctl")
        assert desc is not None
        assert "Chronic Training Load" in desc

    def test_returns_none_for_key_without_description(self):
        # `training_load` n'a pas de champ description dans le YAML.
        assert get_description("training_load") is None

    def test_returns_none_for_unknown_key(self):
        assert get_description("bogus_key_xyz") is None


class TestFallbackWhenYamlMissing:
    """Fallback safe quand le YAML n'est pas lisible."""

    def test_missing_yaml_file_falls_back_gracefully(self, tmp_path, monkeypatch, caplog):
        fake_missing = tmp_path / "does_not_exist.yaml"
        monkeypatch.setattr(metric_labels, "_LABELS_FILE", fake_missing)
        metric_labels._load_labels.cache_clear()

        with caplog.at_level("WARNING"):
            result = get_label("tss")
        assert result == "tss"  # retour clé technique
        assert any("introuvable" in r.message for r in caplog.records)

    def test_malformed_yaml_falls_back_gracefully(self, tmp_path, monkeypatch, caplog):
        broken = tmp_path / "broken.yaml"
        broken.write_text("this is: [not valid yaml\n  broken", encoding="utf-8")
        monkeypatch.setattr(metric_labels, "_LABELS_FILE", broken)
        metric_labels._load_labels.cache_clear()

        with caplog.at_level("WARNING"):
            result = get_label("tss")
        assert result == "tss"
        assert any("illisible" in r.message for r in caplog.records)

    def test_non_dict_yaml_root_falls_back(self, tmp_path, monkeypatch, caplog):
        # YAML valide mais racine = liste (pas dict).
        bad_shape = tmp_path / "list_root.yaml"
        bad_shape.write_text("- item1\n- item2\n", encoding="utf-8")
        monkeypatch.setattr(metric_labels, "_LABELS_FILE", bad_shape)
        metric_labels._load_labels.cache_clear()

        with caplog.at_level("WARNING"):
            result = get_label("tss")
        assert result == "tss"
        assert any("pas un dict racine" in r.message for r in caplog.records)


class TestCacheBehavior:
    """Cache lru sur _load_labels."""

    def test_cache_prevents_repeat_yaml_reads(self, tmp_path, monkeypatch):
        yaml_content = "cached:\n  fr: 'Original'\n"
        fake_file = tmp_path / "metric_labels.yaml"
        fake_file.write_text(yaml_content, encoding="utf-8")
        monkeypatch.setattr(metric_labels, "_LABELS_FILE", fake_file)
        metric_labels._load_labels.cache_clear()

        assert get_label("cached") == "Original"

        # Modifie le fichier après la première lecture — cache doit tenir.
        fake_file.write_text("cached:\n  fr: 'Updated'\n", encoding="utf-8")
        assert get_label("cached") == "Original"  # cache pas invalidé

        # Invalidation manuelle → nouvelle lecture visible.
        metric_labels._load_labels.cache_clear()
        assert get_label("cached") == "Updated"
