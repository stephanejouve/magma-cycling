"""Tests unitaires pour le scraper whatsonzwift.com."""

import pytest

from magma_cycling.external.zwift_models import SegmentType, ZwiftCategory
from magma_cycling.external.zwift_scraper import ZwiftWorkoutScraper

# ---------------------------------------------------------------------------
# Fixtures HTML
# ---------------------------------------------------------------------------

WORKOUT_HTML_SIMPLE = """
<html>
<body>
<article>
  <header><h1>Test Workout</h1></header>
  <p><strong>Duration:</strong> 30m</p>
  <p><strong>Stress Score:</strong> 42</p>
  <p>This is a great endurance workout designed to build your aerobic base over time.</p>
  <section>
    <div class="textbar" style="background:#338cff">8min @ 85rpm, from 50 to 75% FTP</div>
    <div class="textbar" style="background:#4dff4d">10min @ 90rpm, 80% FTP</div>
    <div class="textbar" style="background:#ffcc3f">5min @ 95rpm, 100% FTP</div>
    <div class="textbar" style="background:#338cff">5min @ 85rpm, from 75 to 50% FTP</div>
  </section>
  <section>
    <h2>Similar Workouts</h2>
    <div class="textbar">10min @ 80rpm, 60% FTP</div>
  </section>
</article>
<script>var dimensionSport='bike';</script>
</body>
</html>
"""

WORKOUT_HTML_WITH_SECONDS = """
<html>
<body>
<article>
  <header><h1>Sprint Intervals</h1></header>
  <p><strong>Duration:</strong> 20m30s</p>
  <p><strong>Stress Score:</strong> 55</p>
  <section>
    <div class="textbar">5min @ 85rpm, 55% FTP</div>
    <div class="textbar">30sec @ 110rpm, 150% FTP</div>
    <div class="textbar">2min @ 85rpm, 50% FTP</div>
    <div class="textbar">30sec @ 110rpm, 150% FTP</div>
    <div class="textbar">2min @ 85rpm, 50% FTP</div>
    <div class="textbar">5min @ 85rpm, from 60 to 40% FTP</div>
  </section>
</article>
<script>var dimensionSport='bike';</script>
</body>
</html>
"""

WORKOUT_HTML_FREE_RIDE = """
<html>
<body>
<article>
  <header><h1>Free Ride Session</h1></header>
  <p><strong>Duration:</strong> 45m</p>
  <p><strong>Stress Score:</strong> 30</p>
  <section>
    <div class="textbar">5min @ 80rpm, from 40 to 65% FTP</div>
    <div class="textbar">30min free ride</div>
    <div class="textbar">10min @ 80rpm, from 65 to 40% FTP</div>
  </section>
</article>
</body>
</html>
"""

WORKOUT_HTML_NO_ARTICLE = """
<html>
<body>
<h1>Orphan Workout</h1>
<p><strong>Duration:</strong> 10m</p>
<p><strong>Stress Score:</strong> 15</p>
</body>
</html>
"""

WORKOUT_HTML_MISSING_METADATA = """
<html>
<body>
<article>
  <header><h1>Incomplete Workout</h1></header>
  <p>No duration or TSS here.</p>
  <section>
    <div class="textbar">5min 65% FTP</div>
  </section>
</article>
</body>
</html>
"""

