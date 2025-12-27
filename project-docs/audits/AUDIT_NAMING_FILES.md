# Audit Complet Nommage Fichiers Weekly Reports - 8 Décembre 2025

## 🚨 Résumé Exécutif

**Problème CRITIQUE identifié :** Incohérence systématique casse noms fichiers

**Impact :**
- 12 fichiers non conformes (S067: 6 + S070: 6)
- 18 fichiers conformes (S068: 6 + S069: 6)
- **2 scripts Python** propagent le problème
- **1 prompt IA** instruit casse incorrecte

**Source racine :**
1. ❌ `prepare_weekly_report.py` : Prompt IA avec exemples minuscules
2. ❌ `organize_weekly_report.py` : Validation fichiers attend minuscules

---

## 📊 État Actuel Fichiers

### S067/ - ❌ TOUS en minuscule
```
bilan_final_s067.md              ❌ → bilan_final_S067.md
metrics_evolution_s067.md        ❌ → metrics_evolution_S067.md
protocol_adaptations_s067.md     ❌ → protocol_adaptations_S067.md
training_learnings_s067.md       ❌ → training_learnings_S067.md
transition_s067_s068.md          ❌ → transition_S067_S068.md
workout_history_s067.md          ❌ → workout_history_S067.md
```

### S068/ - ✅ TOUS en MAJUSCULE
```
bilan_final_S068.md              ✅ Conforme
metrics_evolution_S068.md        ✅ Conforme
protocol_adaptations_S068.md     ✅ Conforme
training_learnings_S068.md       ✅ Conforme
transition_S068_S069.md          ✅ Conforme
workout_history_S068.md          ✅ Conforme
```

### S069/ - ✅ TOUS en MAJUSCULE
```
bilan_final_S069.md              ✅ Conforme
metrics_evolution_S069.md        ✅ Conforme
protocol_adaptations_S069.md     ✅ Conforme
training_learnings_S069.md       ✅ Conforme
transition_S069_S070.md          ✅ Conforme
workout_history_S069.md          ✅ Conforme
```

### S070/ - ❌ TOUS en minuscule
```
bilan_final_s070.md              ❌ → bilan_final_S070.md
metrics_evolution_s070.md        ❌ → metrics_evolution_S070.md
protocol_adaptations_s070.md     ❌ → protocol_adaptations_S070.md
training_learnings_s070.md       ❌ → training_learnings_S070.md
transition_s070_s071.md          ❌ → transition_S070_S071.md
workout_history_s070.md          ❌ → workout_history_S070.md
```

### Statistiques

| Métrique | Valeur |
|----------|--------|
| **Répertoires audités** | 4 (S067, S068, S069, S070) |
| **Total fichiers** | 24 fichiers .md |
| **Conformes MAJUSCULE** | 12 fichiers (50%) |
| **Non conformes minuscule** | 12 fichiers (50%) |
| **Répertoires problématiques** | 2 (S067, S070) |

---

## 🔍 Analyse Source du Problème

### 1. Script : `prepare_weekly_report.py`

**Rôle :** Génère le prompt IA pour création rapports hebdomadaires

**Problème CRITIQUE - Lignes 154-205 :**

```python
# ❌ PROMPT IA AVEC MINUSCULES

### 1. workout_history_s{week_number:03d}.md       # Ligne 154 ❌
### 2. metrics_evolution_s{week_number:03d}.md     # Ligne 166 ❌
### 3. training_learnings_s{week_number:03d}.md    # Ligne 175 ❌
### 4. protocol_adaptations_s{week_number:03d}.md  # Ligne 185 ❌
### 5. transition_s{week_number:03d}_s{week_number+1:03d}.md  # Ligne 195 ❌
### 6. bilan_final_s{week_number:03d}.md           # Ligne 205 ❌
```

**Impact :**
- L'IA reçoit instructions explicites d'utiliser minuscules
- Tous les rapports générés avec ce prompt héritent minuscules
- S067 et S070 probablement générés avec ce prompt

**Correction requise :**
```python
# ✅ PROMPT CORRIGÉ

### 1. workout_history_S{week_number:03d}.md       # MAJUSCULE
### 2. metrics_evolution_S{week_number:03d}.md     # MAJUSCULE
### 3. training_learnings_S{week_number:03d}.md    # MAJUSCULE
### 4. protocol_adaptations_S{week_number:03d}.md  # MAJUSCULE
### 5. transition_S{week_number:03d}_S{week_number+1:03d}.md  # MAJUSCULE
### 6. bilan_final_S{week_number:03d}.md           # MAJUSCULE
```

