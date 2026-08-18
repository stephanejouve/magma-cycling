"""BT-050 : distribution d'intensité par zone via streams temps-réel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from magma_cycling.analyzers.intensity_zones import (
    FTP_PALIERS,
    ZONE_BOUNDS,
    bucket_watts_by_zones,
    ftp_at,
    intensity_distribution_from_activities,
)


class TestFtpAt:
    """``ftp_at`` retourne la FTP en vigueur à une date d'activité."""

    def test_after_second_palier_returns_226(self):
        """Date post-2026-03-28 → 226W (dernier palier)."""
        assert ftp_at("2026-05-01") == 226
        assert ftp_at("2026-06-29") == 226
        assert ftp_at("2026-08-18") == 226

    def test_between_paliers_returns_first(self):
        """Date entre 2025-08-23 et 2026-03-28 → 223W (1er palier)."""
        assert ftp_at("2025-11-15") == 223
        assert ftp_at("2026-01-01") == 223
        assert ftp_at("2026-03-27") == 223

    def test_exact_palier_date_returns_that_palier(self):
        """Date exacte du palier → cette valeur (borne inclusive)."""
        assert ftp_at("2025-08-23") == 223
        assert ftp_at("2026-03-28") == 226

    def test_before_first_palier_returns_first_with_reservation(self):
        """Date pré-2025-08-23 → 1er palier par défaut (réserve documentée)."""
        assert ftp_at("2025-08-22") == 223
        assert ftp_at("2025-01-01") == 223

    def test_paliers_constant_shape(self):
        """Sanity check : FTP_PALIERS est bien ordonné chronologiquement."""
        dates = [p[0] for p in FTP_PALIERS]
        assert dates == sorted(dates), "FTP_PALIERS must be chronologically sorted"


class TestBucketWattsByZones:
    """``bucket_watts_by_zones`` classe chaque seconde en Z1-Z5."""

    def test_all_none_falls_in_z1(self):
        """Une session 100 % pause (None) → tout en Z1."""
        watts = [None] * 60
        counts = bucket_watts_by_zones(watts, ftp=200)
        assert counts == {"z1": 60, "z2": 0, "z3": 0, "z4": 0, "z5": 0}

    def test_all_zero_falls_in_z1(self):
        """Watts=0 traité comme Z1 (bornes 0.00-0.55)."""
        watts = [0] * 60
        counts = bucket_watts_by_zones(watts, ftp=200)
        assert counts == {"z1": 60, "z2": 0, "z3": 0, "z4": 0, "z5": 0}

    def test_z2_endurance(self):
        """Watts constants à 60 % FTP → tout en Z2 (0.55-0.75)."""
        watts = [int(200 * 0.60)] * 100  # 120W à FTP 200 = 60 %
        counts = bucket_watts_by_zones(watts, ftp=200)
        assert counts["z2"] == 100
        assert sum(counts.values()) == 100

    def test_z5_vo2max(self):
        """Watts à 100 % FTP → tout en Z5 (0.95-inf)."""
        watts = [200] * 30  # 200W à FTP 200 = 100 %
        counts = bucket_watts_by_zones(watts, ftp=200)
        assert counts["z5"] == 30

    def test_mixed_intervals(self):
        """Mix Z2 endurance + Z5 sprints → bucket propre."""
        # 60s à 120W (Z2) + 30s à 200W (Z5) + 60s à 120W (Z2)
        watts = [120] * 60 + [200] * 30 + [120] * 60
        counts = bucket_watts_by_zones(watts, ftp=200)
        assert counts["z2"] == 120
        assert counts["z5"] == 30
        assert sum(counts.values()) == 150

    def test_z3_z4_boundaries(self):
        """Bornes Z3 (0.75-0.85) et Z4 (0.85-0.95) précises."""
        # 200W FTP → 150W = 0.75 (borne basse Z3), 170W = 0.85 (borne Z4)
        watts = [150] * 10 + [160] * 10 + [170] * 10 + [180] * 10 + [190] * 10
        counts = bucket_watts_by_zones(watts, ftp=200)
        # 150 → pct 0.75 → Z3 (borne inclusive)
        # 160 → 0.80 → Z3
        # 170 → 0.85 → Z4 (borne inclusive)
        # 180 → 0.90 → Z4
        # 190 → 0.95 → Z5 (borne inclusive Z5)
        assert counts["z3"] == 20  # 150 + 160
        assert counts["z4"] == 20  # 170 + 180
        assert counts["z5"] == 10  # 190

    def test_zero_ftp_defensive_all_z1(self):
        """FTP=0 (invalide) → tout en Z1 (fallback conservateur)."""
        watts = [100] * 50
        counts = bucket_watts_by_zones(watts, ftp=0)
        assert counts["z1"] == 50
        assert sum(counts.values()) == 50

    def test_invariant_sum_equals_length(self):
        """Invariant : somme des zones = len(watts)."""
        import random

        random.seed(42)
        watts = [random.randint(0, 350) for _ in range(1000)]
        counts = bucket_watts_by_zones(watts, ftp=226)
        assert sum(counts.values()) == 1000


