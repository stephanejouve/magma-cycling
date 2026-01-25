# End-of-Week One-Shot LaunchAgent

**Purpose:** Execute end-of-week workflow immediately (no waiting)

---

## 🚀 Quick Start

### 1. Install LaunchAgent
```bash
cp scripts/maintenance/com.cyclisme.end-of-week-oneshot.plist ~/Library/LaunchAgents/
```

### 2. Load (starts immediately)
```bash
launchctl load ~/Library/LaunchAgents/com.cyclisme.end-of-week-oneshot.plist
```

### 3. Wait for Notification
Tu recevras une notification macOS quand c'est fini:
```
✅ End-of-Week
Workflow end-of-week terminé! Voir logs.
```

### 4. Check Results
```bash
# View results
tail -100 ~/Library/Logs/end-of-week-oneshot.log

# View errors (if any)
tail -100 ~/Library/Logs/end-of-week-oneshot.error.log
```

---

## 🔧 How It Works

1. **Run immediately** (no sleep)
2. **Auto-calculate weeks** (S077 → S078)
3. **Weekly analysis** (Phase 2 - no interactive prompts)
4. **PID evaluation** (training intelligence learning)
5. **Weekly planner** (prompt generation)
6. **Claude API** (automatic workout generation)
7. **Upload to Intervals.icu** (7 workouts)
8. **Display notification** (macOS notification center)
9. **Auto-unload** (removes itself after execution)

---

## 📋 Workflow Steps

Le workflow execute automatiquement:

1. ✅ **Analyse S077** → 6 reports markdown
2. ✅ **Évaluation PID** → intelligence.json + monitoring
3. ✅ **Génération prompt** → S078 planning context
4. ✅ **Claude API call** → 7 workouts générés
5. ✅ **Validation** → format-planning check
6. ✅ **Upload Intervals.icu** → 7 workouts scheduled

---

## 🐛 Troubleshooting

### Check if LaunchAgent is running
```bash
launchctl list | grep end-of-week-oneshot
```

Expected output (while running):
```
-	0	com.cyclisme.end-of-week-oneshot
```

### Check logs in real-time
```bash
tail -f ~/Library/Logs/end-of-week-oneshot.log
```

### Cancel/Stop LaunchAgent
```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.end-of-week-oneshot.plist
```

---

## 📊 Expected Results

### If successful ✅
```
✅ WORKFLOW TERMINÉ AVEC SUCCÈS

  📊 Semaine analysée   : S077
  📅 Semaine planifiée  : S078
  🤖 Provider utilisé   : claude_api
  📁 Fichier workouts   : ~/cyclisme-training-logs/week-planning/S078_workouts.txt

  🎯 Prochaines étapes:
     1. Vérifiez les workouts dans Intervals.icu
     2. Ajustez si nécessaire avec workflow-coach en servo-mode
     3. Commitez les changements
```

### If errors ⚠️
```
❌ Erreur workflow : [error message]

Check logs:
  tail -100 ~/Library/Logs/end-of-week-oneshot.error.log
```

---

## 🔄 Run Again (if needed)

Si le workflow échoue ou pour refaire:

```bash
# Re-load LaunchAgent (starts immediately)
launchctl load ~/Library/LaunchAgents/com.cyclisme.end-of-week-oneshot.plist
```

---

## 🗑️ Cleanup (After Success)

LaunchAgent auto-unloads after execution, but you can remove it:

```bash
rm ~/Library/LaunchAgents/com.cyclisme.end-of-week-oneshot.plist
```

---

## ⚙️ Configuration

### Environment Variables Required

Dans ton `.env`:
```bash
# Claude API (required for --provider claude_api)
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514

# Intervals.icu (required for upload)
INTERVALS_API_KEY=...
INTERVALS_ATHLETE_ID=i151223
```

### Working Directory

Le workflow s'exécute dans:
```
/Users/stephanejouve/cyclisme-training-logs
```

---

## 📝 Notes

1. **Phase 2 System:**
   - Utilise `workflow_weekly.py` (moderne)
   - Pas de prompts interactifs
   - Compatible LaunchAgent

2. **Claude API:**
   - Génération automatique 7 workouts
   - Timeout: 30 min max
   - Coût: ~$0.50 par workflow

3. **Auto-unload:**
   - Le plist se supprime automatiquement
   - Pas besoin de cleanup manuel

---

**Created:** 25 Jan 2026, 23:30
**Transition:** S077 → S078
**Execution:** Immediate (no delay)
