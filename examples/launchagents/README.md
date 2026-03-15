# LaunchAgents Examples

These are example macOS LaunchAgent configuration files for automating
Magma Cycling workflows. They are **not** loaded automatically &mdash; you must
adapt paths and install them manually.

## Before you start

Every `.plist` references `/Users/stephanejouve/` in `ProgramArguments` and
log paths. **Replace these with your own home directory** before installing.

```bash
# Quick path replacement (example)
sed -i '' 's|/Users/stephanejouve|/Users/YOUR_USER|g' com.cyclisme.*.plist
```

## Installation

```bash
# 1. Copy the plist(s) you want into ~/Library/LaunchAgents/
cp com.cyclisme.rept.10-daily-sync-21h30.plist ~/Library/LaunchAgents/

# 2. Load the agent
launchctl load ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist

# 3. Verify
launchctl list | grep cyclisme
```

To unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
```

## Service catalogue

### Daily agents

| Plist | Schedule | Description |
|---|---|---|
| `rept.10-daily-sync-21h30` | 21 h 30 | Daily sync + AI analysis email |
| `mon.10-adherence-daily-22h` | 22 h 00 | Workout adherence collection |
| `anls.10-pid-evaluation-daily-23h` | 23 h 00 | PID evaluation (training intelligence) |
| `mnt.10-project-clean-daily` | Daily | Project cleanup (temp files, caches) |

### Weekly agents

| Plist | Schedule | Description |
|---|---|---|
| `flow.10-end-of-week-sun-20h` | Sunday 20 h 00 | End-of-week planning |

### Hourly agents

| Plist | Schedule | Description |
|---|---|---|
| `mnt.20-sync-docs-hourly` | Every hour | iCloud docs sync |
| `mnt.30-rsync-sites-hourly` | Every hour | Web docs rsync |

### Legacy / one-shot agents

| Plist | Description |
|---|---|
| `project-cleaner` | Legacy project cleaner |
| `sync-docs-icloud` | Legacy iCloud sync |
| `pid_evaluation` | Legacy PID evaluation |
| `workout_adherence` | Legacy adherence monitor |
| `end-of-week-oneshot` | One-shot end-of-week trigger |
| `brevo-dns-check-oneshot` | One-shot Brevo DNS check |

### Migration agents

| Plist | Description |
|---|---|
| `migration.10-phase1-install-now` | Phase 1: install new agents (RunAtLoad) |
| `migration.20-phase2-unload-48h` | Phase 2: unload old agents after 48 h |
| `migration.30-phase3-archive-7d` | Phase 3: archive old plists after 7 days |

See `END_OF_WEEK_ONESHOT_README.md` for details on the one-shot end-of-week agent.
