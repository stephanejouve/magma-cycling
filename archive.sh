#!/bin/bash
# Archive pour zsh - Gestion stricte des globs

ARCHIVE_NAME="cyclisme-training-$(date +%Y%m%d-%H%M%S).tar.gz"

tar -czf "$ARCHIVE_NAME" \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='*.egg-info' \
  --exclude='backups/migration_*' \
  --exclude='logs/weekly_reports.backup.*' \
  scripts/*.py \
  scripts/*.md \
  $(find scripts -name '*.txt' 2>/dev/null) \
  docs/*.md \
  references/*.md \
  logs/weekly_reports/S067/*.md \
  logs/weekly_reports/S068/*.md \
  logs/weekly_reports/S069/*.md \
  logs/weekly_reports/S070/*.md \
  logs/metrics-evolution.md \
  logs/metrics_sync_summary.md \
  logs/workouts-history.md \
  logs/training-learnings.md \
  logs/workout-templates.md \
  $(find logs -maxdepth 1 -name '*.txt' 2>/dev/null) \
  requirements.txt \
  withings_integration/requirements.txt \
  README.md \
  RAPPORT_*.md \
  AUDIT_*.md \
  DIAGNOSTIC_*.md \
  SETUP_GITHUB.md \
  ARCHIVE_README.md \
  reponse-second-testupload-workouts-py.md \
  withings_integration/core/*.py \
  withings_integration/scripts/*.py \
  withings_integration/docs/*.md \
  data/week_planning/*.md \
  inspect_workout.py \
  2>/dev/null

# Vérification
if [ -f "$ARCHIVE_NAME" ]; then
    echo "✅ Archive créée: $ARCHIVE_NAME"
    ls -lh "$ARCHIVE_NAME"
    echo ""
    echo "📊 Contenu (50 premiers):"
    tar -tzf "$ARCHIVE_NAME" | head -50
    echo ""
    echo "📈 Stats:"
    echo "  Python: $(tar -tzf "$ARCHIVE_NAME" | grep -c '\.py$') fichiers"
    echo "  Markdown: $(tar -tzf "$ARCHIVE_NAME" | grep -c '\.md$') fichiers"
    echo "  Total: $(tar -tzf "$ARCHIVE_NAME" | wc -l | tr -d ' ') fichiers"
else
    echo "❌ Erreur création archive"
fi
