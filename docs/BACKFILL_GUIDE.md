# Backfill History Guide

## Overview

The `backfill-history` tool analyzes all historical training activities from Intervals.icu using the automated AI workflow.

## Quick Start

```bash
# 1. Test with dry run (see what would be analyzed)
poetry run backfill-history --dry-run --limit 10

# 2. Test with 10 real activities
poetry run backfill-history --limit 10 --provider mistral_api

# 3. Backfill complete history
poetry run backfill-history --start-date 2024-01-01 --provider mistral_api
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--start-date` | 2024-01-01 | Start date (YYYY-MM-DD) |
| `--end-date` | today | End date (YYYY-MM-DD) |
| `--provider` | mistral_api | AI provider |
| `--batch-size` | 10 | Activities per git commit |
| `--dry-run` | false | Test mode (no actual analysis) |
| `--skip-planned` | false | Skip activities with planned workouts |
| `--limit` | none | Max activities (for testing) |

## Providers Comparison

| Provider | Time/Activity | Cost/Activity | Quality | Recommendation |
|----------|---------------|---------------|---------|----------------|
| mistral_api | ~1 min | $0.02 | Good | ✅ Best for backfill |
| claude_api | ~40s | $0.08 | Excellent | High cost |
| ollama | ~4 min | $0 | Good | Free but slow |
| openai | ~50s | $0.05 | Excellent | Good balance |

## Examples

### Test Mode

```bash
# Dry run - see what would happen
poetry run backfill-history --dry-run --limit 5

# Test with 10 activities
poetry run backfill-history --limit 10 --provider mistral_api
```

### Production Backfill

```bash
# Full 2024 backfill with Mistral
poetry run backfill-history \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --provider mistral_api \
  --batch-size 10

# Full history with Claude (better quality, higher cost)
poetry run backfill-history \
  --start-date 2024-01-01 \
  --provider claude_api \
  --batch-size 5

# Free backfill with Ollama (slow)
poetry run backfill-history \
  --start-date 2024-01-01 \
  --provider ollama \
  --batch-size 20
```

### Specific Periods

```bash
# Q1 2024
poetry run backfill-history \
  --start-date 2024-01-01 \
  --end-date 2024-03-31

# November 2024
poetry run backfill-history \
  --start-date 2024-11-01 \
  --end-date 2024-11-30
```

## Process

1. **Fetch activities** from Intervals.icu API
2. **Filter** already analyzed (via manage-state)
3. **Estimate** time and cost
4. **Confirm** with user
5. **Analyze** each activity with `workflow-coach --auto`
6. **Commit** in batches to git
7. **Report** final statistics

## Output Example

```
📊 RÉSUMÉ:
   Total activités: 234
   Déjà analysées: 35
   À analyser: 199

⏱️  ESTIMATIONS:
   Temps: ~3.3h (199 min)
   Coût: $3.98 (mistral_api)

⚠️  CONFIRMATION REQUISE
   Cela va analyser 199 activités
   avec le provider 'mistral_api'

   Continuer? (yes/no): yes

[... progress ...]

✅ BACKFILL TERMINÉ!

📊 STATISTIQUES FINALES:
   Total activités: 234
   Déjà analysées: 35
   À analyser: 199
   ✅ Succès: 195
   ❌ Échecs: 4
   📈 Taux réussite: 98.0%

⏱️  TEMPS:
   Total: 187.3 min (3.12h)
   Moyenne: 57.2s par activité

💾 GIT:
   Commits créés: 20
   Activités par commit: ~10
```

## Troubleshooting

### Analysis Failures

If some activities fail:
1. Check provider API keys in `.env`
2. Verify network connectivity
3. Check Intervals.icu API limits
4. Review error messages in output

### Resume After Interruption

The tool can be safely interrupted (Ctrl+C). Already analyzed activities are marked and won't be re-analyzed on next run.

```bash
# Same command - will skip already analyzed
poetry run backfill-history --start-date 2024-01-01
```

### Re-analyze Failed Activities

```bash
# Get failed activity IDs from output
# Remove from analyzed set
poetry run manage-state --remove i12345678

# Re-run backfill (will pick up failed activities)
poetry run backfill-history --start-date 2024-01-01 --limit 20
```

## Best Practices

1. **Start with dry-run** to estimate scope
2. **Test with limit** (10-20 activities) before full backfill
3. **Use Mistral API** for best cost/quality ratio
4. **Batch size 10** is good default
5. **Monitor progress** - can take several hours
6. **Use screen/tmux** if running remotely

## Integration

After backfill:

```bash
# Verify complete history
poetry run manage-state --show --list 100

# Check git log
git log --oneline -20

# Review latest analyses
tail -500 logs/workouts-history.md
```

## Cost Estimates

For 200 activities:

| Provider | Time | Cost |
|----------|------|------|
| Mistral API | ~3.3h | ~$4 |
| Claude API | ~2.3h | ~$16 |
| OpenAI | ~2.7h | ~$10 |
| Ollama | ~13h | $0 |

## Common Issues

### Issue: Activities not detected

**Solution:** Check that activities have power data and TSS > 0. The workflow filters out invalid activities automatically.

### Issue: Slow analysis

**Solution:** Use a faster provider (claude_api, openai) or increase timeout limits. Ollama is slowest but free.

### Issue: Git conflicts

**Solution:** Make sure `logs/workouts-history.md` is clean before starting. Commit or stash any pending changes.

### Issue: API rate limiting

**Solution:** The tool includes 5s delays between batches. If still rate-limited, reduce batch-size or add longer delays.

## Advanced Usage

### Custom Date Range

```bash
# Specific week
poetry run backfill-history \
  --start-date 2024-06-01 \
  --end-date 2024-06-07

# Multiple periods (run separately)
poetry run backfill-history --start-date 2024-01-01 --end-date 2024-06-30
poetry run backfill-history --start-date 2024-07-01 --end-date 2024-12-31
```

### Testing New Provider

```bash
# Test with 5 activities first
poetry run backfill-history --limit 5 --provider claude_api --dry-run
poetry run backfill-history --limit 5 --provider claude_api
```

### Resume After Failure

```bash
# Check what failed
poetry run manage-state --list 20

# Remove failed activities
poetry run manage-state --remove i12345
poetry run manage-state --remove i67890

# Re-run same command (will only process removed activities)
poetry run backfill-history --start-date 2024-01-01
```

## Performance Tips

1. **Parallel execution**: Don't run multiple backfill processes simultaneously (API rate limits)
2. **Network stability**: Use stable connection (avoid WiFi if possible)
3. **Provider selection**: Mistral API offers best balance for bulk processing
4. **Batch commits**: Default 10 is optimal (not too many commits, not too few)
5. **Monitoring**: Check progress regularly to catch issues early

## Integration with Workflow

The backfill tool integrates seamlessly with existing workflow:

- Uses `workflow-coach --auto` internally
- Respects `WorkflowState` tracking
- Creates proper git commits
- Works with all AI providers
- Compatible with `manage-state` tool

## Next Steps

After successful backfill:

1. Verify all activities analyzed: `poetry run manage-state --show`
2. Review analyses quality: `less logs/workouts-history.md`
3. Check git history: `git log --oneline -50`
4. Continue with regular workflow: `poetry run workflow-coach`

The backfill is a one-time operation. After completion, use the regular `workflow-coach` for new activities.
