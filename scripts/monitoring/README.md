# Workout Adherence Monitoring

Automated monitoring system to detect skipped/missed workouts.

## Quick Start

```bash
# Test manually (dry-run)
poetry run python scripts/monitoring/check_workout_adherence.py --dry-run

# Install automated monitoring
# macOS (recommended - uses launchd)
bash scripts/monitoring/setup_launchd.sh

# Linux (uses cron)
bash scripts/monitoring/setup_cron.sh

# Remove
bash scripts/monitoring/remove_launchd.sh  # macOS
bash scripts/monitoring/remove_cron.sh     # Linux
```

## Files

- `check_workout_adherence.py` - Main monitoring script
- `setup_launchd.sh` - Install launchd job (macOS, recommended)
- `remove_launchd.sh` - Remove launchd job (macOS)
- `com.cyclisme.workout_adherence.plist` - launchd configuration
- `setup_cron.sh` - Install cron job (Linux/legacy)
- `remove_cron.sh` - Remove cron job (Linux/legacy)
- `__init__.py` - Module initialization

## macOS vs Linux

**macOS (recommended):** Use `launchd` - native macOS scheduler
- Better power management
- Automatic retry on failure
- Integrated logging
- Recommended by Apple (cron is deprecated)

**Linux:** Use `cron` - standard Unix scheduler
- Universal Linux support
- Simple configuration

## Documentation

See [GUIDE_MONITORING.md](../../project-docs/guides/GUIDE_MONITORING.md) for complete documentation.

## Sprint R6 Integration

This monitoring system is essential for Sprint R6 (PID Baseline & Calibration):
- Detects skipped workouts that affect baseline data collection
- Logs adherence for PID calibration analysis
- Sends notifications for immediate corrective action

## Logs

- Adherence data: `~/data/monitoring/workout_adherence.jsonl`
- Cron output: `~/data/monitoring/cron.log`
