# Guide Remise en Production - Cyclisme Training Logs

**Version** : 1.0.0  
**Date** : 11 décembre 2024  
**Durée estimée** : 2-3 heures

---

## 📋 Vue d'Ensemble

Ce guide vous accompagne pas à pas pour :
1. ✅ Valider que l'API fonctionne (déjà confirmé)
2. 🔧 Corriger les problèmes identifiés
3. 🧪 Tester le workflow complet
4. 📦 Archiver proprement l'ancien état
5. 🚀 Remettre en production

---

## ⏱️ Planning Recommandé

### Session 1 : Diagnostic & Backup (30 min)
- Lire DIAGNOSTIC_COMPLET.md
- Créer branche Git archive
- Backup état actuel

### Session 2 : Corrections (1h)
- Normaliser casse fichiers
- Appliquer patch détection source
- Tester individuellement

### Session 3 : Tests & Production (1h)
- Tests de non-régression
- Workflow complet
- Commit et push

---

## 🚀 Phase 1 : Préparation (30 min)

### 1.1 Lecture Diagnostic
```bash
cd ~/cyclisme-training-logs

# Copier les fichiers de diagnostic
cp /chemin/vers/DIAGNOSTIC_COMPLET.md ./docs/
cp /chemin/vers/PATCH_prepare_analysis.py ./scripts/patches/
cp /chemin/vers/normalize_weekly_reports_casing.py ./scripts/

# Lire le diagnostic
cat docs/DIAGNOSTIC_COMPLET.md | less
```

**⏱️ Durée** : 10 min

### 1.2 Archivage Git
```bash
# Créer branche archive avec état actuel
git checkout -b archive/pre-fix-20241211
git add -A
git commit -m "archive: État avant corrections du 11 décembre 2024

- Problèmes casse répertoires identifiés
- Détection source à améliorer
- Scripts de test accumulés
- API Intervals.icu fonctionnelle confirmée"

git push origin archive/pre-fix-20241211

# Tag de version
git tag -a v1.0-pre-fix -m "État avant corrections - 11 décembre 2024"
git push origin v1.0-pre-fix

# Revenir sur main
git checkout main
```

**⏱️ Durée** : 10 min

### 1.3 Backup Local
```bash
# Backup complet hors Git
cd ~/
tar -czf cyclisme-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  cyclisme-training-logs/ \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__'

# Vérifier backup
ls -lh cyclisme-backup-*.tar.gz | tail -1

# Déplacer dans lieu sûr
mv cyclisme-backup-*.tar.gz ~/Backups/  # Adapter selon votre config
```

**⏱️ Durée** : 10 min

**✅ Checkpoint 1** : Vous avez 3 sauvegardes (branche Git, tag, backup local)

---

## 🔧 Phase 2 : Corrections (1h)

### 2.1 Normalisation Casse Répertoires (15 min)

#### Test Dry-Run
```bash
cd ~/cyclisme-training-logs

# Simulation d'abord
python3 scripts/normalize_weekly_reports_casing.py --dry-run
```

**Attendu** :
```
📊 RÉSUMÉ ANALYSE
✅ Répertoires corrects : X
⚠️  Répertoires à corriger : Y
```

#### Application Réelle
```bash
# Si dry-run OK, appliquer
python3 scripts/normalize_weekly_reports_casing.py

# Répondre 'o' à la confirmation
```

**Attendu** :
```
💾 Création backup: weekly_reports.backup.casing_YYYYMMDD_HHMMSS
✅ Backup créé
🔧 Normalisation en cours...
✅ Renommé: s067 → S067
✅ Renommé: s070 → S070
```

#### Vérification
```bash
# Vérifier la structure
ls -l logs/weekly_reports/

# Attendu: Tous en majuscules (S067, S068, etc.)
```

**⏱️ Durée** : 15 min  
**✅ Checkpoint 2** : Tous les répertoires en majuscules

### 2.2 Amélioration Détection Source (25 min)

#### Backup Script Original
```bash
cd ~/cyclisme-training-logs/scripts
cp prepare_analysis.py prepare_analysis.py.backup.$(date +%Y%m%d)
```

#### Application Patch

