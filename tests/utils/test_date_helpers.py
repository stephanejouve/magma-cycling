"""
Tests for date calculation utilities.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import json

import pytest

from magma_cycling.utils.date_helpers import extract_day_number


class TestExtractDayNumber:
    """Test extract_day_number function."""

    @pytest.fixture
    def temp_planning_dir(self, tmp_path):
        """Create temporary planning directory."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir(exist_ok=True)
        return planning_dir

    @pytest.fixture
    def create_planning_file(self, temp_planning_dir):
        """Factory fixture to create planning files."""

        def _create(week_id: str, start_date: str):
            planning_file = temp_planning_dir / f"week_planning_{week_id}.json"
            planning_data = {
                "week_id": week_id,
                "start_date": start_date,
                "end_date": "2025-12-21",
                "sessions": [],
            }
            with open(planning_file, "w", encoding="utf-8") as f:
                json.dump(planning_data, f)
            return planning_file

        return _create

    def test_extract_day_number_monday(self, temp_planning_dir, create_planning_file):
        """Test extracting day number for Monday (day 1)."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("2025-12-15", "S072", temp_planning_dir)

        assert result == 1

    def test_extract_day_number_wednesday(self, temp_planning_dir, create_planning_file):
        """Test extracting day number for Wednesday (day 3)."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("2025-12-17", "S072", temp_planning_dir)

        assert result == 3

    def test_extract_day_number_sunday(self, temp_planning_dir, create_planning_file):
        """Test extracting day number for Sunday (day 7)."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("2025-12-21", "S072", temp_planning_dir)

        assert result == 7

    def test_extract_day_number_different_week(self, temp_planning_dir, create_planning_file):
        """Test with different week."""
        create_planning_file("S073", "2025-12-22")

        result = extract_day_number("2025-12-24", "S073", temp_planning_dir)

        assert result == 3  # Wednesday

    def test_extract_day_number_file_not_found(self, temp_planning_dir):
        """Test when planning file doesn't exist."""
        result = extract_day_number("2025-12-15", "S999", temp_planning_dir)

        assert result == 1  # Fallback

    def test_extract_day_number_invalid_date_format(self, temp_planning_dir, create_planning_file):
        """Test with invalid date format."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("invalid-date", "S072", temp_planning_dir)

        assert result == 1  # Fallback

    def test_extract_day_number_missing_start_date_key(self, temp_planning_dir, tmp_path):
        """Test when planning file missing start_date key."""
        planning_file = temp_planning_dir / "week_planning_S072.json"
        planning_data = {
            "week_id": "S072",
            # Missing start_date
            "sessions": [],
        }
        with open(planning_file, "w", encoding="utf-8") as f:
            json.dump(planning_data, f)

        result = extract_day_number("2025-12-15", "S072", temp_planning_dir)

        assert result == 1  # Fallback

    def test_extract_day_number_invalid_json(self, temp_planning_dir):
        """Test with invalid JSON in planning file."""
        planning_file = temp_planning_dir / "week_planning_S072.json"
        with open(planning_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json ")

        result = extract_day_number("2025-12-15", "S072", temp_planning_dir)

        assert result == 1  # Fallback

    def test_extract_day_number_negative_delta(self, temp_planning_dir, create_planning_file):
        """Test with date before week start (negative delta)."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("2025-12-14", "S072", temp_planning_dir)

        assert result == 0  # delta + 1 = -1 + 1 = 0

    def test_extract_day_number_far_future_date(self, temp_planning_dir, create_planning_file):
        """Test with date far in the future."""
        create_planning_file("S072", "2025-12-15")

        result = extract_day_number("2025-12-30", "S072", temp_planning_dir)

        assert result == 16  # 15 days delta + 1

    def test_extract_day_number_leap_year(self, temp_planning_dir, create_planning_file):
        """Test with leap year date."""
        create_planning_file("S009", "2024-02-26")  # 2024 is leap year

        result = extract_day_number("2024-02-29", "S009", temp_planning_dir)

        assert result == 4  # 3 days delta + 1

    def test_extract_day_number_year_boundary(self, temp_planning_dir, create_planning_file):
        """Test across year boundary."""
        create_planning_file("S052", "2025-12-29")

        result = extract_day_number("2026-01-01", "S052", temp_planning_dir)

        assert result == 4  # 3 days delta + 1
