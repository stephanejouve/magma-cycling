#!/bin/bash
# Remove cron job for workout adherence monitoring
#
# Usage:
#   bash scripts/monitoring/remove_cron.sh

set -e

echo "=========================================="
echo "🗑️  Removing Workout Adherence Monitoring"
echo "=========================================="
echo ""

# Check if cron job exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "check_workout_adherence.py" || true)

if [ -z "$EXISTING_CRON" ]; then
    echo "ℹ️  No cron job found for workout adherence monitoring"
    exit 0
fi

echo "📝 Existing cron job:"
echo "$EXISTING_CRON"
echo ""

read -p "Do you want to remove it? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Removal cancelled"
    exit 1
fi

# Remove cron job
crontab -l 2>/dev/null | grep -v "check_workout_adherence.py" | crontab -

echo "✅ Cron job removed successfully!"
echo ""
echo "ℹ️  Note: Log files in ~/data/monitoring/ were not deleted"
echo "   To remove logs:"
echo "   rm ~/data/monitoring/workout_adherence.jsonl"
echo "   rm ~/data/monitoring/cron.log"
echo ""
