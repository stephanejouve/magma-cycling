"""Tests du sanitizer de description workout (BT-008)."""

from magma_cycling.workflows.uploader.upload import sanitize_description


class TestSanitizeDescription:
    """Les tirets non-intervalle sont remplacés par des bullets."""

    def test_interval_lines_preserved(self):
        desc = "Warmup\n- 10m ramp 50-65% 85rpm\n- 3m 65% 90rpm"
        result = sanitize_description(desc)
        assert "- 10m ramp" in result
        assert "- 3m 65%" in result

    def test_points_cles_dashes_replaced(self):
        desc = (
            "Warmup\n- 10m 50% 85rpm\n\n"
            "Main set\n- 20m 75% 90rpm\n\n"
            "Cooldown\n- 10m 50% 85rpm\n\n"
            "Points clés\n- Garder la cadence haute\n- Hydratation toutes les 20min"
        )
        result = sanitize_description(desc)
        assert "• Garder la cadence haute" in result
        assert "• Hydratation toutes les 20min" in result
        # Les intervalles sont préservés
        assert "- 10m 50%" in result
        assert "- 20m 75%" in result

    def test_mixed_content(self):
        desc = (
            "Sweet Spot 3x10 (74min, 78 TSS)\n\n"
            "Warmup\n- 12m ramp 50-65% 85rpm\n- 5m 65% 90rpm\n\n"
            "Main set 3x\n- 10m 90% 92rpm\n- 4m 62% 85rpm\n\n"
            "Cooldown\n- 10m ramp 65-50% 85rpm\n\n"
            "Points clés\n- Maintenir cadence >90rpm\n- Ne pas dépasser 95%"
        )
        result = sanitize_description(desc)
        # Intervalles préservés
        assert "- 12m ramp" in result
        assert "- 10m 90%" in result
        assert "- 10m ramp 65-50%" in result
        # Points clés transformés
        assert "• Maintenir cadence" in result
        assert "• Ne pas dépasser" in result

    def test_no_dashes_unchanged(self):
        desc = "Endurance Base (70min, 52 TSS)\n\nWarmup\n- 10m 50% 85rpm"
        result = sanitize_description(desc)
        assert result == desc

    def test_empty_description(self):
        assert sanitize_description("") == ""

    def test_text_only_dashes(self):
        desc = "Notes de séance\n- Boire régulièrement\n- Rester assis"
        result = sanitize_description(desc)
        assert "• Boire régulièrement" in result
        assert "• Rester assis" in result

    def test_real_world_bt008(self):
        """Cas réel BT-008 : Endurance Longue + Tempo avec Points clés."""
        desc = (
            "Endurance Longue + Tempo (3h30, 200 TSS)\n\n"
            "Warmup\n- 15m ramp 50-65% 85rpm\n\n"
            "Main set\n- 120m 65-70% 88rpm\n- 30m 76-80% 90rpm\n\n"
            "Cooldown\n- 15m ramp 60-45% 80rpm\n\n"
            "Points clés\n"
            "- Nutrition : 60g glucides/h dès la première heure\n"
            "- Hydratation : 500ml/h minimum\n"
            "- Tempo : attendre 2h avant de monter en intensité"
        )
        result = sanitize_description(desc)
        # Intervalles intacts
        assert "- 15m ramp 50-65%" in result
        assert "- 120m 65-70%" in result
        assert "- 30m 76-80%" in result
        assert "- 15m ramp 60-45%" in result
        # Points clés transformés
        assert "• Nutrition" in result
        assert "• Hydratation" in result
        assert "• Tempo" in result
        # Aucun tiret parasite restant dans les Points clés
        lines = result.split("\n")
        after_points_cles = False
        for line in lines:
            if "Points clés" in line:
                after_points_cles = True
                continue
            if after_points_cles and line.strip():
                assert not line.strip().startswith("- "), f"Tiret non transformé: {line}"
