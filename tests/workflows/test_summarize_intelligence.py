"""Tests for _summarize_intelligence in context_loading."""

import json

from magma_cycling.workflows.planner.context_loading import _summarize_intelligence


def test_summarize_filters_low_confidence_learnings():
    """Test that low confidence learnings are excluded."""
    data = {
        "learnings": {
            "low_1": {
                "category": "test",
                "description": "Low conf",
                "confidence": "low",
                "impact": "LOW",
                "evidence": ["E1"],
            },
            "med_1": {
                "category": "test2",
                "description": "Med conf",
                "confidence": "medium",
                "impact": "MEDIUM",
                "evidence": ["E1", "E2", "E3"],
            },
        },
        "adaptations": {},
        "patterns": {},
    }

    result = _summarize_intelligence(data)

    assert "Med conf" in result
    assert "Low conf" not in result
    assert "1 sur 2" in result


def test_summarize_deduplicates_and_limits_evidence():
    """Test that evidence is deduplicated and limited to 5."""
    data = {
        "learnings": {
            "test_1": {
                "category": "test",
                "description": "Test",
                "confidence": "high",
                "impact": "HIGH",
                "evidence": ["E1", "E2", "E1", "E3", "E2", "E4", "E5", "E6", "E7"],
            },
        },
        "adaptations": {},
        "patterns": {},
    }

    result = _summarize_intelligence(data)
    parsed = json.loads(result.split("\n", 1)[1])

    learning = parsed[0]
    # 9 items → 7 unique → show 5 + evidence_total
    assert len(learning["evidence"]) == 5
    assert learning["evidence_total"] == 7


def test_summarize_keeps_one_adaptation_per_protocol():
    """Test that only most recent PROPOSED adaptation per protocol is kept."""
    data = {
        "learnings": {},
        "adaptations": {
            "ftp_ADD_1000": {
                "protocol_name": "ftp_test_cycle",
                "adaptation_type": "ADD",
                "proposed_rule": "Old proposal",
                "justification": "Old",
                "confidence": "low",
                "status": "PROPOSED",
            },
            "ftp_ADD_2000": {
                "protocol_name": "ftp_test_cycle",
                "adaptation_type": "ADD",
                "proposed_rule": "Recent proposal",
                "justification": "Recent",
                "confidence": "low",
                "status": "PROPOSED",
            },
            "ftp_ADD_3000": {
                "protocol_name": "ftp_test_cycle",
                "adaptation_type": "ADD",
                "proposed_rule": "Most recent",
                "justification": "Latest",
                "confidence": "low",
                "status": "EXPIRED",
            },
        },
        "patterns": {},
    }

    result = _summarize_intelligence(data)

    assert "Recent proposal" in result
    assert "Old proposal" not in result
    assert "Most recent" not in result  # EXPIRED, excluded
    assert "1 sur 3" in result


def test_summarize_empty_data():
    """Test that empty intelligence returns placeholder."""
    data = {"learnings": {}, "adaptations": {}, "patterns": {}}
    result = _summarize_intelligence(data)
    assert result == "[Aucune recommandation d'adaptation disponible]"


def test_summarize_patterns_passed_through():
    """Test that patterns are included as-is."""
    data = {
        "learnings": {},
        "adaptations": {},
        "patterns": {
            "p1": {
                "name": "sleep_debt",
                "trigger_conditions": {"sleep": "<6h"},
                "observed_outcome": "Failure",
                "frequency": 5,
            }
        },
    }

    result = _summarize_intelligence(data)
    assert "sleep_debt" in result
    assert "Patterns (1)" in result