LISTING_HTML = """
<html>
<body>
<div>
  <a href="/workouts/30-minutes-to-burn/2-by-2">2 by 2</a>
  <a href="/workouts/30-minutes-to-burn/alpha">Alpha</a>
  <a href="https://whatsonzwift.com/workouts/endurance/foundation">Foundation</a>
  <a href="/about">About</a>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Tests parse_workout_detail
# ---------------------------------------------------------------------------


class TestParseWorkoutDetail:
    """Tests pour parse_workout_detail."""

    def test_basic_parsing(self):
        """Parse un workout complet avec warmup, steady, cooldown."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        assert workout.name == "Test Workout"
        assert workout.duration_minutes == 30
        assert workout.tss == 42
        assert workout.url == "https://whatsonzwift.com/workouts/test/test-workout"

    def test_description_extracted(self):
        """Extrait la description (paragraphe > 40 chars, sans % ni FTP)."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        assert "aerobic base" in workout.description

    def test_segments_count_first_section_only(self):
        """Ne parse que les textbars de la premiere section (pas 'Similar')."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        # 4 segments dans la premiere section, pas 5
        assert len(workout.segments) == 4

    def test_warmup_cooldown_detection(self):
        """Le premier ramp = warmup, le dernier ramp = cooldown."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        assert workout.segments[0].segment_type == SegmentType.WARMUP
        assert workout.segments[-1].segment_type == SegmentType.COOLDOWN

    def test_steady_segments(self):
        """Segments a puissance constante correctement parses."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        # Segment 2: 10min @ 90rpm, 80% FTP
        seg = workout.segments[1]
        assert seg.segment_type == SegmentType.STEADY
        assert seg.duration_seconds == 600
        assert seg.power_low == 80
        assert seg.power_high is None
        assert seg.cadence == 90

    def test_ramp_power_values(self):
        """Ramp: power_low et power_high correctement extraits."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        warmup = workout.segments[0]
        assert warmup.power_low == 50
        assert warmup.power_high == 75

    def test_duration_with_seconds(self):
        """Duree avec secondes (20m30s) arrondie a 21 minutes."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_WITH_SECONDS,
            "https://whatsonzwift.com/workouts/test/sprint",
        )

        assert workout is not None
        assert workout.duration_minutes == 21

    def test_seconds_segment_duration(self):
        """Segment en secondes (30sec) correctement parse."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_WITH_SECONDS,
            "https://whatsonzwift.com/workouts/test/sprint",
        )

        assert workout is not None
        # Segment 2: 30sec @ 110rpm, 150% FTP
        seg = workout.segments[1]
        assert seg.duration_seconds == 30
        assert seg.power_low == 150
        assert seg.segment_type == SegmentType.INTERVAL

    def test_free_ride_segment(self):
        """Segment free ride correctement parse."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_FREE_RIDE,
            "https://whatsonzwift.com/workouts/test/free",
        )

        assert workout is not None
        free_seg = workout.segments[1]
        assert free_seg.segment_type == SegmentType.FREE_RIDE
        assert free_seg.duration_seconds == 1800
        assert free_seg.power_low is None
        assert free_seg.power_high is None

    def test_missing_metadata_returns_none(self):
        """Retourne None si duration ou TSS manquants."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_MISSING_METADATA,
            "https://whatsonzwift.com/workouts/test/incomplete",
        )

        assert workout is None

    def test_no_article_fallback_parsing(self):
        """Sans <article>, parse via fallback h1 et strong globaux."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_NO_ARTICLE,
            "https://whatsonzwift.com/workouts/test/orphan",
        )

        # Le scraper utilise le fallback soup.find("h1") et les <strong> globaux
        assert workout is not None
        assert workout.name == "Orphan Workout"
        assert workout.duration_minutes == 10
        assert workout.tss == 15
        assert len(workout.segments) == 0

    def test_sport_detection(self):
        """Detecte le sport via dimensionSport dans le JS."""
        workout = ZwiftWorkoutScraper.parse_workout_detail(
            WORKOUT_HTML_SIMPLE,
            "https://whatsonzwift.com/workouts/test/test-workout",
        )

        assert workout is not None
        # Le sport n'est pas stocke dans le modele mais parse sans erreur


# ---------------------------------------------------------------------------
# Tests _infer_category
# ---------------------------------------------------------------------------


class TestInferCategory:
    """Tests pour _infer_category."""

    @pytest.mark.parametrize(
        "name,description,expected",
        [
            ("FTP Builder", "Build your FTP threshold", ZwiftCategory.FTP),
            ("VO2 Max Intervals", "Push your VO2max", ZwiftCategory.INTERVALS),
            ("Easy Spin", "Active recovery ride", ZwiftCategory.RECOVERY),
            ("Endurance Base", "Zone 2 base building", ZwiftCategory.ENDURANCE),
            ("Sprint Power", "Explosive sprint efforts", ZwiftCategory.SPRINT),
            ("Hill Climb", "Mountain climbing workout", ZwiftCategory.CLIMBING),
            ("Tempo Ride", "Sustained tempo effort", ZwiftCategory.TEMPO),
            ("Interval Session", "Hard interval repeats", ZwiftCategory.INTERVALS),
            ("Random Workout", "Just a ride", ZwiftCategory.MIXED),
        ],
    )
    def test_category_inference(self, name, description, expected):
        """Infere la bonne categorie depuis le nom et la description."""
        result = ZwiftWorkoutScraper._infer_category(name, description)
        assert result == expected


# ---------------------------------------------------------------------------
# Tests parse_collection_url
# ---------------------------------------------------------------------------


class TestParseCollectionUrl:
    """Tests pour parse_collection_url."""

    def test_absolute_url_unchanged(self):
        """URL absolue retournee telle quelle."""
        url = "https://whatsonzwift.com/workouts/endurance"
        assert ZwiftWorkoutScraper.parse_collection_url(url) == url

    def test_relative_path_with_slash(self):
        """Chemin relatif avec / prefixe."""
        url = "/workouts/endurance"
        result = ZwiftWorkoutScraper.parse_collection_url(url)
        assert result == "https://whatsonzwift.com/workouts/endurance"

    def test_collection_name_only(self):
        """Nom de collection seul."""
        result = ZwiftWorkoutScraper.parse_collection_url("endurance")
        assert result == "https://whatsonzwift.com/workouts/endurance"

    def test_custom_base_url(self):
        """Base URL personnalisee."""
        result = ZwiftWorkoutScraper.parse_collection_url(
            "/workouts/test", base_url="https://custom.com"
        )
        assert result == "https://custom.com/workouts/test"


# ---------------------------------------------------------------------------
# Tests parse_workout_metadata_from_listing
# ---------------------------------------------------------------------------


