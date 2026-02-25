# Guide: Workout Adherence Monitoring

**Version:** 1.0.0
**Date:** 5 janvier 2026
**Sprint:** R6 - PID Baseline & Calibration

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Installation](#installation)
3. [Usage Manuel](#usage-manuel)
4. [Configuration Cron](#configuration-cron)
5. [Intégration Sprint R6](#intégration-sprint-r6)
6. [Logs et Notifications](#logs-et-notifications)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'Ensemble

### Objectif

Le système de monitoring automatique détecte les **workouts sautés** en comparant:
- **Planifié** : Events WORKOUT dans Intervals.icu
- **Réalisé** : Activities effectivement complétées

### Cas d'Usage Sprint R6

Pour Sprint R6 (PID Baseline & Calibration), ce monitoring est **critique** car:
- Phase 1-2 (S075-S078): Collecte données baseline pour calibration PID
- Workouts sautés → données manquantes → calibration biaisée
- Détection automatique → action corrective immédiate
- Logging → traçabilité pour analyse post-sprint

### Fonctionnalités

- ✅ **Détection automatique** : Comparaison planned vs actual
- ✅ **Notifications temps réel** : Alertes si workout sauté
- ✅ **Logging structuré** : Historique adherence (JSONL)
- ✅ **Mode week** : Analyse adherence hebdomadaire
- ✅ **Integration cron** : Vérification quotidienne automatique (22:00)

---

## 🔧 Installation

### Prérequis

- Python 3.11+
- Poetry (dependency manager)
- Intervals.icu credentials configurés (`.env`)
- Cron (disponible sur macOS/Linux)

### Setup Scripts

Les scripts sont déjà disponibles dans le projet:

```bash
cd ~/cyclisme-training-logs

# Vérifier présence scripts
ls scripts/monitoring/
# Output:
# __init__.py
# check_workout_adherence.py
# setup_cron.sh
# remove_cron.sh
```

### Rendre Scripts Exécutables

```bash
chmod +x scripts/monitoring/setup_cron.sh
chmod +x scripts/monitoring/remove_cron.sh
chmod +x scripts/monitoring/check_workout_adherence.py
```

---

## 🧪 Usage Manuel

### Check Adherence Today

```bash
cd ~/cyclisme-training-logs
poetry run python scripts/monitoring/check_workout_adherence.py
```

**Output exemple:**

```
============================================================
🔍 Checking workout adherence for 2026-01-05
============================================================

📊 Adherence Summary:
   Status: ✅ COMPLETE
   Planned: 1 workouts
   Completed: 1 activities
   Adherence Rate: 100%

✅ All planned workouts completed!

📝 Results logged to: /Users/stephanejouve/data/monitoring/workout_adherence.jsonl
```

### Check Specific Date

```bash
poetry run python scripts/monitoring/check_workout_adherence.py --date 2026-01-04
```

### Check Entire Week

```bash
poetry run python scripts/monitoring/check_workout_adherence.py --week
```

**Output exemple:**

```
============================================================
📅 Weekly Adherence Check
============================================================

[... daily checks ...]

============================================================
📊 Weekly Summary (2025-W01)
============================================================
   Total Planned: 5 workouts
   Total Completed: 4 activities
   Total Skipped: 1 workouts
   Weekly Adherence: 80%
============================================================
```

### Dry-Run Mode (No Notifications)

```bash
poetry run python scripts/monitoring/check_workout_adherence.py --dry-run
```

---

## ⏰ Configuration Automatique

### macOS: launchd (Recommandé)

**Note:** Sur macOS, Apple recommande d'utiliser `launchd` plutôt que `cron` (deprecated).

#### Installation launchd Job

```bash
cd ~/cyclisme-training-logs
bash scripts/monitoring/setup_launchd.sh
```

**Output:**

```
==========================================
🔧 Setting up Workout Adherence Monitoring (launchd)
==========================================

📍 Project root: /Users/stephanejouve/cyclisme-training-logs
🐍 Python: /Users/stephanejouve/.pyenv/versions/3.11.0/bin/python
📦 Poetry: /usr/local/bin/poetry

📝 Generating launchd configuration...
✅ Configuration generated

📋 Installing launchd configuration...
🚀 Loading launchd job...
✅ launchd job loaded successfully!

✅ Setup complete!

📋 Schedule:
   - Runs daily at 22:00 (10:00 PM)
   - Checks if today's workouts were completed
   - Logs results to ~/data/monitoring/workout_adherence.jsonl
   - Sends notifications if workouts were skipped

📝 Logs:
   - Main output: ~/data/monitoring/launchd.log
   - Stdout: ~/data/monitoring/launchd.stdout.log
   - Stderr: ~/data/monitoring/launchd.stderr.log
```

#### Vérifier Installation (macOS)

```bash
# Check if job is loaded
launchctl list | grep workout_adherence

# Check job status
launchctl print gui/$(id -u)/com.cyclisme.workout_adherence

# View logs
tail -f ~/data/monitoring/launchd.log
```

#### Tester Manuellement (macOS)

```bash
# Force run immediately (without waiting for 22:00)
launchctl start com.cyclisme.workout_adherence

# Check results
tail ~/data/monitoring/launchd.log
```

#### Désinstaller (macOS)

```bash
bash scripts/monitoring/remove_launchd.sh
```

#### Avantages launchd

- ✅ **Natif macOS** : Recommandé par Apple
- ✅ **Gestion énergie** : Ne réveille pas Mac inutilement
- ✅ **Retry automatique** : Relance si échec
- ✅ **Logs intégrés** : Compatible `log show`
- ✅ **Permissions** : Cohérentes avec sécurité macOS
- ✅ **Environment** : Variables mieux gérées

---

## ⏰ Configuration Cron (Linux/Legacy)

**Note:** Pour macOS, utilisez `launchd` (voir section précédente). Cron est fourni pour compatibilité Linux ou legacy.

### Installation Cron Job

```bash
cd ~/cyclisme-training-logs
bash scripts/monitoring/setup_cron.sh
```

**Output:**

```
==========================================
🔧 Setting up Workout Adherence Monitoring
==========================================

📍 Project root: /Users/stephanejouve/cyclisme-training-logs
🐍 Python: /Users/stephanejouve/.pyenv/versions/3.11.0/bin/python

📝 Cron job to be installed:
0 22 * * * cd /Users/stephanejouve/cyclisme-training-logs && /path/to/python scripts/monitoring/check_workout_adherence.py >> ~/data/monitoring/cron.log 2>&1

✅ Cron job installed successfully!

📋 Schedule:
   - Runs daily at 22:00 (10:00 PM)
   - Checks if today's workouts were completed
   - Logs results to ~/data/monitoring/workout_adherence.jsonl
   - Sends notifications if workouts were skipped
```

### Vérifier Installation

```bash
crontab -l | grep check_workout_adherence
```

**Output:**

```
0 22 * * * cd /Users/stephanejouve/cyclisme-training-logs && /path/to/python scripts/monitoring/check_workout_adherence.py >> ~/data/monitoring/cron.log 2>&1
```

### Schedule Par Défaut

- **Quand:** Chaque jour à 22:00 (10:00 PM)
- **Pourquoi 22:00:** Laisse temps pour compléter workout (matin/après-midi/soir)
- **Fréquence:** Quotidienne (7 jours/semaine)

### Personnaliser Schedule

Éditer directement le crontab:

```bash
crontab -e
```

**Exemples de schedules alternatifs:**

```bash
# Tous les jours à 20:00
0 20 * * * cd ~/cyclisme-training-logs && poetry run python scripts/monitoring/check_workout_adherence.py

# Deux fois par jour (12:00 et 22:00)
0 12,22 * * * cd ~/cyclisme-training-logs && poetry run python scripts/monitoring/check_workout_adherence.py

# Seulement jours semaine (Lundi-Vendredi)
0 22 * * 1-5 cd ~/cyclisme-training-logs && poetry run python scripts/monitoring/check_workout_adherence.py

# Seulement weekend (Samedi-Dimanche) à 18:00
0 18 * * 6,7 cd ~/cyclisme-training-logs && poetry run python scripts/monitoring/check_workout_adherence.py
```

### Désinstaller Cron Job

```bash
bash scripts/monitoring/remove_cron.sh
```

---

## 🔬 Intégration Sprint R6

### Phase 1: Observation (S075-S076)

**Objectif:** Collecter 2 semaines de données baseline sans intervention

**Monitoring requis:**
- ✅ Check quotidien adherence (cron 22:00)
- ✅ Alertes si workout sauté
- ✅ Logging structuré pour analyse

**Workflow:**

1. **22:00 chaque soir** → Cron vérifie adherence
2. **Si workout sauté** → Notification immédiate
3. **Action MOA** → Décider si:
   - Skip intentionnel (fatigue, repos forcé) → Update status
   - Skip oublié → Rattrapage possible?
   - Skip pattern → Ajuster planning S076+
4. **Logging** → Données pour calibration PID

### Phase 2: Calibration (S077-S078)

**Objectif:** Calibrer coefficients PID (Kp, Ki, Kd)

**Importance adherence:**
- Données manquantes → calibration biaisée
- Ratio adherence < 90% → recalibration required
- Monitoring détecte problèmes early

### Phase 3: Hybrid Mode (S079-S080)

**Objectif:** Tester PID avec validation MOA

**Monitoring critique:**
- Détection écarts PID predictions vs reality
- Feedback loop pour ajustements
- Validation adherence dashboard MOA

---

## 📊 Logs et Notifications

### Format Logs (JSONL)

**Fichier:** `~/data/monitoring/workout_adherence.jsonl`

**Structure:**

```json
{
  "date": "2026-01-05",
  "planned_workouts": 1,
  "completed_activities": 1,
  "skipped_workouts": [],
  "adherence_rate": 1.0,
  "status": "COMPLETE",
  "timestamp": "2026-01-05T22:00:15.123456"
}
```

**Exemple workout sauté:**

```json
{
  "date": "2026-01-07",
  "planned_workouts": 1,
  "completed_activities": 0,
  "skipped_workouts": [
    {
      "id": 123456,
      "name": "S075-03 Endurance 90min Z2",
      "start_time": "2026-01-07T10:00:00"
    }
  ],
  "adherence_rate": 0.0,
  "status": "MISSED",
  "timestamp": "2026-01-07T22:00:30.456789"
}
```

### Consulter Logs

```bash
# Tous les logs
cat ~/data/monitoring/workout_adherence.jsonl

# Dernières 10 entrées
tail -10 ~/data/monitoring/workout_adherence.jsonl

# Filtrer workouts sautés
cat ~/data/monitoring/workout_adherence.jsonl | jq 'select(.status != "COMPLETE")'

# Calculer adherence moyenne
cat ~/data/monitoring/workout_adherence.jsonl | jq -s 'map(.adherence_rate) | add / length'
```

### Notifications

**Format notification (workout sauté):**

```
============================================================
🚨 WORKOUT ADHERENCE ALERT
============================================================

⚠️  1 workout(s) were skipped on 2026-01-07

Skipped workouts:
  • S075-03 Endurance 90min Z2

💡 Recommended Actions:
   1. Review reason for skip (fatigue, schedule, etc.)
   2. Update session status if intentional:
      poetry run update-session --status skipped --reason 'Your reason'
   3. Consider rescheduling if needed
   4. Update baseline data for PID calibration

============================================================
```

**Où apparaît notification:**
- Terminal output (si run manuel)
- Cron log: `~/data/monitoring/cron.log`
- Email/SMS (extension future si configuré)

### Consulter Cron Logs

```bash
# Logs en temps réel
tail -f ~/data/monitoring/cron.log

# Dernières 50 lignes
tail -50 ~/data/monitoring/cron.log

# Chercher alertes
grep "WORKOUT ADHERENCE ALERT" ~/data/monitoring/cron.log
```

---

## 🔧 Troubleshooting

### Problème: Cron Job Ne Run Pas

**Symptômes:**
- Pas de nouvelles entrées dans `workout_adherence.jsonl`
- `cron.log` vide ou ancien

**Solutions:**

1. **Vérifier cron installé:**
   ```bash
   crontab -l | grep check_workout_adherence
   ```

2. **Vérifier chemins absolus:**
   ```bash
   # Tester commande cron manuellement
   cd /Users/stephanejouve/cyclisme-training-logs
   poetry run python scripts/monitoring/check_workout_adherence.py
   ```

3. **Vérifier permissions:**
   ```bash
   ls -la scripts/monitoring/check_workout_adherence.py
   # Should be executable: -rwxr-xr-x
   ```

4. **Vérifier cron daemon (macOS):**
   ```bash
   # Check if cron is running
   ps aux | grep cron
   ```

5. **Réinstaller cron job:**
   ```bash
   bash scripts/monitoring/remove_cron.sh
   bash scripts/monitoring/setup_cron.sh
   ```

### Problème: Faux Positifs (Workouts Marqués Sautés)

**Symptômes:**
- Workout completed mais marqué "skipped"

**Causes possibles:**

1. **Nom workout différent:**
   - Planned: "S075-02 Endurance Z2"
   - Actual activity: "Morning ride easy"
   - Solution: Utiliser matching name ou workout_id

2. **Délai sync Intervals.icu:**
   - Activity uploadée mais pas encore synced
   - Solution: Attendre 5-10min, re-run check

3. **Activity sans workout_id reference:**
   - Activity manuelle sans link vers planned workout
   - Solution: Ajouter workout_id lors upload

**Fix:**

```bash
# Re-check avec délai
sleep 300  # Wait 5min
poetry run python scripts/monitoring/check_workout_adherence.py --date 2026-01-05
```

### Problème: Credentials Intervals.icu

**Symptômes:**
- Error: "Authentication failed"
- Error: "Could not fetch events"

**Solutions:**

1. **Vérifier `.env`:**
   ```bash
   cat .env | grep INTERVALS
   # Should show:
   # VITE_INTERVALS_ATHLETE_ID=iXXXXXX
   # VITE_INTERVALS_API_KEY=your_key
   ```

2. **Tester API manuellement:**
   ```bash
   poetry run python -c "from cyclisme_training_logs.api.intervals_client import IntervalsClient; from cyclisme_training_logs.config.config_base import ConfigBase; c = ConfigBase(); client = IntervalsClient(c.intervals_athlete_id, c.intervals_api_key); print(client.get_athlete_profile())"
   ```

3. **Regénérer API key:**
   - Login intervals.icu
   - Settings → Developer → Generate new API key
   - Update `.env`

### Problème: Logs Trop Volumineux

**Symptômes:**
- `workout_adherence.jsonl` > 100MB
- `cron.log` très gros

**Solutions:**

1. **Rotation logs (workout_adherence.jsonl):**
   ```bash
   # Archive old logs
   cd ~/data/monitoring
   mv workout_adherence.jsonl workout_adherence_archive_$(date +%Y%m%d).jsonl
   touch workout_adherence.jsonl
   ```

2. **Rotation cron.log:**
   ```bash
   # Truncate cron log
   > ~/data/monitoring/cron.log

   # Ou avec archivage
   mv ~/data/monitoring/cron.log ~/data/monitoring/cron_archive_$(date +%Y%m%d).log
   touch ~/data/monitoring/cron.log
   ```

3. **Automatiser rotation (logrotate):**
   ```bash
   # Create logrotate config
   cat > /tmp/monitoring_logrotate.conf <<EOF
   /Users/stephanejouve/data/monitoring/*.log {
       weekly
       rotate 4
       compress
       missingok
       notifempty
   }
   /Users/stephanejouve/data/monitoring/*.jsonl {
       monthly
       rotate 12
       compress
       missingok
       notifempty
   }
   EOF

   # Add to crontab
   # 0 0 * * 0 /usr/sbin/logrotate /tmp/monitoring_logrotate.conf
   ```

---

## 📈 Métriques et Analyse

### Calculer Adherence Rate Globale

```bash
# Average adherence rate (all time)
cat ~/data/monitoring/workout_adherence.jsonl | jq -s 'map(.adherence_rate) | add / length'

# Output: 0.92 (92% adherence)
```

### Adherence Par Semaine

```bash
# Week S075
cat ~/data/monitoring/workout_adherence.jsonl | jq 'select(.date | startswith("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-10", "2026-01-11"))'
```

### Identifier Patterns Skips

```bash
# List all skipped workouts
cat ~/data/monitoring/workout_adherence.jsonl | jq 'select(.status != "COMPLETE") | {date, skipped: .skipped_workouts[].name}'

# Count skips by day of week
cat ~/data/monitoring/workout_adherence.jsonl | jq -r 'select(.status != "COMPLETE") | .date' | xargs -I {} date -j -f "%Y-%m-%d" {} "+%A" | sort | uniq -c
```

### Export pour Analyse

```bash
# Convert to CSV
cat ~/data/monitoring/workout_adherence.jsonl | jq -r '[.date, .planned_workouts, .completed_activities, .adherence_rate, .status] | @csv' > ~/data/monitoring/adherence_export.csv

# Import dans Excel/Google Sheets pour analyse
```

---

## 🎯 Best Practices

### Sprint R6 Workflow Recommandé

1. **Setup initial (Dimanche soir pré-S075):**
   ```bash
   bash scripts/monitoring/setup_cron.sh
   ```

2. **Check quotidien matin (après cron 22:00):**
   ```bash
   tail -20 ~/data/monitoring/cron.log
   ```

3. **Si workout sauté détecté:**
   - Analyser raison (fatigue? schedule?)
   - Décision MOA: skip intentionnel ou rattrapage
   - Update status si skip intentionnel:
     ```bash
     poetry run update-session --week S075 --session S075-02 --status skipped --reason "Fatigue excessive" --sync
     ```

4. **Review hebdomadaire (Dimanche):**
   ```bash
   poetry run python scripts/monitoring/check_workout_adherence.py --week
   ```

5. **Post-sprint analysis (fin S080):**
   ```bash
   cat ~/data/monitoring/workout_adherence.jsonl | jq 'select(.date >= "2026-01-05" and .date <= "2026-02-15")'
   ```

### Intégration Baseline Collector

Le monitoring adherence alimente le `BaselineCollector` (Sprint R6):

```python
# cyclisme_training_logs/intelligence/baseline_collector.py
from pathlib import Path
import json

def load_adherence_data(week_id: str) -> float:
    """Load adherence rate for week from monitoring logs."""
    log_file = Path.home() / "data" / "monitoring" / "workout_adherence.jsonl"

    # Parse week dates
    week_start = parse_week_id(week_id)  # S075 -> 2026-01-05
    week_end = week_start + timedelta(days=6)

    # Load adherence data
    adherence_rates = []
    with open(log_file) as f:
        for line in f:
            data = json.loads(line)
            date = datetime.fromisoformat(data["date"])
            if week_start <= date <= week_end:
                adherence_rates.append(data["adherence_rate"])

    return sum(adherence_rates) / len(adherence_rates) if adherence_rates else 1.0
```

---

## 📚 Références

### Scripts

- `scripts/monitoring/check_workout_adherence.py` - Script principal
- `scripts/monitoring/setup_cron.sh` - Installation cron
- `scripts/monitoring/remove_cron.sh` - Désinstallation cron

### Documentation Connexe

- [GUIDE_INTELLIGENCE.md](GUIDE_INTELLIGENCE.md) - Training Intelligence & PID
- [ROADMAP.md](../../ROADMAP.md) - Sprint R6 specification
- [SESSION_20260105_SPRINT_R6_PLANNING.md](../sessions/SESSION_20260105_SPRINT_R6_PLANNING.md) - Sprint R6 planning

### API

- [Intervals.icu API Docs](https://intervals.icu/api)
- [IntervalsClient](../../cyclisme_training_logs/api/intervals_client.py)

---

## 📞 Support

**Questions?**
- Voir [ROADMAP.md Sprint R6](../../ROADMAP.md#sprint-r6--pid-baseline--calibration)
- Ouvrir issue GitHub

**Bugs?**
- Tester manuellement: `poetry run python scripts/monitoring/check_workout_adherence.py`
- Vérifier logs: `tail ~/data/monitoring/cron.log`
- Vérifier cron: `crontab -l`

---

**Document créé par:** Claude Code
**Date:** 2026-01-05
**Version:** 1.0.0
**Sprint:** R6 - PID Baseline & Calibration
