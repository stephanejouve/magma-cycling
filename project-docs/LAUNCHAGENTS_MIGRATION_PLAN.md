# 🔄 LaunchAgents - Plan de Migration

**Date**: 25 janvier 2026
**Objectif**: Adopter convention de nommage claire et séquencement lisible

---

## 🎯 CONVENTION DE NOMMAGE

### Format Standard
```
com.cyclisme.{CATEGORY}.{SEQUENCE}-{NAME}-{SCHEDULE}
```

**Composants**:
- **PREFIX**: `com.cyclisme` (uniformisé pour tous)
- **CATEGORY**: Catégorie fonctionnelle (4 lettres lowercase)
- **SEQUENCE**: Ordre d'exécution (10, 20, 30...) avec gaps de 10
- **NAME**: Fonction descriptive (lowercase, hyphens)
- **SCHEDULE**: Fréquence/horaire (daily-21h30, weekly-sun-20h, hourly)

**Catégories**:
- `rept` = Reporting (email, rapports)
- `mon` = Monitoring (collecte métriques)
- `anls` = Analysis (traitement intelligence)
- `flow` = Workflow (processus complets multi-étapes)
- `mnt` = Maintenance (nettoyage, sync)

---

## 📋 MAPPING ANCIEN → NOUVEAU

### REPORTING (Email/Rapports)

```
ANCIEN: com.traininglogs.dailysync
NOUVEAU: com.cyclisme.rept.10-daily-sync-21h30

Fichier: ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
Command: poetry run daily-sync --send-email --ai-analysis --auto-servo
Schedule: Daily 21:30
Status: ✅ Actif → Migrer
```

---

### MONITORING (Collecte Données)

```
ANCIEN: com.cyclisme.workout_adherence
NOUVEAU: com.cyclisme.mon.10-adherence-daily-22h

Fichier: ~/Library/LaunchAgents/com.cyclisme.mon.10-adherence-daily-22h.plist
Command: ./scripts/monitoring/run_adherence_check.sh
Schedule: Daily 22:00
Status: ✅ Actif → Migrer
```

---

### ANALYSIS (Intelligence AI)

```
ANCIEN: com.cyclisme.pid_evaluation
NOUVEAU: com.cyclisme.anls.10-pid-evaluation-daily-23h

Fichier: ~/Library/LaunchAgents/com.cyclisme.anls.10-pid-evaluation-daily-23h.plist
Command: ./scripts/monitoring/run_pid_evaluation.sh
Schedule: Daily 23:00
Status: ❌ Non chargé → Créer + Charger
```

---

### WORKFLOW (Processus Complets)

```
ANCIEN: com.traininglogs.endofweek
NOUVEAU: com.cyclisme.flow.10-end-of-week-sun-20h

Fichier: ~/Library/LaunchAgents/com.cyclisme.flow.10-end-of-week-sun-20h.plist
Command: poetry run end-of-week --auto-calculate --provider claude_api --auto
Schedule: Sunday 20:00
Status: ✅ Actif → Migrer
```

---

### MAINTENANCE (Nettoyage/Sync)

```
ANCIEN: com.cyclisme.project-cleaner
NOUVEAU: com.cyclisme.mnt.10-project-clean-daily

Fichier: ~/Library/LaunchAgents/com.cyclisme.mnt.10-project-clean-daily.plist
Command: cd ~/cyclisme-training-logs && poetry run project-clean
Schedule: Every 24h
Status: ✅ Actif → Migrer
```

```
ANCIEN: com.cyclisme.sync-docs-icloud
NOUVEAU: com.cyclisme.mnt.20-sync-docs-hourly

Fichier: ~/Library/LaunchAgents/com.cyclisme.mnt.20-sync-docs-hourly.plist
Command: ./scripts/maintenance/sync_docs_icloud.sh
Schedule: Every 1h
Status: ✅ Actif → Migrer
```

