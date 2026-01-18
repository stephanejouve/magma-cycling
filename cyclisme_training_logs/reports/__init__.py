"""Weekly Reports Generation Module.

This module provides AI-powered generation of weekly training reports.

Sprint R10 MVP focuses on 2 critical reports:
- workout_history: Detailed chronological session-by-session analysis
- bilan_final: Comprehensive week synthesis and learnings

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
Status: Production
Priority: P0
Version: 1.0.0

Metadata:
    Created: 2026-01-18
    Author: Cyclisme Training Logs Team
    Category: REPORTS
    Status: Production
    Priority: P0
    Version: 1.0.0
"""

from cyclisme_training_logs.reports.generator import ReportGenerator

__all__ = ["ReportGenerator"]

__version__ = "1.0.0"
