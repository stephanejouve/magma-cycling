"""Tests for analysis.baseline.pattern_analysis module.

Tests PatternAnalysisMixin : skip reasons clustering, day-of-week patterns, workout type patterns.
"""

from magma_cycling.analysis.baseline.pattern_analysis import PatternAnalysisMixin


class StubAnalyzer(PatternAnalysisMixin):
    """Stub providing PatternAnalysisMixin for isolated testing."""

    pass


class TestAnalyzeSkipReasons:
    """Tests for analyze_skip_reasons()."""

    def setup_method(self):
        self.analyzer = StubAnalyzer()

    def test_empty_sessions(self):
        result = self.analyzer.analyze_skip_reasons([])
        assert result["total"] == 0
        assert result["categories"] == {}
        assert result["distribution"] == {}

    def test_work_schedule_reason(self):
        sessions = [{"reason": "Too late from work", "date": "2026-03-01", "name": "S081-05"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert result["total"] == 1
        assert "work_schedule" in result["distribution"]
        assert result["distribution"]["work_schedule"]["count"] == 1

    def test_health_reason(self):
        sessions = [{"reason": "Fatigue accumulée", "date": "2026-03-02", "name": "S081-03"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert "health" in result["distribution"]

    def test_mechanics_reason(self):
        sessions = [
            {"reason": "Bike issue trainer broken", "date": "2026-03-03", "name": "S081-04"}
        ]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert "mechanics" in result["distribution"]

    def test_weather_reason(self):
        sessions = [{"reason": "Heavy rain all day", "date": "2026-03-04", "name": "S081-02"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert "weather" in result["distribution"]

    def test_personal_reason(self):
        sessions = [{"reason": "Family emergency", "date": "2026-03-05", "name": "S081-06"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert "personal" in result["distribution"]

    def test_uncategorized_reason(self):
        sessions = [{"reason": "No particular reason", "date": "2026-03-06", "name": "S081-07"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert "other" in result["distribution"]

    def test_multiple_categories(self):
        sessions = [
            {"reason": "Too late from work", "date": "2026-03-01", "name": "S081-01"},
            {"reason": "Fatigue", "date": "2026-03-02", "name": "S081-02"},
            {"reason": "Heavy rain", "date": "2026-03-03", "name": "S081-03"},
        ]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert result["total"] == 3
        assert len(result["distribution"]) == 3

    def test_percentage_calculation(self):
        sessions = [
            {"reason": "Work meeting", "date": "2026-03-01", "name": "S081-01"},
            {"reason": "Office deadline", "date": "2026-03-02", "name": "S081-02"},
        ]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert result["distribution"]["work_schedule"]["percentage"] == 100.0

    def test_missing_reason_field(self):
        sessions = [{"date": "2026-03-01", "name": "S081-01"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        assert result["total"] == 1
        assert "other" in result["distribution"]

    def test_categories_contain_session_details(self):
        sessions = [{"reason": "Sick day", "date": "2026-03-01", "name": "S081-01"}]
        result = self.analyzer.analyze_skip_reasons(sessions)
        health_items = result["categories"]["health"]
        assert len(health_items) == 1
        assert health_items[0]["date"] == "2026-03-01"
        assert health_items[0]["reason"] == "Sick day"


class TestAnalyzeDayOfWeekPatterns:
    """Tests for analyze_day_of_week_patterns()."""

    def setup_method(self):
        self.analyzer = StubAnalyzer()

    def test_empty_patterns(self):
        result = self.analyzer.analyze_day_of_week_patterns({})
        assert result["days"] == {}
        assert result["high_risk_days"] == []
        assert result["recommendations"] == []

    def test_perfect_adherence(self):
        patterns = {"Monday": {"planned": 5, "completed": 5}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert result["days"]["Monday"]["adherence_rate"] == 1.0
        assert result["days"]["Monday"]["risk_score"] == 0.0
        assert result["days"]["Monday"]["risk_level"] == "LOW"

    def test_zero_adherence_critical_risk(self):
        patterns = {"Friday": {"planned": 5, "completed": 0}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert result["days"]["Friday"]["risk_score"] == 100.0
        assert result["days"]["Friday"]["risk_level"] == "CRITICAL"

    def test_moderate_risk(self):
        patterns = {"Wednesday": {"planned": 10, "completed": 7}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert result["days"]["Wednesday"]["risk_level"] == "MODERATE"

    def test_high_risk_day_detected(self):
        patterns = {"Thursday": {"planned": 10, "completed": 4}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert len(result["high_risk_days"]) == 1
        assert result["high_risk_days"][0]["day"] == "Thursday"

    def test_high_risk_days_sorted_by_risk(self):
        patterns = {
            "Monday": {"planned": 10, "completed": 5},
            "Friday": {"planned": 10, "completed": 2},
        }
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert len(result["high_risk_days"]) == 2
        assert result["high_risk_days"][0]["day"] == "Friday"

    def test_recommendations_generated_for_critical(self):
        patterns = {"Friday": {"planned": 10, "completed": 2}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert len(result["recommendations"]) > 0
        assert "CRITICAL" in result["recommendations"][0]

    def test_recommendations_generated_for_high(self):
        patterns = {"Wednesday": {"planned": 10, "completed": 5}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert len(result["recommendations"]) > 0
        assert "HIGH" in result["recommendations"][0]

    def test_zero_planned_no_crash(self):
        patterns = {"Sunday": {"planned": 0, "completed": 0}}
        result = self.analyzer.analyze_day_of_week_patterns(patterns)
        assert result["days"]["Sunday"]["adherence_rate"] == 0
        assert result["days"]["Sunday"]["risk_score"] == 100.0


class TestAnalyzeWorkoutTypePatterns:
    """Tests for analyze_workout_type_patterns()."""

    def setup_method(self):
        self.analyzer = StubAnalyzer()

    def test_empty_sessions(self):
        result = self.analyzer.analyze_workout_type_patterns([], [])
        assert result["types"] == {}
        assert result["high_risk_types"] == []

    def test_single_type_all_completed(self):
        all_sessions = [
            {"name": "S081-01-END-Endurance-V001"},
            {"name": "S081-03-END-Endurance-V001"},
        ]
        completed = [
            {"name": "S081-01-END-Endurance-V001"},
            {"name": "S081-03-END-Endurance-V001"},
        ]
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert "END" in result["types"]
        assert result["types"]["END"]["adherence_rate"] == 1.0

    def test_mixed_types(self):
        all_sessions = [
            {"name": "S081-01-END-Endurance-V001"},
            {"name": "S081-03-INT-Intervals-V001"},
            {"name": "S081-05-REC-Recovery-V001"},
        ]
        completed = [
            {"name": "S081-01-END-Endurance-V001"},
            {"name": "S081-05-REC-Recovery-V001"},
        ]
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert len(result["types"]) == 3
        assert result["types"]["END"]["completed"] == 1
        assert result["types"]["INT"]["completed"] == 0
        assert result["types"]["REC"]["completed"] == 1

    def test_high_risk_type_detected(self):
        all_sessions = [
            {"name": "S081-01-INT-Intervals-V001"},
            {"name": "S081-03-INT-Intervals-V001"},
            {"name": "S081-05-INT-Intervals-V001"},
        ]
        completed = []
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert len(result["high_risk_types"]) == 1
        assert result["high_risk_types"][0]["type"] == "INT"

    def test_status_tags_stripped(self):
        all_sessions = [
            {"name": "[SAUTÉE] S081-01-INT-Intervals-V001"},
            {"name": "[ANNULÉE] S081-03-END-Endurance-V001"},
        ]
        completed = []
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert "INT" in result["types"]
        assert "END" in result["types"]

    def test_no_matching_pattern_skipped(self):
        all_sessions = [{"name": "RandomName"}]
        completed = []
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert len(result["types"]) == 0

    def test_recommendations_for_critical_type(self):
        all_sessions = [
            {"name": "S081-01-CAD-Cadence-V001"},
            {"name": "S081-03-CAD-Cadence-V001"},
        ]
        completed = []
        result = self.analyzer.analyze_workout_type_patterns(completed, all_sessions)
        assert len(result["recommendations"]) > 0
        assert "CRITICAL" in result["recommendations"][0]
