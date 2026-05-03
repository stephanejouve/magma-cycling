"""Analysis and backup tool schemas."""

from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return analysis and backup tool schemas."""
    return [
        Tool(
            name="check-workout-adherence",
            description=(
                "Daily-batch adherence check (legacy CLI check-workout-adherence). "
                "Different from analyze-session-adherence which is per-session. "
                "Three modes : 'day' (default, check single date), 'week' (Monday→Sunday "
                "of the date's week), 'weekly_alert' (R10 alerts if weekly adherence "
                "<85%%). Used by the legacy LaunchAgent at 22h daily."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Check mode (day=single date, week=full week, weekly_alert=R10 alerts)",
                        "enum": ["day", "week", "weekly_alert"],
                        "default": "day",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date to check (YYYY-MM-DD, default: today)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Dry-run mode (no notifications)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="pid-daily-evaluation",
            description=(
                "Run the PID training intelligence pipeline (legacy CLI "
                "pid-daily-evaluation). Two modes : 'daily' (default) collects "
                "cycle metrics + learnings + CTL/Peaks monitoring + test FTP "
                "opportunity check ; 'cycle' recalibrates PID with a measured "
                "FTP at end of training cycle. Updates ~/data/intelligence.json "
                "and appends to ~/data/monitoring/pid_evaluation.jsonl."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Evaluation mode (daily collects, cycle recalibrates PID)",
                        "enum": ["daily", "cycle"],
                        "default": "daily",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Days to analyze in daily mode (default 7)",
                        "minimum": 1,
                        "maximum": 90,
                        "default": 7,
                    },
                    "measured_ftp": {
                        "type": "number",
                        "description": ("Measured FTP from test (W). REQUIRED when mode='cycle'."),
                        "minimum": 50,
                        "maximum": 600,
                    },
                    "cycle_weeks": {
                        "type": "integer",
                        "description": "Cycle duration in weeks (default 6, mode='cycle')",
                        "minimum": 1,
                        "maximum": 52,
                        "default": 6,
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Dry-run mode (no file writes)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="validate-week-consistency",
            description="Validate week planning consistency (no conflicts, TSS coherent, sessions well-formed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="get-recommendations",
            description="Get PID and Peaks system recommendations for a week",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="analyze-session-adherence",
            description="Analyze adherence between planned session and completed activity (TSS, IF, duration comparison)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (e.g., S081-04)",
                    },
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (format: i107424849)",
                    },
                },
                "required": ["session_id", "activity_id"],
            },
        ),
        Tool(
            name="get-training-statistics",
            description="Get aggregated training statistics for a date range (TSS, compliance, intensity distribution)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        ),
        Tool(
            name="export-week-to-json",
            description="Export week planning to JSON file for backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path (optional, defaults to /tmp/)",
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="restore-week-from-backup",
            description="Restore week planning from JSON backup file (PROTECTION: requires confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "backup_path": {
                        "type": "string",
                        "description": "Path to backup JSON file",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation required for restore (default: false)",
                        "default": False,
                    },
                },
                "required": ["week_id", "backup_path", "confirm"],
            },
        ),
        Tool(
            name="analyze-training-patterns",
            description="META TOOL: Comprehensive analysis loading all relevant data (planning, activities, wellness, adherence) for AI coach analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID to analyze (e.g., S081)",
                        "pattern": "^S\\d{3}$",
                    },
                    "depth": {
                        "type": "string",
                        "description": "Analysis depth: 'quick' (current week only), 'standard' (current + prev week), 'comprehensive' (current + prev + context)",
                        "enum": ["quick", "standard", "comprehensive"],
                        "default": "standard",
                    },
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include PID/Peaks recommendations if available (default: true)",
                        "default": True,
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="validate-local-remote-sync",
            description="Compare local planning sessions vs Intervals.icu remote events to detect sync drift (name/type/date mismatches, swaps, orphans). Description check off by default (structural noise).",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_id": {
                        "type": "string",
                        "description": "Week ID (e.g., S087)",
                        "pattern": "^S\\d{3}$",
                    },
                    "include_description_check": {
                        "type": "boolean",
                        "description": "Include DESCRIPTION_MISMATCH checks (default: false, opt-in for debug)",
                        "default": False,
                    },
                },
                "required": ["week_id"],
            },
        ),
        Tool(
            name="get-coach-analysis",
            description="Retrieve past coach AI analysis from workouts-history.md by activity ID, session ID, or date",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "Activity ID (e.g., i131572602)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Planning session ID (e.g., S084-04). Uses word-boundary match to avoid partial hits.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format. Returns all analyses for that day.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "section": {
                        "type": "string",
                        "description": "Filter to a specific section (default: full)",
                        "enum": [
                            "metrics_pre",
                            "execution",
                            "technique",
                            "load",
                            "validation",
                            "attention",
                            "recommendations",
                            "metrics_post",
                            "full",
                        ],
                        "default": "full",
                    },
                },
            },
        ),
    ]
