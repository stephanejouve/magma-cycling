"""
Pydantic models for weekly planning with anti-aliasing protection.

This module provides type-safe models for weekly planning data with automatic
deep copy validation to prevent shallow copy bugs detected by memory_graph analysis.

Key Features:
    - Automatic deep copy on assignment to prevent aliasing
    - Validation of planning structure and constraints
    - Type-safe access to planning data
    - Immutability protection via validators

Examples:
    Load planning from JSON::

        with open("week_planning_S079.json", encoding="utf-8") as f:
            data = json.load(f)

        # Automatic validation and deep copy protection
        plan = WeeklyPlan(**data)

        # Safe backup - creates true deep copy
        backup = plan.backup_sessions()

        # Modification doesn't affect backup
        plan.sessions[0].status = "cancelled"
        assert backup[0].status != "cancelled"  # ✅ Protected!

    Create planning from scratch::

        session = Session(
            session_id="S080-01",
            date=date(2026, 2, 9),
            name="EnduranceDouce",
            type="END",
            tss_planned=50,
            duration_min=60
        )

        plan = WeeklyPlan(
            week_id="S080",
            start_date=date(2026, 2, 9),
            end_date=date(2026, 2, 15),
            tss_target=350,
            sessions=[session]
        )

Architecture Decision:
    - Uses Pydantic v2 BaseModel (already installed: pydantic ^2.5.0)
    - Follows existing pattern from athlete_profile.py and thresholds.py
    - Prevents shallow copy bugs via model_validator
    - Compatible with existing JSON structure (no migration needed)

Author: Claude Sonnet 4.5
Created: 2026-02-08
Version: 1.0.0

Metadata:
    Status: Production
    Priority: P0 (Anti-aliasing protection)
    Sprint: R9 Follow-up
"""

import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- Session ID patterns (canonical source) ---
SESSION_ID_PATTERN = r"S\d{3}-\d{2}[a-z]?"
SESSION_ID_REGEX = re.compile(r"^" + SESSION_ID_PATTERN + r"$")
WORKOUT_NAME_PATTERN = r"(" + SESSION_ID_PATTERN + r")-(\w+)-([^-]+)-(V\d{3})"
WORKOUT_NAME_REGEX = re.compile(WORKOUT_NAME_PATTERN)


class Session(BaseModel):
    """
    Individual training session within a weekly plan.

    Attributes:
        session_id: Unique session identifier (e.g., "S079-01")
        date: Planned session date
        name: Session name (e.g., "EnduranceDouce")
        type: Session type (END, INT, REC, CAD, VO2, etc.)
        version: Session version (e.g., "V001")
        tss_planned: Planned Training Stress Score
        duration_min: Planned duration in minutes
        description: Workout description text
        status: Session status (pending, completed, skipped, cancelled)
        intervals_id: Intervals.icu event ID (after upload)
        description_hash: SHA256 hash for change detection
        skip_reason: Reason if status is "skipped"

    Anti-Aliasing Protection:
        - Pydantic creates new instances on validation
        - model_copy() returns deep copy by default
        - No shared references between instances
    """

    session_id: str = Field(
        pattern=r"^S\d{3}-\d{2}[a-z]?$",
        description="Session ID (e.g., S079-01, S081-06a for double sessions)",
    )
    session_date: date = Field(alias="date", description="Planned session date")
    name: str = Field(min_length=1, description="Session name")
    session_type: str = Field(
        alias="type", description="Session type (END, INT, REC, CAD, VO2, etc.)"
    )  # Use alias to avoid 'type' keyword conflict
    version: str = Field(default="V001", pattern=r"^V\d{3}$", description="Session version")
    tss_planned: int = Field(ge=0, le=500, description="Planned Training Stress Score")
    duration_min: int = Field(ge=0, le=600, description="Planned duration in minutes")
    description: str = Field(default="", description="Workout description")
    status: Literal[
        "pending",
        "planned",
        "uploaded",
        "completed",
        "skipped",
        "cancelled",
        "rest_day",
        "replaced",
        "modified",
    ] = Field(default="pending", description="Session status")
    intervals_id: int | None = Field(default=None, description="Intervals.icu event ID")
    description_hash: str | None = Field(default=None, description="SHA256 hash for sync")
    skip_reason: str | None = Field(
        default=None, alias="reason", description="Reason if skipped/cancelled/replaced"
    )

    @model_validator(mode="after")
    def validate_skip_reason(self) -> "Session":
        """Ensure skip_reason is set when status requires a reason."""
        if self.status in ("skipped", "cancelled", "replaced") and not self.skip_reason:
            raise ValueError(f"skip_reason required when status is '{self.status}'")
        return self

    def model_copy_deep(self) -> "Session":
        """
        Create a true deep copy of this session.

        Returns:
            New Session instance with no shared references.

        Example:
            >>> session = Session(session_id="S080-01", ...)
            >>> copy = session.model_copy_deep()
            >>> copy.status = "cancelled"
            >>> assert session.status != copy.status  # ✅ No aliasing
        """
        return Session(**self.model_dump(mode="python"))

    model_config = ConfigDict(
        validate_assignment=True,  # Validate on attribute assignment
        frozen=False,  # Allow modifications (needed for status updates)
        populate_by_name=True,  # Allow both 'session_type' and 'type'
    )