```
ANCIEN: com.user.sync.cyclisme
NOUVEAU: com.cyclisme.mnt.30-rsync-sites-hourly

Fichier: ~/Library/LaunchAgents/com.cyclisme.mnt.30-rsync-sites-hourly.plist
Command: rsync -av --delete ~/cyclisme-training-logs/docs/_build/html/ ~/Sites/cyclisme-training-logs/
Schedule: Every 1h
Status: ✅ Actif → Migrer
```

---

## 📊 RÉSULTAT FINAL

### Nouveau Listing (Alphabétique)

```bash
$ launchctl list | grep cyclisme

com.cyclisme.anls.10-pid-evaluation-daily-23h
com.cyclisme.flow.10-end-of-week-sun-20h
com.cyclisme.mnt.10-project-clean-daily
com.cyclisme.mnt.20-sync-docs-hourly
com.cyclisme.mnt.30-rsync-sites-hourly
com.cyclisme.mon.10-adherence-daily-22h
com.cyclisme.rept.10-daily-sync-21h30
```

### Workflow Chronologique (Immédiatement Visible)

```
QUOTIDIEN:
21:30 → rept.10 (daily-sync)         → Email rapport
22:00 → mon.10  (adherence)          → Collecte métriques
23:00 → anls.10 (pid-evaluation)     → Intelligence AI

HEBDOMADAIRE:
Sun 20:00 → flow.10 (end-of-week)    → Planning semaine

MAINTENANCE:
Hourly → mnt.20 (sync-docs)          → iCloud sync
Hourly → mnt.30 (rsync-sites)        → Web docs
Daily  → mnt.10 (project-clean)      → Nettoyage
```

---

## 🔧 PROCÉDURE DE MIGRATION

### Étape 1: Créer Nouveaux .plist

```bash
cd ~/cyclisme-training-logs/scripts/launchagents

# Créer nouveaux fichiers avec nouvelle convention
./create_new_plists.sh
```

Script génère:
- `com.cyclisme.rept.10-daily-sync-21h30.plist`
- `com.cyclisme.mon.10-adherence-daily-22h.plist`
- `com.cyclisme.anls.10-pid-evaluation-daily-23h.plist`
- `com.cyclisme.flow.10-end-of-week-sun-20h.plist`
- `com.cyclisme.mnt.10-project-clean-daily.plist`
- `com.cyclisme.mnt.20-sync-docs-hourly.plist`
- `com.cyclisme.mnt.30-rsync-sites-hourly.plist`

### Étape 2: Copier vers ~/Library/LaunchAgents

```bash
cp scripts/launchagents/*.plist ~/Library/LaunchAgents/
```

### Étape 3: Charger Nouveaux (Sans Décharger Anciens)

```bash
# Charger nouveaux en parallèle des anciens
launchctl load ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.mon.10-adherence-daily-22h.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.anls.10-pid-evaluation-daily-23h.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.flow.10-end-of-week-sun-20h.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.mnt.10-project-clean-daily.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.mnt.20-sync-docs-hourly.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.mnt.30-rsync-sites-hourly.plist
```

### Étape 4: Validation (48h)

Observer que:
- ✅ Emails arrivent à 21h30 (daily-sync)
- ✅ Adherence collecté à 22h00
- ✅ PID evaluation à 23h00 (NOUVEAU!)
- ✅ Planning dimanche 20h00
- ✅ Logs générés correctement

### Étape 5: Désactiver Anciens

```bash
# Après validation (48h)
launchctl unload ~/Library/LaunchAgents/com.traininglogs.dailysync.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.workout_adherence.plist
launchctl unload ~/Library/LaunchAgents/com.traininglogs.endofweek.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
launchctl unload ~/Library/LaunchAgents/com.user.sync.cyclisme.plist
```

### Étape 6: Archiver Anciens (7 jours après)

```bash
# Créer backup avant suppression
mkdir -p ~/Library/LaunchAgents/.archived-$(date +%Y%m%d)

mv ~/Library/LaunchAgents/com.traininglogs.*.plist ~/Library/LaunchAgents/.archived-$(date +%Y%m%d)/
mv ~/Library/LaunchAgents/com.user.sync.cyclisme.plist ~/Library/LaunchAgents/.archived-$(date +%Y%m%d)/

# Anciens com.cyclisme.* déjà déchargés, pas besoin de bouger si pas chargés
```