**Option A : Manuel** (recommandé pour comprendre)
```bash
# Ouvrir prepare_analysis.py dans votre éditeur
nano prepare_analysis.py  # ou vim, code, etc.

# 1. Ajouter les nouvelles fonctions AVANT format_activity_data (ligne ~240)
#    Copier depuis PATCH_prepare_analysis.py:
#    - is_limited_data_source()
#    - format_limited_data_warning()

# 2. Remplacer format_activity_data (lignes 241-268)
#    Par format_activity_data_NOUVEAU()

# 3. Remplacer warning Strava (lignes 1068-1075)
#    Par code de main_PATCH_warning_display()

# Sauvegarder et quitter
```

**Option B : Script Automatique** (avancé)
```bash
# Si à l'aise avec sed/awk, créer script d'application automatique
# Sinon, utiliser Option A
```

#### Validation Syntaxe
```bash
# Vérifier pas d'erreur Python
python3 -m py_compile scripts/prepare_analysis.py

# Si erreur, restaurer backup
# cp scripts/prepare_analysis.py.backup.YYYYMMDD scripts/prepare_analysis.py
```

**⏱️ Durée** : 25 min  
**✅ Checkpoint 3** : prepare_analysis.py modifié sans erreur de syntaxe

### 2.3 Nettoyage Scripts Test (10 min)

```bash
cd ~/cyclisme-training-logs/scripts

# Créer répertoire archive
mkdir -p archive_tests_$(date +%Y%m%d)

# Déplacer scripts de test (sauf test_api.py et test_wellness.py)
mv test_14nov.py archive_tests_*/
mv test_7days.py archive_tests_*/
mv test_activity_details.py archive_tests_*/
mv test_all_fields.py archive_tests_*/
mv test_create_event.py archive_tests_*/
mv test_filters.py archive_tests_*/
mv test_rest_and_cancellations.py archive_tests_*/
mv test_weekly_corrections.py archive_tests_*/
mv test_weekly_parser.py archive_tests_*/

# Garder uniquement
ls test_*.py
# Attendu: test_api.py test_wellness.py

# Archiver aussi scripts obsolètes
mv debug_detection.py archive_tests_*/
mv demo_rest_handling.py archive_tests_*/
mv apply_workflow_patch_final.py archive_tests_*/
```

**⏱️ Durée** : 10 min  
**✅ Checkpoint 4** : Scripts tests archivés

### 2.4 Commit Corrections (10 min)

```bash
cd ~/cyclisme-training-logs

# Vérifier changements
git status

# Staging
git add -A

# Commit avec message descriptif
git commit -m "fix: Corrections majeures système

- Normalisation casse répertoires (S067 standard)
- Amélioration détection source activités
- Archivage scripts test obsolètes
- Fonction is_limited_data_source() ajoutée

Fixes #1 (adapter numéro issue si existant)

Voir docs/DIAGNOSTIC_COMPLET.md pour détails"

# Push
git push origin main
```

**⏱️ Durée** : 10 min  
**✅ Checkpoint 5** : Corrections committées

---

## 🧪 Phase 3 : Tests de Non-Régression (1h)

### 3.1 Test API Connection (5 min)

```bash
cd ~/cyclisme-training-logs/scripts

# Test connexion API
python3 test_api.py
```

**Attendu** :
```json
{
  "id": "iXXXXXXXX",
  "type": "VirtualRide",
  "icu_training_load": XX,
  "source": "UPLOAD",
  ...
}
```

**✅ Si OK** : API fonctionnelle  
**❌ Si KO** : Vérifier credentials dans `~/.intervals_config.json`

### 3.2 Test Détection Source - Activité Zwift (10 min)

```bash
# Test avec activité UPLOAD (données complètes)
python3 prepare_analysis.py --activity-id i107093941
```

**Attendu** :
```
🔍 Recherche du workout planifié...
✅ Données complètes disponibles

📖 Chargement du contexte...
✍️  Génération du prompt...
📋 Prompt copié dans le presse-papier !
```

**Validation** :
- ✅ Pas de warning "données limitées"
- ✅ Message "Données complètes disponibles"
- ✅ Prompt généré sans erreur

### 3.3 Test Détection Source - Activité Strava (10 min)

```bash
# Test avec activité Strava (données limitées)
python3 prepare_analysis.py --activity-id 16457456654
```