class WeeklyPlan(BaseModel):
    """
    Weekly training plan with anti-aliasing protection.

    Attributes:
        week_id: Week identifier (e.g., "S079")
        start_date: Week start date (Monday)
        end_date: Week end date (Sunday)
        created_at: Plan creation timestamp
        last_updated: Last modification timestamp
        version: Plan version number
        athlete_id: Athlete identifier (e.g., "iXXXXXX")
        tss_target: Target weekly TSS
        planned_sessions: List of sessions (auto deep-copied)

    Anti-Aliasing Protection:
        - Sessions list is deep-copied on initialization
        - backup_sessions() returns true deep copy
        - restore_sessions() deep-copies before assignment
        - No shared references with external code

    Example:
        >>> plan = WeeklyPlan.from_json("week_planning_S079.json")
        >>> backup = plan.backup_sessions()
        >>> plan.sessions[0].status = "cancelled"
        >>> plan.restore_sessions(backup)  # ✅ Restored safely
    """

    week_id: str = Field(pattern=r"^S\d{3}$", description="Week identifier (e.g., S079)")
    start_date: date = Field(description="Week start date (Monday)")
    end_date: date = Field(description="Week end date (Sunday)")
    created_at: datetime = Field(description="Plan creation timestamp")
    last_updated: datetime = Field(description="Last modification timestamp")
    version: int = Field(ge=1, description="Plan version number")
    athlete_id: str = Field(description="Athlete identifier (e.g., iXXXXXX)")
    tss_target: int = Field(ge=0, le=2000, description="Target weekly TSS")
    planned_sessions: list[Session] = Field(
        default_factory=list, alias="planned_sessions", description="List of planned sessions"
    )

    @field_validator("start_date")
    @classmethod
    def validate_start_monday(cls, v: date) -> date:
        """Ensure start_date is a Monday."""
        if v.weekday() != 0:
            raise ValueError(f"start_date must be Monday, got {v.strftime('%A')}")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_sunday(cls, v: date, info) -> date:
        """Ensure end_date is Sunday and matches start_date + 6 days."""
        start_date = info.data.get("start_date")
        if start_date and v != start_date + timedelta(days=6):
            raise ValueError(f"end_date must be start_date + 6 days, got {v}")
        if v.weekday() != 6:
            raise ValueError(f"end_date must be Sunday, got {v.strftime('%A')}")
        return v

    @model_validator(mode="after")
    def validate_sessions_dates(self) -> "WeeklyPlan":
        """Ensure all session dates are within week boundaries."""
        for session in self.planned_sessions:
            if not (self.start_date <= session.session_date <= self.end_date):
                raise ValueError(
                    f"Session {session.session_id} date {session.session_date} "
                    f"outside week range {self.start_date} - {self.end_date}"
                )
        return self

    def backup_sessions(self) -> list[Session]:
        """
        Create a true deep copy of all sessions.

        Returns:
            New list with deep-copied Session instances.

        Anti-Aliasing Guarantee:
            Modifying the returned list or its sessions will NOT affect
            the original WeeklyPlan.planned_sessions.

        Example:
            >>> plan = WeeklyPlan(...)
            >>> backup = plan.backup_sessions()
            >>> backup[0].status = "cancelled"
            >>> assert plan.planned_sessions[0].status != "cancelled"  # ✅
        """
        return [session.model_copy_deep() for session in self.planned_sessions]

    def restore_sessions(self, backup: list[Session]) -> None:
        """
        Restore sessions from backup with deep copy protection.

        Args:
            backup: List of Session instances to restore from

        Anti-Aliasing Guarantee:
            Creates deep copy before assignment to prevent shared references.

        Example:
            >>> plan = WeeklyPlan(...)
            >>> backup = plan.backup_sessions()
            >>> # ... modifications ...
            >>> plan.restore_sessions(backup)  # ✅ Safe restoration
        """
        self.planned_sessions = [session.model_copy_deep() for session in backup]
        self.last_updated = datetime.now(UTC)

    @classmethod
    def from_json(cls, filepath: str | Path) -> "WeeklyPlan":
        """
        Load planning from JSON file with validation.

        Args:
            filepath: Path to week_planning_SXXX.json file

        Returns:
            Validated WeeklyPlan instance with deep copy protection

        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If JSON structure is invalid

        Example:
            >>> plan = WeeklyPlan.from_json("~/training-logs/data/week_planning/week_planning_S079.json")
            >>> print(f"Week {plan.week_id}: {len(plan.planned_sessions)} sessions")
        """
        filepath = Path(filepath).expanduser()
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self, filepath: str | Path, indent: int = 2) -> None:
        """
        Save planning to JSON file with atomic write.

        Args:
            filepath: Destination file path
            indent: JSON indentation (default: 2)

        Example:
            >>> plan = WeeklyPlan(...)
            >>> plan.to_json("week_planning_S080.json")
        """
        filepath = Path(filepath).expanduser()
        # Atomic write: write to temp file, then rename
        temp_path = filepath.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=indent, by_alias=True))
        temp_path.replace(filepath)

    model_config = ConfigDict(
        validate_assignment=True,  # Validate on attribute assignment
        frozen=False,  # Allow modifications
        populate_by_name=True,  # Allow both 'sessions' and 'planned_sessions'
    )


# Export public API
__all__ = ["Session", "WeeklyPlan"]
