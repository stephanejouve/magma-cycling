# Changelog

All notable changes to Cyclisme Training Logs will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### [Sprint R2.1] - 2026-01-01

#### Added - Advanced Metrics & VETO Safety

**6 Advanced Analytics Functions** (`utils/metrics_advanced.py`):
- `calculate_ramp_rate()`: CTL progression rate analysis (points/week)
  - Master athlete recommendations: max 5-7 points/week
  - Alerts if >10 points/week (overload risk)
- `get_weekly_metrics_trend()`: Trend detection (rising/stable/declining)
  - Analyzes 2+ weeks of data
  - Returns slope + volatility metrics
- `detect_training_peaks()`: Significant load peak identification
  - 3-week rolling baseline
  - Configurable threshold (default: 10% increase)
- `get_recovery_recommendation()`: Personalized recovery advice
  - 4 priority levels: low/medium/high/critical
  - Master athlete automatic adjustments
  - Intensity + duration + rest day limits
- `format_metrics_comparison()`: Period-to-period comparison formatting
  - Visual symbols: ↑ ↓ →
  - Customizable labels

**CRITICAL Safety Function** (`detect_overtraining_risk()`):
- VETO logic for master athlete protection (54 years)
- Automatic session cancellation triggers:
  - TSB < -25 (critical fatigue)
  - ATL/CTL > 1.8 (acute overload)
  - Sleep < 5.5h (insufficient recovery)
  - Sleep < 6h + TSB < -15 (combined stress, sleep-dependent athletes)
- Returns: veto boolean, risk_level, recommendation, factors
- Calibrated thresholds for master athletes (50+ years)

**VETO Integration** (`rest_and_cancellations.py`):
- `check_pre_session_veto()`: Pre-session overtraining check
- Calls `detect_overtraining_risk()` with wellness + profile data
- Usage before high-intensity sessions (>85% FTP)
- Comprehensive logging of VETO decisions
- 11 integration tests (100% passing)

#### Tests
- 32 new tests for advanced metrics (100% coverage)
- 11 VETO integration tests (100% passing)
- **Total: 91 tests passing** (80 existing + 43 new)
- 0 regressions

#### Documentation
- `SPRINT_R2.1_DOCUMENTATION.md`: Complete technical documentation
- `GUIDE_INSTALLATION_R2.1.md`: 3-step installation guide
- `RECAPITULATIF_SPRINT_R2.1.md`: Sprint summary + archive
- `VETO_PROTOCOL.md`: Detailed VETO protocol for athletes
- Google Style docstrings with examples (100% functions)
- Type hints: 100% coverage

#### Archive
- `cyclisme-training-logs-sprint-r2.1-20260101.tar.gz` (15 MB)
- Complete project state with Sprint R2.1 integrated
- Extraction instructions provided

---

### [Sprint R2] - 2026-01-01

#### Added - Centralization CTL/ATL/TSB + Configuration

**Core Metrics Utilities** (`utils/metrics.py`):
- `extract_wellness_metrics()`: Unified extraction with None handling
- `calculate_tsb()`: TSB = CTL - ATL calculation
- `format_metrics_display()`: Format "CTL: X | ATL: Y | TSB: Z"
- `is_metrics_complete()`: Validation completeness check
- `calculate_metrics_change()`: Delta between 2 timepoints
- `get_metrics_safely()`: Safe extraction from lists

**Configuration Modules**:
- `config/athlete_profile.py`: Athlete characteristics from environment
  - Age, category (junior/senior/master), recovery capacity
  - FTP, weight, power-to-weight ratio
  - Pydantic validation with Field constraints
- `config/thresholds.py`: Training load thresholds from environment
  - TSB thresholds: fresh/optimal/fatigued/overreached
  - ATL/CTL ratio thresholds: optimal/warning/critical
  - Recovery indicators: HRV, sleep, resting HR
  - Methods: `get_tsb_state()`, `is_overtraining_risk()`

**Environment Variables** (17 new):
- Athlete profile: age, category, recovery capacity, sleep dependency, FTP, weight
- TSB thresholds: fresh_min, optimal_min, fatigued_min, critical
- ATL/CTL ratios: optimal, warning, critical
- Recovery indicators: HRV threshold, sleep hours min, HR deviation max
- Feature flag: ENABLE_RECOVERY_ANALYZER

#### Changed
- **8 files migrated** to centralized utilities:
  - `prepare_analysis.py`
  - `rest_and_cancellations.py` (3 locations)
  - `weekly_analysis.py` (2 locations)
  - `weekly_aggregator.py` (3 locations)
  - `sync_intervals.py` (2 locations)
  - `weekly_planner.py`
  - `planned_sessions_checker.py`
  - `daily_aggregator.py`
- ~150 lines of duplicated code eliminated
- Consistent None handling across all files

#### Tests
- 48 new tests (100% coverage on new modules)
- **404 tests passing total**
- 0 regressions

#### Documentation
- `LIVRAISON_MOA_SPRINT_R2.md`: Complete delivery documentation
- `REPONSE_MOA_SPRINT_R2.md`: MOA questions responses
- `SPRINT_R2_VALIDATION_S074.md`: S074 week validation
- Reorganized: `project-docs/sprints/R2/` structure

---

### [Sprint R1] - 2025-12

#### Added - Infrastructure & Base Workflows
- Project infrastructure setup
- Basic workflows implementation
- Initial documentation structure

---

## Version History

- **Sprint R2.1** (2026-01-01): Advanced Metrics + VETO Safety
- **Sprint R2** (2026-01-01): Centralization CTL/ATL/TSB + Configuration
- **Sprint R1** (2025-12): Infrastructure & Base Workflows

---

**Legend:**
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