**Attendu** :
```
⚠️  ATTENTION : Données limitées
   Raison : Source Strava avec restrictions API
   
   Recommandations :
   • Vérifier les métriques sur Intervals.icu web
   • Les données de puissance peuvent être manquantes
   • Utiliser les données disponibles pour analyse qualitative
```

**Validation** :
- ✅ Warning affiché clairement
- ✅ Recommandations présentes
- ✅ Prompt généré malgré limitations

### 3.4 Test Workflow Complet (20 min)

```bash
# Workflow orchestré complet
python3 workflow_coach.py
```

**Étapes attendues** :
1. ✅ Détection gaps (séances non analysées)
2. ✅ Option collecte feedback
3. ✅ Génération prompt
4. ✅ Copie presse-papier
5. ✅ Instructions Claude.ai
6. ✅ Validation réponse
7. ✅ Insertion analyse
8. ✅ Commit Git (optionnel)

**Tester avec** :
- Une activité Zwift récente
- Feedback athlète simulé
- Analyse complète

### 3.5 Test Analyse Hebdomadaire (10 min)

```bash
# Test génération bilan hebdo
python3 weekly_analysis.py --week S070
```

**Attendu** :
```
📊 Analyse Semaine S070
✅ 6 fichiers générés:
   - workout_history_S070.md
   - metrics_evolution_S070.md
   - training_learnings_S070.md
   - protocol_adaptations_S070.md
   - transition_S070_S071.md
   - bilan_final_S070.md
```

**Validation** :
- ✅ Tous fichiers dans `logs/weekly_reports/S070/` (majuscules)
- ✅ Contenu cohérent
- ✅ Pas d'erreur de chemin

### 3.6 Test Upload Workouts (5 min)

```bash
# Test upload workout vers Intervals.icu
python3 upload_workouts.py --week S071 --dry-run
```

**Attendu** :
```
🔍 Recherche workouts pour S071...
✅ 5 workout(s) trouvé(s)
   - S071-01-END-EnduranceBase-V001.zwo
   - S071-02-INT-SweetSpot-V001.zwo
   ...

🔍 Mode dry-run: simulation uniquement
✅ Tous les workouts sont valides
```

**✅ Checkpoint 6** : Tous les tests passent

---

## 🚀 Phase 4 : Mise en Production (30 min)

### 4.1 Documentation Mise à Jour (15 min)

#### README.md Principal
```bash
cd ~/cyclisme-training-logs

# Éditer README.md
nano README.md

# Ajouter section "Correctifs Récents"
```

**Contenu à ajouter** :
```markdown
## 🔧 Correctifs Récents (11 décembre 2024)

- ✅ Normalisation casse répertoires (standard : S067)
- ✅ Détection source activités améliorée
- ✅ Nettoyage scripts test obsolètes
- ✅ Documentation consolidée

Voir [DIAGNOSTIC_COMPLET.md](docs/DIAGNOSTIC_COMPLET.md) pour détails.
```

#### CHANGELOG.md
```bash
# Créer/Mettre à jour CHANGELOG.md
cat >> CHANGELOG.md << 'EOF'

## [1.1.0] - 2024-12-11

### Fixed
- Normalisation casse répertoires weekly_reports (S067 standard)
- Amélioration détection source activités (fonction `is_limited_data_source()`)
- Correction warnings faux positifs pour activités UPLOAD

### Changed
- Archivage scripts test obsolètes dans `scripts/archive_tests_*/`
- Consolidation documentation dans `docs/`

### Added
- Script `normalize_weekly_reports_casing.py`
- Fonction `is_limited_data_source()` robuste
- Fonction `format_limited_data_warning()` informative
- Documentation `DIAGNOSTIC_COMPLET.md`

EOF
```

### 4.2 Commit Final (5 min)

```bash
# Staging documentation
git add README.md CHANGELOG.md docs/

# Commit
git commit -m "docs: Mise à jour documentation post-correctifs v1.1.0"

# Push
git push origin main
```

### 4.3 Tag Version (5 min)

```bash
# Tag nouvelle version stable
git tag -a v1.1.0 -m "Version 1.1.0 - Corrections majeures

- Normalisation casse répertoires
- Détection source améliorée
- Nettoyage scripts obsolètes
- Tests de non-régression validés"

git push origin v1.1.0
```

