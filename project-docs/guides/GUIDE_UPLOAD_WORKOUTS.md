# Guide Upload Workouts vers Intervals.icu

## Vue d'Ensemble

Le script `upload_workouts.py` permet d'uploader automatiquement les workouts générés par Claude.ai directement sur Intervals.icu via l'API.

## Prérequis

1. ✅ Credentials API configurés (`.env` ou `~/.intervals_config.json`)
2. ✅ Workouts générés au format standardisé avec délimiteurs `=== WORKOUT ... ===`
3. ✅ Python 3.x avec module `requests`

## Workflow Complet

### Étape 1 : Générer les Workouts

```bash
# Générer le prompt de planification
python3 scripts/weekly_planner.py S069 --start-date 2025-11-24

# Résultat : Prompt copié dans le presse-papier
```

### Étape 2 : Obtenir les Workouts de Claude

1. Coller le prompt dans Claude.ai
2. Attendre que Claude génère les 7 workouts
3. Copier **toute la réponse** de Claude (Cmd+A puis Cmd+C)

### Étape 3 : Uploader sur Intervals.icu

#### Option A : Depuis le Presse-Papier (recommandé)

```bash
# Simulation (dry-run) pour vérifier
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24 --dry-run

# Upload réel si validation OK
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24
```

#### Option B : Depuis un Fichier

```bash
# Sauvegarder la réponse Claude dans un fichier
cat > workouts/S069-workouts.txt
[Coller la réponse de Claude]
[Ctrl+D pour terminer]

# Upload depuis fichier
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24 \
    --file workouts/S069-workouts.txt
```

## Format Attendu

Le script détecte automatiquement les workouts délimités par :

```
=== WORKOUT S069-01-END-EnduranceBase-V001 ===

Endurance Base (70min, 52 TSS)

Warmup
- 12m ramp 50-65% 85rpm

Main set
- 45m 68-72% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm

=== FIN WORKOUT ===
```

## Options du Script

### Arguments Obligatoires

- `week` : Numéro de semaine (ex: S069)
- `--start-date YYYY-MM-DD` : Date du lundi de la semaine

### Arguments Optionnels

- `--file CHEMIN` : Fichier contenant les workouts (sinon lit presse-papier)
- `--dry-run` : Simulation sans upload réel (pour tester)

## Exemples d'Utilisation

### Exemple 1 : Upload Basique

```bash
# 1. Générer avec weekly_planner.py
python3 scripts/weekly_planner.py S069 --start-date 2025-11-24

# 2. Coller dans Claude.ai, obtenir les workouts

# 3. Copier réponse Claude (Cmd+A, Cmd+C)

# 4. Upload direct
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24
```

### Exemple 2 : Avec Validation

```bash
# 1. Dry-run pour vérifier le parsing
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24 \
    --dry-run

# Vérifier la sortie :
# ✅ Jour 01 (24/11) : S069-01-END-EnduranceBase-V001
# ✅ Jour 02 (25/11) : S069-02-INT-SweetSpot-V001
# etc.

# 2. Si OK, upload réel
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24
```

### Exemple 3 : Depuis Fichier Sauvegardé

```bash
# Sauvegarder workouts dans fichier
pbpaste > workouts/S069-generated.txt

# Upload depuis fichier
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24 \
    --file workouts/S069-generated.txt \
    --dry-run
```

## Sortie du Script

### Parsing

```
📄 Lecture presse-papier...
  ✅ Jour 01 (24/11) : S069-01-END-EnduranceBase-V001
  ✅ Jour 02 (25/11) : S069-02-INT-SweetSpot-V001
  ✅ Jour 03 (26/11) : S069-03-CAD-TechniqueCadence-V001
  ✅ Jour 04 (27/11) : S069-04-FOR-ForceEndurance-V001
  ✅ Jour 05 (28/11) : S069-05-REC-RecuperationActive-V001
  ✅ Jour 06 (29/11) : S069-06-END-EnduranceVolume-V001
  ⏭️  Jour 07 (30/11) : S069-07-REPOS (ignoré)

📊 Total : 7 workout(s) dans le presse-papier
```

### Upload

```
======================================================================
📤 UPLOAD WORKOUTS VERS INTERVALS.ICU
Semaine : S069
Période : 24/11/2025 → 30/11/2025
Mode : RÉEL
======================================================================

📅 Jour 01 - 2025-11-24
   S069-01-END-EnduranceBase-V001
  ✅ Uploadé : Endurance Base (70min, 52 TSS) (2025-11-24)

[...]

======================================================================
📊 RÉSUMÉ
======================================================================
✅ Succès   : 6
❌ Échecs   : 0
⏭️  Ignorés  : 1
📝 Total    : 7
======================================================================
```