### 2. Script : `organize_weekly_report.py`

**Rôle :** Valide et organise fichiers rapports hebdomadaires

**Problème - Lignes 116-121 (méthode `validate_files`) :**

```python
# ❌ VALIDATION ATTEND MINUSCULES

expected = [
    f"workout_history_s{week_str}.md",         # ❌ minuscule
    f"metrics_evolution_s{week_str}.md",       # ❌ minuscule
    f"training_learnings_s{week_str}.md",      # ❌ minuscule
    f"protocol_adaptations_s{week_str}.md",    # ❌ minuscule
    f"transition_s{week_str}_s{next_week_str}.md",  # ❌ minuscule
    f"bilan_final_s{week_str}.md"              # ❌ minuscule
]
```

**Impact :**
- Valide fichiers minuscules comme corrects
- Ne détecte pas l'incohérence
- Perpétue le problème

**Note :** Ligne 144 déjà corrigée pour répertoires (S majuscule) mais pas les noms fichiers

**Correction requise :**
```python
# ✅ VALIDATION CORRIGÉE

expected = [
    f"workout_history_S{week_str}.md",         # ✅ MAJUSCULE
    f"metrics_evolution_S{week_str}.md",       # ✅ MAJUSCULE
    f"training_learnings_S{week_str}.md",      # ✅ MAJUSCULE
    f"protocol_adaptations_S{week_str}.md",    # ✅ MAJUSCULE
    f"transition_S{week_str}_S{next_week_str}.md",  # ✅ MAJUSCULE
    f"bilan_final_S{week_str}.md"              # ✅ MAJUSCULE
]
```

---

## 💡 Explication Alternance S067/S068/S069/S070

**Hypothèse validée :**

1. **S067** : Généré avec `prepare_weekly_report.py` (prompt minuscule) → minuscules
2. **S068** : Généré **manuellement** ou script corrigé temporairement → MAJUSCULES ✅
3. **S069** : Même processus que S068 → MAJUSCULES ✅
4. **S070** : Retour `prepare_weekly_report.py` non corrigé → minuscules

**Conclusion :** S068 et S069 = accident heureux (correction manuelle ?)

---

## 📝 Plan de Correction Complet

### Étape 1 : Backup (Sécurité)

✅ **Déjà effectué :** `logs/weekly_reports.backup.20251208_085104/`

Créer backup additionnel avant corrections fichiers :
```bash
cp -R logs/weekly_reports logs/weekly_reports.backup.files.20251208
```

### Étape 2 : Correction Scripts Python

#### 2a. Corriger `prepare_weekly_report.py`

**Fichier :** `scripts/prepare_weekly_report.py`
**Lignes :** 154, 166, 175, 185, 195, 205

**Changements (6 occurrences) :**
```python
# Ligne 154
- ### 1. workout_history_s{week_number:03d}.md
+ ### 1. workout_history_S{week_number:03d}.md

# Ligne 166
- ### 2. metrics_evolution_s{week_number:03d}.md
+ ### 2. metrics_evolution_S{week_number:03d}.md

# Ligne 175
- ### 3. training_learnings_s{week_number:03d}.md
+ ### 3. training_learnings_S{week_number:03d}.md

# Ligne 185
- ### 4. protocol_adaptations_s{week_number:03d}.md
+ ### 4. protocol_adaptations_S{week_number:03d}.md

# Ligne 195
- ### 5. transition_s{week_number:03d}_s{week_number+1:03d}.md
+ ### 5. transition_S{week_number:03d}_S{week_number+1:03d}.md

# Ligne 205
- ### 6. bilan_final_s{week_number:03d}.md
+ ### 6. bilan_final_S{week_number:03d}.md
```

#### 2b. Corriger `organize_weekly_report.py`

**Fichier :** `scripts/organize_weekly_report.py`
**Lignes :** 116-121

**Changements (6 lignes) :**
```python
expected = [
-   f"workout_history_s{week_str}.md",
+   f"workout_history_S{week_str}.md",
-   f"metrics_evolution_s{week_str}.md",
+   f"metrics_evolution_S{week_str}.md",
-   f"training_learnings_s{week_str}.md",
+   f"training_learnings_S{week_str}.md",
-   f"protocol_adaptations_s{week_str}.md",
+   f"protocol_adaptations_S{week_str}.md",
-   f"transition_s{week_str}_s{next_week_str}.md",
+   f"transition_S{week_str}_S{next_week_str}.md",
-   f"bilan_final_s{week_str}.md"
+   f"bilan_final_S{week_str}.md"
]
```