### 4.4 Nettoyage Final (5 min)

```bash
# Supprimer backups anciens (garder le plus récent)
cd ~/cyclisme-training-logs/logs

# Lister backups
ls -d weekly_reports.backup.*

# Supprimer sauf le plus récent
# (Adapter selon vos backups)
rm -rf weekly_reports.backup.files.20251208
# rm -rf weekly_reports.backup.20251208_085104  # Garder celui-ci si le plus récent

# Commit nettoyage
cd ~/cyclisme-training-logs
git add -A
git commit -m "chore: Nettoyage backups obsolètes"
git push
```

**✅ Checkpoint 7** : Version 1.1.0 en production

---

## 📊 Validation Finale

### Checklist Production

- [x] API Intervals.icu fonctionnelle
- [x] Casse répertoires normalisée (S067)
- [x] Détection source améliorée
- [x] Tests workflow complets réussis
- [x] Documentation à jour
- [x] Version 1.1.0 taguée
- [x] Backups archivés

### Tests Utilisateur Final

Exécuter une séquence réelle complète :

```bash
# 1. Nouvelle séance Zwift
# (Faire une vraie séance ou utiliser existante)

# 2. Workflow complet
cd ~/cyclisme-training-logs
python3 scripts/workflow_coach.py

# Suivre les étapes interactives
# Valider que tout fonctionne sans erreur

# 3. Vérifier résultat
# - Analyse insérée dans workouts-history.md
# - Métriques mises à jour
# - Commit Git créé
```

**✅ Si OK** : Système opérationnel

---

## 🆘 Plan B : Rollback

Si problème majeur détecté :

### Option 1 : Rollback Git
```bash
cd ~/cyclisme-training-logs

# Revenir à l'archive
git checkout archive/pre-fix-20241211

# Créer nouvelle branche depuis là
git checkout -b fix-rollback-$(date +%Y%m%d)

# Identifier le problème
# Corriger
# Re-tester
```

### Option 2 : Rollback Backup Local
```bash
# Restaurer depuis backup tar.gz
cd ~/
tar -xzf Backups/cyclisme-backup-YYYYMMDD-HHMMSS.tar.gz

# Comparer avec version actuelle
diff -r cyclisme-training-logs cyclisme-training-logs.backup

# Copier fichiers nécessaires
```

### Option 3 : Rollback Partiel
```bash
# Restaurer uniquement prepare_analysis.py
cd ~/cyclisme-training-logs/scripts
cp prepare_analysis.py.backup.YYYYMMDD prepare_analysis.py

# Ou uniquement répertoires
# (Utiliser backup weekly_reports.backup.casing_*)
```

---

## 📞 Support Post-Production

### Monitoring (1 semaine)

- **Jour 1-3** : Surveiller chaque utilisation
- **Jour 4-7** : Usage normal, noter anomalies
- **Jour 8+** : Stabilité confirmée

### Issues à Surveiller

1. **Chemins fichiers** : Erreurs "File not found" liées à casse
2. **Détection source** : Warnings inappropriés
3. **Performance** : Ralentissements inhabituels
4. **Données** : Métriques manquantes

### Logging Problèmes

Créer issue GitHub si :
- Erreur reproduisible
- Comportement inattendu
- Régression détectée

**Template issue** :
```markdown
### Problème
[Description courte]

### Reproduction
1. Étape 1
2. Étape 2

### Attendu
[Comportement attendu]

### Observé
[Comportement réel]

### Environnement
- Version : v1.1.0
- OS : macOS/Linux
- Python : 3.x
```

---

## ✅ Conclusion

**Durée totale** : ~2h30  
**Complexité** : Moyenne  
**Risque** : Faible (backups multiples)

**Prochaines étapes** :
1. Utiliser le système 1 semaine en production
2. Noter améliorations possibles
3. Planifier v1.2.0 avec nouvelles features

**Questions** : Consulter `docs/FAQ.md` ou ouvrir issue GitHub

---

**Version Guide** : 1.0  
**Dernière mise à jour** : 11 décembre 2024  
**Auteur** : Assistant Coach