class TestIntensityDistributionFromActivities:
    """``intensity_distribution_from_activities`` agrège en temps + %."""

    def _mock_client(self, streams_by_id: dict[str, list]) -> MagicMock:
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            return streams_by_id.get(activity_id, [])

        client.get_activity_streams.side_effect = _fake_streams
        return client

    def test_empty_activities_returns_zeros(self):
        """Liste vide → total_seconds=0, tous pcts à 0."""
        client = self._mock_client({})
        result = intensity_distribution_from_activities([], client)
        assert result["total_seconds"] == 0
        assert result["z1_seconds"] == 0
        assert result["z1_pct"] == 0.0
        assert result["z5_pct"] == 0.0

    def test_single_endurance_activity_z2_dominant(self):
        """Une activité 100 % Z2 → z2_pct = 100 %."""
        client = self._mock_client(
            {
                "i111": [
                    {"type": "time", "data": list(range(3600))},
                    {"type": "watts", "data": [130] * 3600},  # 130W ≈ 58 % de 223 = Z2
                ],
            }
        )
        activities = [
            {"id": "i111", "start_date_local": "2025-11-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["total_seconds"] == 3600
        assert result["z2_seconds"] == 3600
        assert result["z2_pct"] == 100.0
        assert result["z1_pct"] == 0.0

    def test_mixed_activities_aggregation(self):
        """2 activités : 1h Z2 + 30 min mix Z1/Z5 → agrégat propre."""
        client = self._mock_client(
            {
                "i222": [
                    {"type": "watts", "data": [130] * 3600},  # 1h Z2 à FTP 223
                ],
                "i333": [
                    {
                        "type": "watts",
                        # 900s Z1 (30W) + 900s Z5 (230W)
                        "data": [30] * 900 + [230] * 900,
                    },
                ],
            }
        )
        activities = [
            {"id": "i222", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i333", "start_date_local": "2025-11-16T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        # 3600 Z2 + 900 Z1 + 900 Z5 = 5400 s
        assert result["total_seconds"] == 5400
        assert result["z1_seconds"] == 900
        assert result["z2_seconds"] == 3600
        assert result["z5_seconds"] == 900
        # 900 / 5400 = 16.666... → arrondi 16.7
        assert result["z1_pct"] == 16.7
        # 3600 / 5400 = 66.666... → 66.7
        assert result["z2_pct"] == 66.7

    def test_ftp_historique_applied_per_activity(self):
        """FTP différente selon date d'activité (223 pré-2026-03-28, 226 après)."""
        client = self._mock_client(
            {
                "i_old": [
                    # 150W à FTP 223 → pct 0.673 → Z2
                    {"type": "watts", "data": [150] * 100},
                ],
                "i_new": [
                    # 150W à FTP 226 → pct 0.664 → Z2 aussi
                    # Choisir un W qui bascule : 170W à FTP 223 = 0.762 (Z3),
                    # 170W à FTP 226 = 0.752 (Z3 aussi, borne 0.75)
                    # 168W : 223 → 0.753 Z3, 226 → 0.743 Z2 — bascule !
                    {"type": "watts", "data": [168] * 100},
                ],
            }
        )
        activities = [
            {"id": "i_old", "start_date_local": "2026-01-15T10:00:00"},
            {"id": "i_new", "start_date_local": "2026-06-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        # i_old: 150W/223 = 0.673 → Z2 (100s)
        # i_new: 168W/226 = 0.743 → Z2 (100s)
        # Total : 200s en Z2
        assert result["z2_seconds"] == 200

    def test_activity_without_watts_stream_skipped(self):
        """Activité sans stream watts (Zwift libre ?) → skip sans crash."""
        client = self._mock_client(
            {
                "i_ok": [{"type": "watts", "data": [130] * 60}],
                "i_no_watts": [{"type": "heartrate", "data": [140] * 60}],
            }
        )
        activities = [
            {"id": "i_ok", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i_no_watts", "start_date_local": "2025-11-16T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        # Seul i_ok contribue
        assert result["total_seconds"] == 60

    def test_activity_fetch_error_skipped_defensively(self):
        """API error sur un fetch → skip, ne casse pas l'agrégat."""
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            if activity_id == "i_flaky":
                raise Exception("429 rate limit")
            return [{"type": "watts", "data": [130] * 60}]

        client.get_activity_streams.side_effect = _fake_streams
        activities = [
            {"id": "i_ok", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i_flaky", "start_date_local": "2025-11-16T10:00:00"},
            {"id": "i_ok2", "start_date_local": "2025-11-17T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        # 2 activités OK × 60s = 120 (flaky skippée)
        assert result["total_seconds"] == 120

    def test_activity_without_id_or_date_skipped(self):
        """Data corrompue (id ou date manquante) → skip."""
        client = self._mock_client({"i111": [{"type": "watts", "data": [130] * 60}]})
        activities = [
            {"start_date_local": "2025-11-15T10:00:00"},  # pas d'id
            {"id": "i222"},  # pas de date
            {"id": "i111", "start_date_local": "2025-11-16T10:00:00"},  # OK
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["total_seconds"] == 60

    def test_exposes_zone_bounds_for_verification(self):
        """BT-050 v2 : zone_bounds présents dans le payload (Coach AI 2026-08-18).

        Sans ces bornes, aucune distribution rétrospective n'est vérifiable
        depuis le MCP. Exposition obligatoire pour audit indépendant.
        """
        client = self._mock_client(
            {"i111": [{"type": "watts", "data": [130] * 60}]},
        )
        activities = [{"id": "i111", "start_date_local": "2025-11-15T10:00:00"}]
        result = intensity_distribution_from_activities(activities, client)
        assert "zone_bounds" in result
        bounds = result["zone_bounds"]
        assert set(bounds.keys()) == {"z1", "z2", "z3", "z4", "z5"}
        # Z1 : [0.00, 0.55]
        assert bounds["z1"] == [0.00, 0.55]
        # Z5 : [0.95, None] — la borne haute infinity est sérialisée en None
        assert bounds["z5"][0] == 0.95
        assert bounds["z5"][1] is None

    def test_exposes_ftp_by_activity_for_audit(self):
        """BT-050 v2 : ftp_by_activity présent pour vérif FTP historique appliquée.

        Coach AI 2026-08-18 : « si le calcul utilise la FTP courante, la
        répartition historique est faussée — décalage vers le bas des zones ».
        Le mapping ``{activity_id: ftp_utilisée}`` permet à l'opérateur de
        vérifier que la FTP historique est bien appliquée par date.
        """
        client = self._mock_client(
            {
                "i_old": [{"type": "watts", "data": [130] * 60}],
                "i_new": [{"type": "watts", "data": [130] * 60}],
            }
        )
        activities = [
            # 2025-11-15 → palier 223W
            {"id": "i_old", "start_date_local": "2025-11-15T10:00:00"},
            # 2026-06-15 → palier 226W
            {"id": "i_new", "start_date_local": "2026-06-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert "ftp_by_activity" in result
        assert result["ftp_by_activity"]["i_old"] == 223
        assert result["ftp_by_activity"]["i_new"] == 226

    def test_ftp_by_activity_excludes_skipped_activities(self):
        """Une activité skippée (fetch error, no watts) n'apparaît pas
        dans ``ftp_by_activity`` — le mapping reflète les activités
        effectivement utilisées."""
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            if activity_id == "i_flaky":
                raise Exception("429")
            return [{"type": "watts", "data": [130] * 60}]

        client.get_activity_streams.side_effect = _fake_streams
        activities = [
            {"id": "i_ok", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i_flaky", "start_date_local": "2025-11-16T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert "i_ok" in result["ftp_by_activity"]
        assert "i_flaky" not in result["ftp_by_activity"]


class TestBT059DisambiguateCacheMissFromZero:
    """BT-059 : distinguer « total_seconds=0 aucun temps réalisé » de
    « total_seconds=0 toutes activités échouées au fetch ».

    Nit remonté par Admin sur S106 preprod (post-backfill BT-025 partiel) :
    cache miss silencieux → total_seconds=0 ambigu. Fix via ``activities_
    considered`` + ``skipped_activities`` avec raison typée.
    """

    def test_all_ok_no_skips(self):
        """Cas nominal : aucune activité skippée, activities_considered=N."""
        client = MagicMock()
        client.get_activity_streams.return_value = [{"type": "watts", "data": [130] * 60}]
        activities = [
            {"id": "i_ok1", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i_ok2", "start_date_local": "2025-11-16T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["activities_considered"] == 2
        assert result["skipped_activities"] == []
        assert result["total_seconds"] == 120

    def test_fetch_failed_captured_with_error_and_reason(self):
        """Fetch error → skipped avec reason=fetch_failed + error tronqué."""
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            raise Exception("429 rate limit exceeded")

        client.get_activity_streams.side_effect = _fake_streams
        activities = [
            {"id": "i_flaky", "start_date_local": "2025-11-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["activities_considered"] == 1
        assert len(result["skipped_activities"]) == 1
        skipped = result["skipped_activities"][0]
        assert skipped["id"] == "i_flaky"
        assert skipped["date"] == "2025-11-15"
        assert skipped["reason"] == "fetch_failed"
        assert "Exception" in skipped["error"]
        assert "429" in skipped["error"]

    def test_no_watts_stream_reason(self):
        """Streams reçus mais pas de type watts → reason=no_watts_stream."""
        client = MagicMock()
        client.get_activity_streams.return_value = [
            {"type": "heartrate", "data": [140] * 60},
        ]
        activities = [
            {"id": "i_hr_only", "start_date_local": "2025-11-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert len(result["skipped_activities"]) == 1
        assert result["skipped_activities"][0]["reason"] == "no_watts_stream"

    def test_empty_watts_data_reason(self):
        """Stream watts présent mais data vide → reason=empty_watts_data."""
        client = MagicMock()
        client.get_activity_streams.return_value = [{"type": "watts", "data": []}]
        activities = [
            {"id": "i_empty", "start_date_local": "2025-11-15T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert len(result["skipped_activities"]) == 1
        assert result["skipped_activities"][0]["reason"] == "empty_watts_data"

    def test_invalid_metadata_reason(self):
        """Activité sans id ou date → reason=invalid_metadata."""
        client = MagicMock()
        activities = [
            {"start_date_local": "2025-11-15T10:00:00"},  # sans id
            {"id": "i_no_date"},  # sans date
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["activities_considered"] == 2
        assert len(result["skipped_activities"]) == 2
        for s in result["skipped_activities"]:
            assert s["reason"] == "invalid_metadata"

    def test_prod_scenario_cache_miss_all_failed_disambiguable(self):
        """Cas prod S106 remonté par Admin : cache miss sur toutes les activités.

        Après fix : le consommateur voit ``activities_considered=N`` +
        ``skipped_activities=N (all fetch_failed)`` + ``total_seconds=0``,
        distinguable de « aucun temps réalisé » (skipped=[], total=0).
        """
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            raise Exception("cache miss + API 502")

        client.get_activity_streams.side_effect = _fake_streams
        activities = [
            {"id": "i_a", "start_date_local": "2026-08-10T10:00:00"},
            {"id": "i_b", "start_date_local": "2026-08-11T10:00:00"},
            {"id": "i_c", "start_date_local": "2026-08-12T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        # Diagnostic : 3 considérées, 3 skippées avec raison fetch_failed
        assert result["activities_considered"] == 3
        assert len(result["skipped_activities"]) == 3
        assert all(s["reason"] == "fetch_failed" for s in result["skipped_activities"])
        # Distinguable de « aucun temps réalisé » (skipped=[])
        assert result["total_seconds"] == 0

    def test_partial_skips_do_not_break_aggregation(self):
        """Mix : 1 activité OK + 1 fetch_failed + 1 no_watts → agrégat sur les OK,
        skipped tracé pour les 2 autres."""
        client = MagicMock()

        def _fake_streams(activity_id, **kwargs):
            if activity_id == "i_ok":
                return [{"type": "watts", "data": [130] * 60}]
            if activity_id == "i_flaky":
                raise Exception("timeout")
            return [{"type": "heartrate", "data": [140] * 60}]  # i_no_watts

        client.get_activity_streams.side_effect = _fake_streams
        activities = [
            {"id": "i_ok", "start_date_local": "2025-11-15T10:00:00"},
            {"id": "i_flaky", "start_date_local": "2025-11-16T10:00:00"},
            {"id": "i_no_watts", "start_date_local": "2025-11-17T10:00:00"},
        ]
        result = intensity_distribution_from_activities(activities, client)
        assert result["activities_considered"] == 3
        assert result["total_seconds"] == 60  # seul i_ok agrégé
        assert len(result["skipped_activities"]) == 2
        reasons = {s["reason"] for s in result["skipped_activities"]}
        assert reasons == {"fetch_failed", "no_watts_stream"}

    def test_error_field_truncated_to_200_chars(self):
        """Error tronqué à 200 chars pour éviter les leaks (URL, body HTTP)."""
        client = MagicMock()
        long_error_msg = "A" * 500

        def _fake_streams(activity_id, **kwargs):
            raise Exception(long_error_msg)

        client.get_activity_streams.side_effect = _fake_streams
        activities = [{"id": "i", "start_date_local": "2025-11-15T10:00:00"}]
        result = intensity_distribution_from_activities(activities, client)
        skipped = result["skipped_activities"][0]
        # "Exception: " prefix (11 chars) + jusqu'à 200 chars du message
        assert len(skipped["error"]) <= 11 + 200


class TestZoneBoundsSanity:
    """Sanity checks sur les bornes ZONE_BOUNDS (invariants doctrinaux)."""

    def test_all_5_zones_present(self):
        assert set(ZONE_BOUNDS.keys()) == {"z1", "z2", "z3", "z4", "z5"}

    def test_bounds_contiguous_no_gap(self):
        """Les bornes doivent former une partition ininterrompue de [0, inf)."""
        sorted_zones = ["z1", "z2", "z3", "z4", "z5"]
        prev_hi = 0.0
        for z in sorted_zones:
            lo, hi = ZONE_BOUNDS[z]
            assert (
                lo == prev_hi
            ), f"gap detected between {z} et prev (prev_hi={prev_hi}, {z}.lo={lo})"
            prev_hi = hi
        assert prev_hi == float("inf"), "Z5 must extend to infinity"


@pytest.fixture(autouse=True)
def _fast_test(monkeypatch):
    """Neutralise tout éventuel sleep dans le code testé (pas attendu ici mais safe)."""
    monkeypatch.setattr("time.sleep", lambda _: None)