### Étape 3 : Correction Fichiers Existants

**Script automatique :** `scripts/fix_weekly_reports_files.py`

**Opérations :**
1. Renommer 6 fichiers S067/ (s067 → S067)
2. Renommer 6 fichiers S070/ (s070 → S070)

**Détail renommages S067/ :**
```
bilan_final_s067.md          → bilan_final_S067.md
metrics_evolution_s067.md    → metrics_evolution_S067.md
protocol_adaptations_s067.md → protocol_adaptations_S067.md
training_learnings_s067.md   → training_learnings_S067.md
transition_s067_s068.md      → transition_S067_S068.md
workout_history_s067.md      → workout_history_S067.md
```

**Détail renommages S070/ :**
```
bilan_final_s070.md          → bilan_final_S070.md
metrics_evolution_s070.md    → metrics_evolution_S070.md
protocol_adaptations_s070.md → protocol_adaptations_S070.md
training_learnings_s070.md   → training_learnings_S070.md
transition_s070_s071.md      → transition_S070_S071.md
workout_history_s070.md      → workout_history_S070.md
```

### Étape 4 : Ajout Validation Stricte

**Nouveau fichier :** `scripts/validate_naming_convention.py`

Validation automatique détectant :
- Répertoires minuscules
- Fichiers minuscules
- Format invalide (non SXXX)

### Étape 5 : Tests Validation

```bash
# Test 1 : Aucun fichier minuscule
find logs/weekly_reports -name "*_s0*.md"
# Attendu : aucun résultat

# Test 2 : Tous fichiers MAJUSCULES
find logs/weekly_reports -name "*_S0*.md" | wc -l
# Attendu : 24 fichiers

# Test 3 : Structure 6 fichiers par semaine
for dir in logs/weekly_reports/S*/; do
    count=$(ls -1 "$dir"/*.md 2>/dev/null | wc -l)
    echo "$dir : $count fichiers"
done
# Attendu : 6 pour S067, S068, S069, S070

# Test 4 : Patterns transition
find logs/weekly_reports -name "transition_S*_S*.md"
# Attendu : 3 fichiers (S067→S068, S068→S069, S069→S070, S070→S071)
```

---

## 🎯 Convention Finale STRICTE

### Répertoires
```
SXXX/
```
Exemples : `S067/`, `S068/`, `S070/`

### Fichiers (6 obligatoires par semaine)
```
bilan_final_SXXX.md
metrics_evolution_SXXX.md
protocol_adaptations_SXXX.md
training_learnings_SXXX.md
transition_SXXX_SYYY.md
workout_history_SXXX.md
```

### Règles
1. **S en MAJUSCULE** partout (répertoires ET fichiers)
2. **3 chiffres** avec padding zéros (001, 067, 070)
3. **Pas d'exception** : format strict obligatoire

### Exemples Valides ✅
```
S067/bilan_final_S067.md
S070/transition_S070_S071.md
S123/workout_history_S123.md
```

### Exemples Invalides ❌
```
s067/bilan_final_s067.md        (minuscules)
S67/bilan_final_S67.md          (2 chiffres seulement)
S070/bilan_final_s070.md        (fichier minuscule)
Week070/bilan_Week070.md        (préfixe invalide)
```

---

## ✅ Checklist Pré-Exécution

- [ ] Backup additionnel créé
- [ ] Scripts Python corrigés (prepare + organize)
- [ ] Script renommage fichiers prêt
- [ ] Tests validation définis
- [ ] Convention documentée

---

## 📊 Récapitulatif Corrections

| Élément | Corrections | Impact |
|---------|-------------|--------|
| **Scripts Python** | 2 fichiers (12 lignes) | Futur conforme |
| **Fichiers existants** | 12 renommages | Passé conforme |
| **Validation ajoutée** | 1 nouveau script | Prévention |
| **Tests** | 4 tests automatisés | Vérification |

---

## 🚀 Prochaine Étape

**Validation utilisateur requise :**

1. ✅ Corriger `prepare_weekly_report.py` (6 lignes) ?
2. ✅ Corriger `organize_weekly_report.py` (6 lignes) ?
3. ✅ Renommer 12 fichiers (S067 + S070) ?
4. ✅ Créer script validation automatique ?

**Confirme pour exécution immédiate.**

---

**Généré le :** 8 décembre 2025
**Outil :** Claude Code - Audit Exhaustif Nommage
**Status :** ⏸️  En attente validation utilisateur
