# 🔄 LaunchAgents Migration - Nouvelle Convention de Nommage

**Date**: 25 janvier 2026
**Status**: ✅ Prêt pour migration

---

## 📋 CONTENU DOSSIER

### Fichiers .plist (7)
```
com.cyclisme.rept.10-daily-sync-21h30.plist            ✅ Validé
com.cyclisme.mon.10-adherence-daily-22h.plist          ✅ Validé
com.cyclisme.anls.10-pid-evaluation-daily-23h.plist    ✅ Validé
com.cyclisme.flow.10-end-of-week-sun-20h.plist         ✅ Validé
com.cyclisme.mnt.10-project-clean-daily.plist          ✅ Validé
com.cyclisme.mnt.20-sync-docs-hourly.plist             ✅ Validé
com.cyclisme.mnt.30-rsync-sites-hourly.plist           ✅ Validé
```

### Scripts Utilitaires (9)
```
start-migration.sh              🚀 POINT D'ENTRÉE - Lance migration automatique
validate-plists.sh              Validation syntaxe .plist (plutil)
phase1-install-new-agents.sh    Phase 1: Installation nouveaux agents
phase2-unload-old-agents.sh     Phase 2: Désactivation anciens
phase3-archive-old-agents.sh    Phase 3: Archivage anciens
migration-phase2-checker.sh     Checker auto Phase 2 (48h)
migration-phase3-checker.sh     Checker auto Phase 3 (7j)
list-agents.sh                  Listing état agents
```

### Agents de Migration (3)
```
com.cyclisme.migration.10-phase1-install-now.plist      Phase 1 (RunAtLoad)
com.cyclisme.migration.20-phase2-unload-48h.plist       Phase 2 (auto 48h)
com.cyclisme.migration.30-phase3-archive-7d.plist       Phase 3 (auto 7j)
```

---

## 🎯 MIGRATION AUTOMATIQUE EN 3 PHASES

### 🚀 Démarrage (Une seule commande !)

```bash
cd ~/magma-cycling/scripts/launchagents

# 1. Validation préalable (optionnel mais recommandé)
./validate-plists.sh

# 2. Lancer migration automatique
./start-migration.sh
```

**C'est tout !** Le système s'occupe du reste :
- Phase 1 s'exécute immédiatement
- Phase 2 se déclenche automatiquement dans 48h
- Phase 3 se déclenche automatiquement 7j après Phase 2

---

### Phase 1: Installation (Automatique - Immédiat)

**Exécution**: Agent `migration.10-phase1-install-now` (RunAtLoad)
**Script**: `phase1-install-new-agents.sh`
**Résultat**: 7 nouveaux agents chargés + anciens encore actifs

---

### Phase 2: Désactivation (Automatique - 48h après Phase 1)

**Observation critique pendant 48h**:
- ✅ Email 21h30 reçu (daily-sync)
- ✅ Adherence collecté 22h00
- ✅ PID evaluation 23h00 (NOUVEAU - premiers runs!)
- ✅ Planning dimanche 20h00

**Logs à surveiller**:
```bash
# Migration
tail -f ~/Library/Logs/cyclisme-migration-phase2.log

# Daily-sync
tail -f ~/Library/Logs/cyclisme-rept-daily-sync.log

# Adherence
tail -f ~/data/monitoring/launchd.stdout.log

# PID Evaluation (NOUVEAU!)
tail -f ~/data/monitoring/pid_evaluation.stdout.log

# End-of-week
tail -f ~/Library/Logs/cyclisme-flow-endofweek.log
```

**Exécution automatique**: Agent `migration.20-phase2-unload-48h` vérifie toutes les heures
**Script**: `migration-phase2-checker.sh` → `phase2-unload-old-agents.sh`
**Résultat**: Anciens agents désactivés, se désactive lui-même

**Manuel (si nécessaire)**:
```bash
./phase2-unload-old-agents.sh
```

---

### Phase 3: Archivage (Automatique - 7j après Phase 2)

**Exécution automatique**: Agent `migration.30-phase3-archive-7d` vérifie toutes les 12h
**Script**: `migration-phase3-checker.sh` → `phase3-archive-old-agents.sh`
**Résultat**: Anciens .plist archivés, se désactive lui-même

Archives créées dans:
```
~/Library/LaunchAgents/.archived-YYYYMMDD/
```