---

## 🎯 BÉNÉFICES POST-MIGRATION

### 1. Clarté Immédiate

**Avant**:
```
com.traininglogs.dailysync           → ???
com.cyclisme.workout_adherence       → ???
com.cyclisme.pid_evaluation          → ???
```

**Après**:
```
com.cyclisme.rept.10-daily-sync-21h30        → Reporting, seq 10, daily 21h30
com.cyclisme.mon.10-adherence-daily-22h      → Monitoring, seq 10, daily 22h
com.cyclisme.anls.10-pid-evaluation-daily-23h → Analysis, seq 10, daily 23h
```

### 2. Documentation Auto-Générée

```bash
# Script utilitaire: scripts/monitoring/list-agents.sh

REPORTING
  ✓ rept.10-daily-sync-21h30

MONITORING
  ✓ mon.10-adherence-daily-22h

ANALYSIS
  ✓ anls.10-pid-evaluation-daily-23h

WORKFLOW
  ✓ flow.10-end-of-week-sun-20h

MAINTENANCE
  ✓ mnt.10-project-clean-daily
  ✓ mnt.20-sync-docs-hourly
  ✓ mnt.30-rsync-sites-hourly
```

### 3. Évolutivité

**Insertion facile**:
```
Si besoin nouveau agent entre daily-sync et adherence:
→ Créer rept.15-new-report-21h45 (entre rept.10 et mon.10)
→ Pas de renommage nécessaire (gaps de 10)
```

### 4. baseline_preliminary.py Intégration

**Nouvelle position**:
```
ANALYSIS Category:
  ├─ anls.10-pid-evaluation-daily-23h    (existant, daily)
  ├─ anls.20-baseline-weekly-dim-23h30  (FUTUR - Sprint R10?)
  └─ anls.30-baseline-manual             (manuel, on-demand)
```

---

## ⚠️ ATTENTION: PID Evaluation

**Point Critique**: `com.cyclisme.pid_evaluation` **n'est PAS chargé** actuellement!

Migration = **Opportunité de l'activer**:
```bash
# Lors de la migration, CHARGER le nouveau:
launchctl load ~/Library/LaunchAgents/com.cyclisme.anls.10-pid-evaluation-daily-23h.plist

# Vérifier qu'il tourne bien à 23h00:
tail -f ~/data/monitoring/pid_evaluation.stdout.log
```

---

## 📝 CHECKLIST MIGRATION

- [ ] Créer 7 nouveaux .plist avec convention
- [ ] Copier vers ~/Library/LaunchAgents/
- [ ] Charger nouveaux (launchctl load)
- [ ] Vérifier listing: `launchctl list | grep cyclisme`
- [ ] Attendre 48h validation
- [ ] Observer logs chaque agent
- [ ] Désactiver anciens (launchctl unload)
- [ ] Attendre 7j rollback window
- [ ] Archiver anciens .plist
- [ ] Mettre à jour docs projet
- [ ] Commit migration

---

## 🎯 TIMELINE RECOMMANDÉE

**Samedi 25 janvier (Aujourd'hui)**:
- 14h00: Créer nouveaux .plist
- 14h30: Copier + charger nouveaux
- 21h30: Vérifier daily-sync (nouveau)
- 22h00: Vérifier adherence (nouveau)
- 23h00: Vérifier pid-evaluation (PREMIER RUN!)

**Dimanche 26 janvier**:
- 20h00: Vérifier end-of-week (nouveau)
- Observation logs toute la journée

**Lundi 27 janvier**:
- Validation workflow complet 24h
- Décision: garder nouveaux ou rollback

**Mardi 28 janvier** (si validation OK):
- Désactiver anciens agents
- Documentation mise à jour

**Mardi 4 février** (7j après):
- Archiver anciens .plist
- Nettoyage complet
- Commit final migration

---

**Prêt à générer les nouveaux .plist ?** 🎯
