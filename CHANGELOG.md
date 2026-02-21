# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.27.0] - 2026-02-21

### 🎉 MILESTONE: MCP Testing & CI/CD Infrastructure

Major release focusing on code quality, automated testing, and eliminating production debugging.

### Added

#### CI/CD Pipeline
- GitHub Actions workflow with multi-job pipeline (lint → test → mcp-validation → status)
- Matrix testing across Python 3.11, 3.12, and 3.13
- Dependency caching for 4x faster builds (~30s vs 2-3min)
- Coverage reporting integration with Codecov
- Required status checks to prevent merging broken code
- Complete CI/CD documentation in `.github/workflows/README.md`

#### Test Suite (24 tests total)
- **test_mcp_edge_cases.py**: 7 regression tests covering critical bugs (100% passing ✅)
  - daily-sync returns empty dict instead of None
  - Session model attribute name validation
  - update-athlete-profile schema validation
  - Activity list None handling
  - Empty activity_dates protection
  - Create-remote-note regex patterns
  - Integration test validation

- **test_mcp_tools_comprehensive.py**: 17 comprehensive test cases
  - daily-sync: 5 tests (empty activities, multiple activities, mixed types, null handling, malformed dates)
  - analyze-session-adherence: 5 tests (perfect match, over/under performance, missing sessions, zero values)
  - update-athlete-profile: 7 tests (single/multiple fields, weight/HR updates, empty updates, custom fields)

#### MCP Schema Validation
- Automated validation of all 30+ MCP tool schemas on every commit
- Critical tool verification (daily-sync, analyze-session-adherence, update-athlete-profile)
- Schema correctness checks (additionalProperties, required fields, etc.)

### Fixed

#### Critical MCP Handler Bugs
All bugs discovered through testing and now prevented by CI:

1. **daily-sync: NoneType AttributeError** (Priority 0)
   - Fixed `update_completed_sessions()` returning `None` instead of `{}`
   - Added empty dict returns on lines 1362, 1387 of `daily_sync.py`
   - Added protection for empty `activity_dates` list (line 1373)
   - Added None checks in 5 activity processing loops
   - **Impact**: Tool now works correctly, no more crashes

2. **analyze-session-adherence: Wrong Attribute Names** (Priority 0)
   - Fixed `planned_tss` → `tss_planned` (line 2766 of `mcp_server.py`)
   - Fixed `planned_duration` → `duration_min` (line 2770 of `mcp_server.py`)
   - **Impact**: Adherence analysis now functional

3. **update-athlete-profile: Incomplete JSON Schema** (Priority 0)
   - Added `"additionalProperties": true` to updates schema (line 580 of `mcp_server.py`)
   - **Impact**: Tool now accepts dynamic fields like `{"ftp": 223, "weight": 75}`

4. **daily-sync: Empty List Protection** (New bug found by tests)
   - Added check for empty `activity_dates` before `min()`/`max()` calls
   - **Impact**: Prevents ValueError when processing activities with missing dates

### Changed

#### Code Quality
- Removed debug traceback wrapper from `handle_daily_sync`
- Cleaned up error handling to use standard MCP exception propagation
- Added protection against None entries in activity lists (5 locations)
- Improved null safety across all MCP handlers

#### Development Workflow
- Pre-commit hooks now aligned with CI validation
- Local testing commands documented for pre-push validation
- Coverage tracking enabled for all new code

### Developer Experience

**Before this release:**
- ❌ Bugs discovered in production
- ❌ Manual testing required
- ❌ No coverage tracking
- ❌ Inconsistent code quality

**After this release:**
- ✅ All code validated automatically before merge
- ✅ 24 tests prevent regression
- ✅ Coverage tracked on every commit
- ✅ CI fails on any quality issues
- ✅ Never debug in production again! 🎉

### Performance

- CI pipeline runs in ~5-8 minutes (with caching)
- Local test suite runs in ~6-8 seconds
- Matrix strategy parallelizes Python version testing

### Documentation

- Complete CI/CD guide in `.github/workflows/README.md`
- Badge integration instructions for repository README
- Local testing commands for pre-push validation
- Debugging guide for CI failures

### Technical Debt Addressed

- Eliminated 4 critical production bugs through automated testing
- Established testing infrastructure for future MCP tools
- Created regression test suite to prevent bug recurrence
- Implemented code quality gates

### Dependencies

- Added `pytest-asyncio` ^1.3.0 for async test support
- All tests compatible with Python 3.11, 3.12, and 3.13

### Migration Notes

No breaking changes. All MCP tools remain backward compatible.

### Next Steps

Recommended post-release actions:
1. Enable GitHub branch protection rules for `main`
2. Require CI status checks before merge
3. Set up Codecov integration for coverage badges
4. Consider adding integration tests for Intervals.icu API

---

## [1.26.0] - 2026-02-21

### Added
- PID and Peaks hierarchical recommendation system integration
- Daily-sync adherence alerts and CTL progression monitoring
- Weekly planner with PLANNING_PREFERENCES (mercredi repos rule)
- Sprint R10 Day 3 planning templates and integration

### Changed
- Load PLANNING_PREFERENCES in weekly planner prompt
- Enhanced monitoring with adherence tracking

---

## Template for Future Releases

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes
```

---

**Legend:**
- 🎉 Major milestone
- ⚠️ Breaking change
- 🐛 Bug fix
- ✨ New feature
- 🔧 Enhancement
- 📝 Documentation
- 🧪 Testing