**Manuel (si nécessaire)**:
```bash
./phase3-archive-old-agents.sh
```

---

## 🏗️ ARCHITECTURE NOUVELLE CONVENTION

### Format
```
com.cyclisme.{CATEGORY}.{SEQUENCE}-{NAME}-{SCHEDULE}
```

### Catégories
- `rept` = Reporting (email, rapports)
- `mon` = Monitoring (collecte métriques)
- `anls` = Analysis (intelligence AI)
- `flow` = Workflow (processus multi-étapes)
- `mnt` = Maintenance (nettoyage, sync)

### Séquence
- Numéros: 10, 20, 30... (gaps de 10 pour insertion future)
- Indique ordre d'exécution dans la catégorie

### Schedule
- `daily-21h30` = Quotidien 21:30
- `sun-20h` = Dimanche 20:00
- `hourly` = Toutes les heures
- `daily` = Quotidien (StartInterval)

---

## 📊 WORKFLOW APRÈS MIGRATION

### Quotidien
```
21:30 → rept.10-daily-sync-21h30          Email + analyses AI
22:00 → mon.10-adherence-daily-22h        Collecte adherence
23:00 → anls.10-pid-evaluation-daily-23h  Intelligence 7j
```

### Hebdomadaire
```
Sun 20:00 → flow.10-end-of-week-sun-20h   Planning semaine
```

### Maintenance
```
Hourly → mnt.20-sync-docs-hourly          iCloud sync
Hourly → mnt.30-rsync-sites-hourly        Web docs
Daily  → mnt.10-project-clean-daily       Nettoyage
```

---

## 🆕 NOUVEAUTÉS POST-MIGRATION

### 1. PID Evaluation Actif ⭐

**AVANT**: Non chargé (fichier dormant dans repo)
**APRÈS**: Actif quotidien 23h00

**Impact**:
- Intelligence AI quotidienne automatique
- Learnings, patterns, adaptations générés chaque soir
- Détection opportunités tests FTP
- Output: `~/data/intelligence.json`

### 2. Intégration baseline_preliminary.py

**Position future**:
```
ANALYSIS (anls)
├─ anls.10-pid-evaluation-daily-23h      (quotidien)
├─ anls.20-baseline-weekly-dim-23h30     (Sprint R10 - futur)
└─ anls.30-baseline-manual               (manuel, on-demand)
```

**Gap de 10** permet insertion facile hebdomadaire sans tout renommer.

---

## 🔧 COMMANDES UTILES

### Listing Agents
```bash
# Voir tous agents cyclisme
launchctl list | grep cyclisme

# Détail avec status
./list-agents.sh

# Logs agent spécifique
launchctl list com.cyclisme.rept.10-daily-sync-21h30
```

### Debug
```bash
# Forcer exécution immédiate (test)
launchctl start com.cyclisme.rept.10-daily-sync-21h30

# Recharger après modification .plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
```

### Rollback (Si Problème)
```bash
# Désactiver nouveaux
launchctl unload ~/Library/LaunchAgents/com.cyclisme.rept.10-daily-sync-21h30.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.mon.10-adherence-daily-22h.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.anls.10-pid-evaluation-daily-23h.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.flow.10-end-of-week-sun-20h.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.mnt.10-project-clean-daily.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.mnt.20-sync-docs-hourly.plist
launchctl unload ~/Library/LaunchAgents/com.cyclisme.mnt.30-rsync-sites-hourly.plist

# Anciens déjà actifs - aucune action requise
```

---

## 📚 DOCUMENTATION RÉFÉRENCE

- **État actuel**: `../../project-docs/LAUNCHAGENTS_CURRENT_STATE.md`
- **Plan migration**: `../../project-docs/LAUNCHAGENTS_MIGRATION_PLAN.md`

---

## ✅ CHECKLIST MIGRATION

- [ ] Phase 1: Installation nouveaux agents
- [ ] Observation 24h: Tous agents tournent
- [ ] Observation 48h: Aucune erreur logs
- [ ] Phase 2: Désactivation anciens
- [ ] Observation 7j: Stabilité confirmée
- [ ] Phase 3: Archivage anciens .plist
- [ ] Commit migration dans git
- [ ] Mise à jour docs projet

---

**Prêt à migrer !** 🚀
