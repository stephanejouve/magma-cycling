"""Tests for the get-coach-analysis MCP tool."""

import json
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)

# ---------------------------------------------------------------------------
# Fixture: sample workouts-history.md content
# ---------------------------------------------------------------------------

SAMPLE_HISTORY = """\
### S084-04-END-EnduranceLongue-V001
ID : i131572602
Date : 12/03/2026

#### Métriques Pré-séance
- CTL : 45
- ATL : 57
- TSB : -12
- Sommeil : 7.0h

#### Exécution
- Durée : 174min
- IF : 0.78
- TSS : 175

#### Exécution Technique
La séance visait une endurance longue en zone 2.

#### Charge d'Entraînement
Le TSS réalisé (175) dépasse le TSS planifié (150).

#### Validation Objectifs
- ❌ Respect intensité Z2 : IF 0.78 > 0.70
- ✅ Découplage aérobie < 5%

#### Points d'Attention
- Surcharge non intentionnelle due au vent

#### Recommandations Progression
1. Passer en indoor pour mieux contrôler l'intensité
2. Réduire la durée de 15min si conditions venteuses

#### Métriques Post-séance
- CTL : 45
- ATL : 53
- TSB : -9

### S084-03-INT-TempoCourt-V001
ID : i131572601
Date : 11/03/2026

#### Métriques Pré-séance
- CTL : 44
- ATL : 55

#### Exécution
- Durée : 60min
- IF : 0.88

#### Exécution Technique
Bonne exécution des intervalles tempo.

#### Charge d'Entraînement
TSS conforme au plan.

#### Validation Objectifs
- ✅ Puissance tempo maintenue
- ✅ Cadence cible atteinte

#### Points d'Attention
Aucun point particulier.

#### Recommandations Progression
1. Augmenter la durée des intervalles la semaine prochaine

#### Métriques Post-séance
- CTL : 44
- ATL : 56

### S084-05-REC-Recuperation-V001
ID : i131572603
Date : 12/03/2026

#### Métriques Pré-séance
- CTL : 45

#### Exécution
- Durée : 30min

#### Exécution Technique
Récupération active légère.

#### Charge d'Entraînement
TSS faible comme prévu.

#### Validation Objectifs
- ✅ Intensité basse respectée

#### Points d'Attention
RAS

#### Recommandations Progression
Maintenir ce type de séance après les blocs intensifs.

#### Métriques Post-séance
- CTL : 45
"""


@pytest.fixture
def mock_data_config(tmp_path):
    """Mock get_data_config to use a temp workouts-history.md."""
    history_file = tmp_path / "workouts-history.md"
    history_file.write_text(SAMPLE_HISTORY, encoding="utf-8")

    config = MagicMock()
    config.workouts_history_path = history_file
    config.data_repo_path = tmp_path

    with patch(
        "magma_cycling.config.get_data_config",
        return_value=config,
    ):
        yield config


@pytest.fixture
def mock_data_config_empty(tmp_path):
    """Mock with empty history file."""
    history_file = tmp_path / "workouts-history.md"
    history_file.write_text("", encoding="utf-8")

    config = MagicMock()
    config.workouts_history_path = history_file
    config.data_repo_path = tmp_path

    with patch(
        "magma_cycling.config.get_data_config",
        return_value=config,
    ):
        yield config


@pytest.fixture
def mock_data_config_missing(tmp_path):
    """Mock with non-existent history file."""
    config = MagicMock()
    config.workouts_history_path = tmp_path / "nonexistent.md"
    config.data_repo_path = tmp_path

    with patch(
        "magma_cycling.config.get_data_config",
        return_value=config,
    ):
        yield config


def _parse_result(result):
    """Parse MCP TextContent result to dict."""
    return json.loads(result[0].text)


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_by_activity_id(mock_data_config):
    """Find analysis by Intervals.icu activity ID."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"activity_id": "i131572602"}))

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["analyses"][0]["activity_id"] == "i131572602"
    assert result["analyses"][0]["activity_name"] == "S084-04-END-EnduranceLongue-V001"
    assert result["analyses"][0]["week_id"] == "S084"


@pytest.mark.asyncio
async def test_by_session_id(mock_data_config):
    """Find analysis by session ID (word-boundary match)."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"session_id": "S084-04"}))

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["analyses"][0]["activity_name"] == "S084-04-END-EnduranceLongue-V001"


@pytest.mark.asyncio
async def test_by_session_id_no_partial_match(mock_data_config):
    """Session ID S084-0 should NOT match S084-03, S084-04, S084-05."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"session_id": "S084-0"}))

    # S084-0 has word boundary after "0", but S084-03 has "3" after — no match
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_by_date(mock_data_config):
    """Find all analyses for a given date (multiple results)."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"date": "2026-03-12"}))

    assert result["status"] == "success"
    assert result["count"] == 2
    names = [a["activity_name"] for a in result["analyses"]]
    assert "S084-04-END-EnduranceLongue-V001" in names
    assert "S084-05-REC-Recuperation-V001" in names


@pytest.mark.asyncio
async def test_section_filter(mock_data_config):
    """Filter to a specific section only."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(
        await handle_get_coach_analysis({"activity_id": "i131572602", "section": "recommendations"})
    )

    assert result["status"] == "success"
    assert result["count"] == 1
    analysis = result["analyses"][0]
    assert "recommendations" in analysis["sections"]
    assert "indoor" in analysis["sections"]["recommendations"]
    # When section filter is active, content should be absent
    assert "content" not in analysis


@pytest.mark.asyncio
async def test_not_found(mock_data_config):
    """Gracefully return empty when no match."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"activity_id": "i999999999"}))

    assert result["status"] == "success"
    assert result["count"] == 0
    assert result["analyses"] == []


@pytest.mark.asyncio
async def test_no_params_error():
    """Return error when no search parameter provided."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({}))

    assert "error" in result
    assert "At least one search parameter" in result["error"]


@pytest.mark.asyncio
async def test_structured_sections(mock_data_config):
    """Verify all 8 sections are parsed correctly."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"activity_id": "i131572602"}))

    sections = result["analyses"][0]["sections"]
    expected_keys = [
        "metrics_pre",
        "execution",
        "technique",
        "load",
        "validation",
        "attention",
        "recommendations",
        "metrics_post",
    ]
    for key in expected_keys:
        assert key in sections, f"Missing section: {key}"
        assert sections[key], f"Empty section: {key}"

    # Spot-check content
    assert "CTL : 45" in sections["metrics_pre"]
    assert "174min" in sections["execution"]
    assert "❌" in sections["validation"]
    assert "indoor" in sections["recommendations"]


@pytest.mark.asyncio
async def test_missing_file(mock_data_config_missing):
    """Handle missing workouts-history.md gracefully."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"activity_id": "i131572602"}))

    assert result["status"] == "success"
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_empty_file(mock_data_config_empty):
    """Handle empty workouts-history.md gracefully."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"activity_id": "i131572602"}))

    assert result["status"] == "success"
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_invalid_section():
    """Return error for invalid section parameter."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(
        await handle_get_coach_analysis({"activity_id": "i131572602", "section": "nonexistent"})
    )

    assert "error" in result
    assert "Invalid section" in result["error"]


@pytest.mark.asyncio
async def test_week_id_extracted(mock_data_config):
    """Verify week_id is extracted from activity name."""
    from magma_cycling._mcp.handlers.analysis import handle_get_coach_analysis

    result = _parse_result(await handle_get_coach_analysis({"session_id": "S084-03"}))

    assert result["analyses"][0]["week_id"] == "S084"
