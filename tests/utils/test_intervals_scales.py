"""Tests for intervals_scales utility module."""

import pytest

from magma_cycling.utils.intervals_scales import FEEL_EMOJIS, FEEL_LABELS, format_feel


class TestFeelLabels:
    """Tests for FEEL_LABELS and FEEL_EMOJIS constants."""

    def test_labels_cover_1_to_5(self):
        assert set(FEEL_LABELS.keys()) == {1, 2, 3, 4, 5}

    def test_emojis_cover_1_to_5(self):
        assert set(FEEL_EMOJIS.keys()) == {1, 2, 3, 4, 5}


class TestFormatFeel:
    """Tests for format_feel function."""

    def test_none_returns_non_renseigne(self):
        assert format_feel(None) == "_Non renseigné_"

    def test_none_with_emoji_returns_non_renseigne(self):
        assert format_feel(None, with_emoji=True) == "_Non renseigné_"

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1, "Excellent"),
            (2, "Bien"),
            (3, "Moyen"),
            (4, "Passable"),
            (5, "Mauvais"),
        ],
    )
    def test_plain_labels(self, value, expected):
        assert format_feel(value) == expected

    @pytest.mark.parametrize(
        "value,expected_label",
        [
            (1, "Excellent"),
            (2, "Bien"),
            (3, "Moyen"),
            (4, "Passable"),
            (5, "Mauvais"),
        ],
    )
    def test_with_emoji_contains_label_and_fraction(self, value, expected_label):
        result = format_feel(value, with_emoji=True)
        assert expected_label in result
        assert f"({value}/5)" in result

    def test_with_emoji_starts_with_emoji(self):
        result = format_feel(1, with_emoji=True)
        # Should start with emoji character, not a letter
        assert not result[0].isalpha()

    def test_unknown_value_returns_valeur_inconnue(self):
        assert format_feel(99) == "_Valeur inconnue: 99_"

    def test_zero_returns_valeur_inconnue(self):
        assert format_feel(0) == "_Valeur inconnue: 0_"
