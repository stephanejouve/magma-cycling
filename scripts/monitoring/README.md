# Workout Adherence Monitoring

Automated monitoring system to detect skipped/missed workouts.

## Quick Start

```bash
# Test manually (dry-run)
poetry run python scripts/monitoring/check_workout_adherence.py --dry-run

# Install cron job (runs daily at 22:00)
bash scripts/monitoring/setup_cron.sh

# Remove cron job
bash scripts/monitoring/remove_cron.sh
```

## Files

- `check_workout_adherence.py` - Main monitoring script
- `setup_cron.sh` - Install cron job
- `remove_cron.sh` - Remove cron job
- `__init__.py` - Module initialization

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