class TestParseWorkoutMetadataFromListing:
    """Tests pour parse_workout_metadata_from_listing."""

    def test_finds_workout_links(self):
        """Trouve les liens de workouts dans le listing."""
        workouts = ZwiftWorkoutScraper.parse_workout_metadata_from_listing(
            LISTING_HTML, "https://whatsonzwift.com"
        )

        # 3 liens workout valides (pas le lien /about)
        assert len(workouts) == 3

    def test_workout_names(self):
        """Extrait les noms depuis le texte des liens."""
        workouts = ZwiftWorkoutScraper.parse_workout_metadata_from_listing(
            LISTING_HTML, "https://whatsonzwift.com"
        )

        names = [w["name"] for w in workouts]
        assert "2 by 2" in names
        assert "Alpha" in names
        assert "Foundation" in names

    def test_relative_urls_resolved(self):
        """URLs relatives resolues avec le base_url."""
        workouts = ZwiftWorkoutScraper.parse_workout_metadata_from_listing(
            LISTING_HTML, "https://whatsonzwift.com"
        )

        urls = [w["url"] for w in workouts]
        assert "https://whatsonzwift.com/workouts/30-minutes-to-burn/2-by-2" in urls

    def test_absolute_urls_preserved(self):
        """URLs absolues conservees telles quelles."""
        workouts = ZwiftWorkoutScraper.parse_workout_metadata_from_listing(
            LISTING_HTML, "https://whatsonzwift.com"
        )

        urls = [w["url"] for w in workouts]
        assert "https://whatsonzwift.com/workouts/endurance/foundation" in urls

    def test_non_workout_links_excluded(self):
        """Liens hors /workouts/ exclus."""
        workouts = ZwiftWorkoutScraper.parse_workout_metadata_from_listing(
            LISTING_HTML, "https://whatsonzwift.com"
        )

        urls = [w["url"] for w in workouts]
        assert not any("/about" in u for u in urls)


# ---------------------------------------------------------------------------
# Tests _parse_segments_from_soup (via parse_workout_detail)
# ---------------------------------------------------------------------------


class TestParseSegments:
    """Tests pour _parse_segments_from_soup."""

    def test_recovery_zone_classification(self):
        """Puissance <= 55% FTP classee en recovery."""
        html = """
        <html><body><article>
          <header><h1>Recovery</h1></header>
          <p><strong>Duration:</strong> 10m</p>
          <p><strong>Stress Score:</strong> 5</p>
          <section>
            <div class="textbar">10min @ 80rpm, 45% FTP</div>
          </section>
        </article></body></html>
        """
        workout = ZwiftWorkoutScraper.parse_workout_detail(html, "http://test/recovery")

        assert workout is not None
        assert workout.segments[0].segment_type == SegmentType.RECOVERY

    def test_interval_classification_above_threshold(self):
        """Puissance > 105% FTP classee en interval."""
        html = """
        <html><body><article>
          <header><h1>Intervals</h1></header>
          <p><strong>Duration:</strong> 5m</p>
          <p><strong>Stress Score:</strong> 20</p>
          <section>
            <div class="textbar">5min @ 100rpm, 120% FTP</div>
          </section>
        </article></body></html>
        """
        workout = ZwiftWorkoutScraper.parse_workout_detail(html, "http://test/intervals")

        assert workout is not None
        assert workout.segments[0].segment_type == SegmentType.INTERVAL

    def test_empty_section_returns_empty_segments(self):
        """Section sans textbars retourne une liste vide de segments."""
        html = """
        <html><body><article>
          <header><h1>Empty</h1></header>
          <p><strong>Duration:</strong> 10m</p>
          <p><strong>Stress Score:</strong> 10</p>
          <section></section>
        </article></body></html>
        """
        workout = ZwiftWorkoutScraper.parse_workout_detail(html, "http://test/empty")

        assert workout is not None
        assert len(workout.segments) == 0

    def test_unparseable_textbar_skipped(self):
        """Textbar au format inconnu ignore sans crash."""
        html = """
        <html><body><article>
          <header><h1>Mixed</h1></header>
          <p><strong>Duration:</strong> 15m</p>
          <p><strong>Stress Score:</strong> 20</p>
          <section>
            <div class="textbar">5min @ 90rpm, 75% FTP</div>
            <div class="textbar">something weird here</div>
            <div class="textbar">5min @ 85rpm, 65% FTP</div>
          </section>
        </article></body></html>
        """
        workout = ZwiftWorkoutScraper.parse_workout_detail(html, "http://test/mixed")

        assert workout is not None
        assert len(workout.segments) == 2

    def test_cadence_optional(self):
        """Cadence absente acceptee (None)."""
        html = """
        <html><body><article>
          <header><h1>No Cadence</h1></header>
          <p><strong>Duration:</strong> 10m</p>
          <p><strong>Stress Score:</strong> 15</p>
          <section>
            <div class="textbar">10min 70% FTP</div>
          </section>
        </article></body></html>
        """
        workout = ZwiftWorkoutScraper.parse_workout_detail(html, "http://test/no-cad")

        assert workout is not None
        assert workout.segments[0].cadence is None
        assert workout.segments[0].power_low == 70
