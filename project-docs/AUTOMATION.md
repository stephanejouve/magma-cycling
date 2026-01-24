# Automation System

This document describes the automated workflows configured via macOS LaunchAgents.

## Overview

Two automated workflows run on schedule:
1. **Daily Sync** - Runs every day at 21:30 (9:30 PM)
2. **End of Week** - Runs every Sunday at 20:00 (8:00 PM)

Both workflows use auto-calculation of week-ids based on the `WeekReferenceConfig`, eliminating all hard-coded dates and week numbers.

## Daily Sync Automation

### Schedule
- **Frequency**: Every day
- **Time**: 21:30 (9:30 PM)
- **LaunchAgent**: `~/Library/LaunchAgents/com.traininglogs.dailysync.plist`

### What it does
1. Fetches new activities from Intervals.icu
2. Generates AI analysis for each activity
3. Automatically inserts analysis into `workouts-history.md`
4. Sends daily email report with:
   - Completed activities and AI analysis
   - Planning modifications detected
   - Auto-servo recommendations (if criteria met)
5. Auto-servo mode evaluation:
   - Checks if planning adjustments are needed based on:
     - Découplage > 7.5%
     - Sommeil < 7h
     - Feel ≤ 2/4
     - TSB < -10
   - If criteria met, generates AI recommendations for adjustments
   - Includes recommendations in email report

### Week-ID Calculation
- Automatically calculated from current date using `WeekReferenceConfig`
- No manual week-id specification needed
- Works across multiple seasons

### Command
```bash
poetry run daily-sync --send-email --ai-analysis --auto-servo
```

### Logs
- **Output**: `~/Library/Logs/traininglogs-dailysync.log`
- **Errors**: `~/Library/Logs/traininglogs-dailysync.error.log`

### Manual Testing
```bash
# Dry-run to test without making changes
poetry run daily-sync --dry-run

# With email and AI analysis
poetry run daily-sync --send-email --ai-analysis

# With auto-servo evaluation
poetry run daily-sync --send-email --ai-analysis --auto-servo
```

## End of Week Automation

### Schedule
- **Frequency**: Every Sunday
- **Time**: 20:00 (8:00 PM)
- **LaunchAgent**: `~/Library/LaunchAgents/com.traininglogs.endofweek.plist`

### What it does
Complete 6-step weekly transition workflow:

1. **Analyze Completed Week**
   - Runs `weekly-analysis` for the week that just ended
   - Generates bilan final, transition report, metrics evolution

2. **Generate Planning Prompt**
   - Runs `weekly-planner` for the upcoming week
   - Includes context from previous week analysis

3. **Generate Workouts via AI**
   - Calls Claude API to generate 7 workouts
   - Saves to `{week_next}_workouts.txt`

4. **Validate Workouts**
   - Validates workout notation format
   - Ensures all required fields present

5. **Upload to Intervals.icu**
   - Programmatically uploads all 7 workouts
   - Creates events in Intervals.icu calendar

6. **Archive (Optional)**
   - Archives reports and planning files
   - Commits changes to git

### Week-ID Calculation
The workflow automatically calculates:
- `week_completed`: The week that just ended (contains today's date)
- `week_next`: The week starting next Monday

Example:
- Running on Sunday 2026-01-25 or Monday 2026-01-26:
  - `week_completed` = S077 (2026-01-19 to 2026-01-25)
  - `week_next` = S078 (2026-01-26 to 2026-02-01)

### Command
```bash
poetry run end-of-week --auto-calculate --provider claude_api --auto
```

### Logs
- **Output**: `~/Library/Logs/traininglogs-endofweek.log`
- **Errors**: `~/Library/Logs/traininglogs-endofweek.error.log`

### Manual Testing
```bash
# Dry-run to test without making changes
poetry run end-of-week --auto-calculate --dry-run

# With manual confirmation (clipboard mode)
poetry run end-of-week --auto-calculate

# Fully automatic with Claude API
poetry run end-of-week --auto-calculate --provider claude_api --auto

# Specify weeks manually (old way)
poetry run end-of-week --week-completed S077 --week-next S078
```

## Configuration

### Environment Variables
All environment variables are loaded from `.env` file:
- `CLAUDE_API_KEY` - Claude API key for AI analysis
- `INTERVALS_API_KEY` - Intervals.icu API key
- `BREVO_API_KEY` - Brevo email API key
- `EMAIL_TO` - Recipient email address

### Week Reference Config
Located in `.config.json`:
```json
{
  "week_reference": {
    "seasons": [
      {
        "season_id": "2024-2025",
        "week_ids": ["S001"],
        "reference_dates": ["2024-08-05"]
      }
    ]
  }
}
```

This configuration:
- Defines S001 as Monday August 5, 2024
- All subsequent weeks calculated from this reference
- Supports multiple seasons
- No hard-coded dates in code

## LaunchAgent Management

### Check Status
```bash
# List all training logs agents
launchctl list | grep traininglogs

# Should show:
# -  0  com.traininglogs.dailysync
# -  0  com.traininglogs.endofweek
```

### Reload Configuration
```bash
# After modifying plist files
launchctl unload ~/Library/LaunchAgents/com.traininglogs.dailysync.plist
launchctl load ~/Library/LaunchAgents/com.traininglogs.dailysync.plist

launchctl unload ~/Library/LaunchAgents/com.traininglogs.endofweek.plist
launchctl load ~/Library/LaunchAgents/com.traininglogs.endofweek.plist
```

### Disable Automation
```bash
# Unload agents to stop automation
launchctl unload ~/Library/LaunchAgents/com.traininglogs.dailysync.plist
launchctl unload ~/Library/LaunchAgents/com.traininglogs.endofweek.plist
```

### Enable Automation
```bash
# Load agents to enable automation
launchctl load ~/Library/LaunchAgents/com.traininglogs.dailysync.plist
launchctl load ~/Library/LaunchAgents/com.traininglogs.endofweek.plist
```

## Zero Hard-Coding Principle

The automation system follows the project's "no hard coding tolerate" principle:

- **No hard-coded week-ids**: All week-ids auto-calculated from `WeekReferenceConfig`
- **No hard-coded dates**: All dates calculated dynamically from current date
- **No hard-coded paths**: All paths loaded from `.config.json`
- **No hard-coded credentials**: All credentials loaded from `.env`

This ensures:
- Automation works across seasons without manual updates
- No weekly maintenance required
- Single source of truth for all configuration

## Troubleshooting

### Check Logs
```bash
# View daily-sync logs
tail -f ~/Library/Logs/traininglogs-dailysync.log
tail -f ~/Library/Logs/traininglogs-dailysync.error.log

# View end-of-week logs
tail -f ~/Library/Logs/traininglogs-endofweek.log
tail -f ~/Library/Logs/traininglogs-endofweek.error.log
```

### Common Issues

**Agent not running**
- Check if loaded: `launchctl list | grep traininglogs`
- Reload: `launchctl unload ... && launchctl load ...`

**Missing API keys**
- Verify `.env` file exists in project root
- Check environment variables are set correctly
- LaunchAgents load `.env` via python-dotenv in config module

**Wrong week-id calculated**
- Verify `.config.json` has correct S001 reference date
- Check date calculation: `poetry run end-of-week --auto-calculate --dry-run`

**Email not received**
- Check Brevo API key is valid
- Verify sender email is verified in Brevo
- Check spam folder
- Review logs for email errors

## Future Enhancements

- Archive automation (step 6) for end-of-week
- Notification system for automation failures
- Web dashboard for monitoring automation status
- Automatic rollback on upload failures
