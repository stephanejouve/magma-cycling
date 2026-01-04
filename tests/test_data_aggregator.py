"""
Tests for DataAggregator abstract framework.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

from cyclisme_training_logs.core.data_aggregator import DataAggregator


class ConcreteAggregator(DataAggregator):
    """Implémentation concrète pour tests."""

    def collect_raw_data(self):
        return {"test": "data"}

    def process_data(self, raw_data):
        return {"processed": raw_data["test"].upper()}

    def format_output(self, processed_data):
        return f"Result: {processed_data['processed']}"


def test_aggregator_pipeline():
    """Test pipeline complet agrégation."""
    aggregator = ConcreteAggregator()

    result = aggregator.aggregate()

    assert result.success
    assert result.data["raw"] == {"test": "data"}
    assert result.data["processed"] == {"processed": "DATA"}
    assert result.data["formatted"] == "Result: DATA"


def test_aggregator_with_metadata():
    """Test ajout metadata."""
    aggregator = ConcreteAggregator()

    data = {"key": "value"}
    enriched = aggregator.add_metadata(data)

    assert "_metadata" in enriched
    assert enriched["_metadata"]["aggregator"] == "ConcreteAggregator"


def test_aggregator_with_custom_config():
    """Test agrégateur avec configuration personnalisée."""
    config = {"option": "value"}

    aggregator = ConcreteAggregator(config=config)

    assert aggregator.config == config


def test_aggregator_with_custom_data_dir(tmp_path):
    """Test agrégateur avec répertoire données personnalisé."""
    aggregator = ConcreteAggregator(data_dir=tmp_path)

    assert aggregator.data_dir == tmp_path


def test_aggregator_error_handling():
    """Test gestion erreurs dans pipeline."""

    class FailingAggregator(DataAggregator):
        def collect_raw_data(self):
            raise ValueError("Collection failed")

        def process_data(self, raw_data):
            return {}

        def format_output(self, processed_data):
            return ""

    aggregator = FailingAggregator()
    result = aggregator.aggregate()

    assert not result.success
    assert len(result.errors) > 0
    assert "Collection failed" in result.errors[0]


def test_validate_data():
    """Test hook validation données."""
    aggregator = ConcreteAggregator()

    assert aggregator.validate_data({"key": "value"}) is True