## Gestion des Erreurs

### Erreur : Aucun workout détecté

**Cause** : Format de délimiteurs incorrect dans la réponse Claude

**Solution** :
```bash
# Vérifier que la réponse contient :
grep "=== WORKOUT" fichier.txt
grep "=== FIN WORKOUT" fichier.txt

# Si absent, redemander à Claude avec le prompt corrigé
```

### Erreur : API non disponible

**Cause** : Credentials API manquants ou invalides

**Solution** :
```bash
# Vérifier config
cat ~/.intervals_config.json

# Ou vérifier .env
cat .env

# Reconfigurer si nécessaire
export VITE_INTERVALS_ATHLETE_ID=iXXXXXX
export VITE_INTERVALS_API_KEY=votre_clé
```

### Erreur : Format date invalide

**Cause** : Date pas au format YYYY-MM-DD

**Solution** :
```bash
# Incorrect
--start-date 24/11/2025

# Correct
--start-date 2025-11-24
```

## Vérification Post-Upload

1. Aller sur Intervals.icu > Calendar
2. Vérifier que les workouts apparaissent aux bonnes dates
3. Cliquer sur un workout pour vérifier le contenu
4. Tester l'exécution d'un workout pour validation finale

## Workflow Complet Type

```bash
# Semaine S069 (24-30 novembre 2025)

# 1. Planification
python3 scripts/weekly_planner.py S069 --start-date 2025-11-24

# 2. Claude.ai : Coller prompt, copier réponse

# 3. Validation (dry-run)
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24 --dry-run

# 4. Upload réel
python3 scripts/upload_workouts.py S069 --start-date 2025-11-24

# 5. Vérification sur Intervals.icu
open "https://intervals.icu/calendar"

# 6. Documentation locale (optionnel)
pbpaste > logs/workouts_planning/S069-workouts-generated.txt
```

## Intégration dans le Workflow Global

```mermaid
graph LR
    A[weekly_planner.py] -->|Prompt| B[Claude.ai]
    B -->|7 Workouts| C[Presse-papier]
    C -->|upload_workouts.py| D[Intervals.icu API]
    D -->|Création| E[Calendar Intervals.icu]
```

## Notes Importantes

1. **Jours de repos** : Automatiquement ignorés (détection `REPOS` dans le nom)
2. **Dry-run recommandé** : Toujours tester avec `--dry-run` d'abord
3. **Confirmation** : Le script demande confirmation avant upload réel
4. **Idempotence** : Re-uploader la même semaine créera des doublons (attention !)
5. **Modification** : Si besoin de modifier, mieux vaut éditer sur Intervals.icu UI

## Dépannage

### Commande Complète de Test

```bash
# Test complet depuis zéro
cd ~/magma-cycling

# Génération
python3 scripts/weekly_planner.py S069 --start-date 2025-11-24

# [Coller dans Claude, copier réponse]

# Test parsing
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24 \
    --dry-run

# Upload si OK
python3 scripts/upload_workouts.py S069 \
    --start-date 2025-11-24
```

### Logs Détaillés

Le script affiche chaque étape :
- ✅ = Succès
- ❌ = Erreur
- ⏭️ = Ignoré
- 🔍 = Dry-run

## Support

En cas de problème :
1. Vérifier le format de sortie Claude (délimiteurs `===`)
2. Tester avec `--dry-run` d'abord
3. Vérifier credentials API
4. Consulter les logs du script

### ⚠️ Format Nom Important

Le nom du workout dans Intervals.icu provient **uniquement** du délimiteur :
- ✅ `=== WORKOUT S069-02-INT-SweetSpotAdaptation-V002 ===` → Nom utilisé
- ❌ `Sweet Spot Adaptation 2x10 (65min, 65 TSS)` → Description uniquement

**Avantages :**
- **Traçabilité** : Lien direct avec fichiers .zwo
- **Cohérence** : Respect convention de nommage SSSS-JJ-TYPE-NomExercice-VVVV
- **Parsing** : Extraction automatique type/jour/version depuis le nom

**Exemple :**
```
=== WORKOUT S069-02-INT-SweetSpotAdaptation-V002 ===
```
Devient dans Intervals.icu :
- Nom : `S069-02-INT-SweetSpotAdaptation-V002`
- Permet recherche par : S069, INT, SweetSpot, V002
- Lien fichier : `S069-02-INT-SweetSpotAdaptation-V002.zwo`
