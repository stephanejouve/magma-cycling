# SHA256 Checksums - Patches Détection Séances Sautées

## Fichiers de patch

### patches/add_skipped_sessions_detection.patch
**SHA256:** `6b1111a4536140bf982c9a55544014d307f31a9f8ea601f793c37e99a4f6214d`
**Taille:** 4.7 KB
**Modifie:** `scripts/workflow_coach.py`
**Testé avec:** `git apply --check` ✅

### patches/add_skipped_status_support.patch
**SHA256:** `c2d960df3ac4739d7064ee9ff4974357d94fdc846d14fd58bd09d27fd5f954e1`
**Taille:** 7.0 KB
**Modifie:** `scripts/rest_and_cancellations.py`
**Testé avec:** `git apply --check` ✅

## Vérification

Pour vérifier l'intégrité des patches après téléchargement :

```bash
cd cyclisme-training-logs

# Vérifier checksums
sha256sum patches/add_skipped_sessions_detection.patch
sha256sum patches/add_skipped_status_support.patch

# Devrait afficher :
# 6b1111a4536140bf982c9a55544014d307f31a9f8ea601f793c37e99a4f6214d  patches/add_skipped_sessions_detection.patch
# c2d960df3ac4739d7064ee9ff4974357d94fdc846d14fd58bd09d27fd5f954e1  patches/add_skipped_status_support.patch
```

## Application

Les patches doivent être appliqués **depuis la racine du projet** :

```bash
cd ~/cyclisme-training-logs  # PAS depuis ~/cyclisme-training-logs/patches

# Appliquer les patches
git apply patches/add_skipped_sessions_detection.patch
git apply patches/add_skipped_status_support.patch
```

## Validation post-application

```bash
# Vérifier les modifications
git status

# Devrait afficher :
# modified:   scripts/workflow_coach.py
# modified:   scripts/rest_and_cancellations.py
```

## En cas de problème

Si les checksums ne correspondent pas :
1. Retélécharger l'archive `skipped-sessions-detection.tar.gz`
2. Extraire à nouveau
3. Revérifier les checksums

Si `git apply` échoue :
1. Vérifier que vous êtes dans `~/cyclisme-training-logs` (pas dans `patches/`)
2. Vérifier l'état du dépôt : `git status`
3. Si fichiers déjà modifiés : `git checkout scripts/workflow_coach.py scripts/rest_and_cancellations.py`
4. Réessayer l'application

## Contenu des patches

### add_skipped_sessions_detection.patch

**Modifications** :
- Ajoute `from planned_sessions_checker import PlannedSessionsChecker` (ligne 36)
- Ajoute attribut `self.skipped_sessions = None` (ligne 57)
- Ajoute détection séances sautées dans `step_1b_detect_all_gaps()` (après ligne 199)
- Modifie calcul total_gaps pour inclure count_skipped
- Ajoute affichage séances sautées dans rapport
- Modifie menu options pour inclure sautées

**Lignes modifiées:** ~110 lignes

### add_skipped_status_support.patch

**Modifications** :
- Ajoute 'skipped' à VALID_STATUSES
- Ajoute fonction `generate_skipped_session_entry()` (~90 lignes)
- Ajoute 'skipped' dans result de `reconcile_planned_vs_actual()`
- Ajoute traitement statut 'skipped' dans boucle reconciliation
- Modifie traitement completed sans activité → skipped au lieu de cancelled
- Ajoute 'skipped' dans logs de rapport
- Ajoute traitement 'skipped' dans `process_week_with_rest_handling()`

**Lignes modifiées:** ~181 lignes

## Génération

Patches générés le : 2025-12-13
Méthode : `git diff` sur repo test validé
Validation : `git apply --check` réussie ✅
