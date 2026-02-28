"""Report validators module.

Validates generated report content for quality and correctness.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from magma_cycling.reports.validators.markdown_validator import (
    MarkdownValidator,
    ValidationResult,
)

__all__ = ["MarkdownValidator", "ValidationResult"]
