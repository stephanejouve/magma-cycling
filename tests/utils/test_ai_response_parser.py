"""
Tests for AI response parser utilities.

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

from magma_cycling.utils.ai_response_parser import parse_ai_modifications


class TestParseAIModifications:
    """Test parse_ai_modifications function."""

    def test_parse_json_in_markdown_code_block(self):
        """Test parsing JSON from markdown code block."""
        ai_response = """
Here are the modifications:

```json
{
  "modifications": [
    {"action": "lighten", "date": "2026-03-05", "percentage": 20}
  ]
}
```

That's all!
"""
        result = parse_ai_modifications(ai_response)

        assert len(result) == 1
        assert result[0]["action"] == "lighten"
        assert result[0]["date"] == "2026-03-05"
        assert result[0]["percentage"] == 20

    def test_parse_json_without_markdown(self):
        """Test parsing plain JSON without markdown."""
        ai_response = """
{"modifications": [{"action": "replace", "date": "2026-03-06", "code": "END-Test"}]}
"""
        result = parse_ai_modifications(ai_response)

        assert len(result) == 1
        assert result[0]["action"] == "replace"

    def test_parse_multiple_modifications(self):
        """Test parsing multiple modifications."""
        ai_response = """
```json
{
  "modifications": [
    {"action": "lighten", "date": "2026-03-05", "percentage": 20},
    {"action": "cancel", "date": "2026-03-06", "reason": "Fatigue"},
    {"action": "replace", "date": "2026-03-07", "code": "END-Recovery"}
  ]
}
```
"""
        result = parse_ai_modifications(ai_response)

        assert len(result) == 3
        assert result[0]["action"] == "lighten"
        assert result[1]["action"] == "cancel"
        assert result[2]["action"] == "replace"

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        result = parse_ai_modifications("")

        assert result == []

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only response."""
        result = parse_ai_modifications("   \n\n   ")

        assert result == []

    def test_parse_no_modifications_key(self):
        """Test parsing JSON without modifications key."""
        ai_response = """
```json
{
  "status": "ok",
  "message": "No changes needed"
}
```
"""
        result = parse_ai_modifications(ai_response)

        assert result == []

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        ai_response = """
```json
{
  "modifications": [
    {"action": "lighten", "date": "2026-03-05"
  ]
}
```
"""
        result = parse_ai_modifications(ai_response)

        assert result == []

    def test_parse_modifications_not_list(self):
        """Test when modifications is not a list."""
        ai_response = """
```json
{
  "modifications": "should be a list"
}
```
"""
        result = parse_ai_modifications(ai_response)

        assert result == []

    def test_parse_whitespace_variations(self):
        """Test parsing with various whitespace."""
        ai_response = """
```json

{
    "modifications"  :  [
        {
            "action"  :  "lighten"  ,
            "date"  :  "2026-03-05"  ,
            "percentage"  :  20
        }
    ]
}

```
"""
        result = parse_ai_modifications(ai_response)

        assert len(result) == 1
        assert result[0]["action"] == "lighten"

    def test_parse_no_json_found(self):
        """Test when no JSON structure is found."""
        ai_response = "This is just plain text without any JSON."

        result = parse_ai_modifications(ai_response)

        assert result == []
