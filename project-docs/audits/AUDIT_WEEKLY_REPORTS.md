# Audit Weekly Reports - 8 Décembre 2025

## Résumé Exécutif

🚨 **Problèmes critiques identifiés :**
- **1 doublon** : `S067` et `s067` (casse différente, contenu identique)
- **1 casse incorrecte** : `s070` (devrait être `S070`)
- **1 script source** : `organize_weekly_report.py` crée répertoires en minuscule

## État Initial

### Arborescence Actuelle
```
logs/weekly_reports/
├── S001/         ✅ Correct
├── S046/         ✅ Correct
├── S067/         ✅ Correct (mais doublon avec s067)
├── S068/         ✅ Correct
├── S069/         ✅ Correct
├── s067/         ❌ Minuscule (doublon de S067)
└── s070/         ❌ Minuscule (devrait être S070)
```

### Détails Répertoires Problématiques

#### S067 vs s067 (DOUBLON)

| Attribut | S067 (majuscule) | s067 (minuscule) |
|----------|------------------|------------------|
| **Date modif** | 25 nov 06:56 | 25 nov 06:29 |
| **Fichiers** | 6 fichiers | 6 fichiers |
| **Tailles** | 20K, 7.7K, 16K, 19K, 15K, 12K | 20K, 7.7K, 16K, 19K, 15K, 12K |
| **Contenu** | Identique (vérifié par diff) | Identique |

**Analyse :**
- `s067` créé en premier (06:29)
- `S067` créé 27 minutes plus tard (06:56) avec contenu identique
- **Hypothèse** : Génération initiale en minuscule, puis re-génération avec correction
- **Recommandation** : **Supprimer `s067`**, garder `S067` (plus récent et casse correcte)

#### s070 (CASSE INCORRECTE)

| Attribut | Valeur |
|----------|--------|
| **Date création** | 7 déc 21:20 |
| **Fichiers** | 6 fichiers |
| **Tailles** | 121-130 bytes (stubs/placeholders) |
| **État** | Répertoire récent, fichiers vides |

**Analyse :**
- Répertoire créé très récemment
- Fichiers très petits → probablement placeholders ou génération incomplète
- Pas de doublon en majuscule
- **Recommandation** : **Renommer `s070` → `S070`**

## Analyse Code Source

### Script Problématique Identifié

**Fichier :** `scripts/organize_weekly_report.py`
**Ligne :** 144-145

```python
# ❌ PROBLÈME
week_str = f"s{week_number:03d}"  # Crée "s067" au lieu de "S067"
week_dir = self.bilans_dir / week_str
```

**Impact :**
- Tous les répertoires créés par ce script utilisent minuscule
- Source directe des répertoires `s067` et `s070`

**Correction requise :**
```python
# ✅ CORRECTION
week_str = f"S{week_number:03d}"  # Majuscule obligatoire
week_dir = self.bilans_dir / week_str
```

### Autres Occurrences

**Lignes additionnelles dans `organize_weekly_report.py` :**
- Ligne 34-39 : Templates noms de fichiers (utilisent `s{week}` minuscule)
- Ligne 116-121 : Validation fichiers (utilisent `s{week_str}` minuscule)

**Note :** Les noms de **fichiers** peuvent rester en minuscule (convention établie), mais les noms de **répertoires** doivent être en majuscule.

## Plan de Correction

### Étape 1 : Backup (Sécurité)
```bash
cp -R logs/weekly_reports logs/weekly_reports.backup.20251208
```

### Étape 2 : Correction Doublon S067/s067
**Action :** Supprimer `s067` (obsolète, identique à `S067`)
```bash
rm -rf logs/weekly_reports/s067
```

**Justification :**
- S067 plus récent (27 min après s067)
- Contenu strictement identique
- Casse correcte

### Étape 3 : Correction Casse s070
**Action :** Renommer `s070` → `S070`
```bash
mv logs/weekly_reports/s070 logs/weekly_reports/S070
```

**Justification :**
- Pas de doublon existant
- Fichiers récents à préserver
- Simple correction de casse

### Étape 4 : Correction Code Source
**Fichier :** `scripts/organize_weekly_report.py`

**Changements :**
```python
# Ligne 144
- week_str = f"s{week_number:03d}"
+ week_str = f"S{week_number:03d}"
```

### Étape 5 : Validation
```bash
# Vérifier structure finale
ls -la logs/weekly_reports/

# Vérifier nombre fichiers préservés
find logs/weekly_reports -type f | wc -l

# Comparer avec backup
diff -r logs/weekly_reports logs/weekly_reports.backup.20251208 | grep -v "^Only in"
```

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|---------|------------|
| Perte données | Faible | Critique | Backup complet avant modifications |
| Références cassées | Moyen | Moyen | Audit scripts référençant weekly_reports |
| Git conflicts | Faible | Faible | Commit backup avant corrections |
| Régression script | Faible | Moyen | Tests post-correction |

## Validation Post-Correction

### Checklist
- [ ] Backup créé et vérifié
- [ ] s067 supprimé
- [ ] s070 renommé en S070
- [ ] Script organize_weekly_report.py corrigé
- [ ] Arborescence finale conforme (S001, S046, S067, S068, S069, S070)
- [ ] Aucun fichier perdu (count avant = count après)
- [ ] Git diff propre
- [ ] Test script organize_weekly_report.py avec nouvelle semaine

### Commandes Validation
```bash
# 1. Structure finale
ls logs/weekly_reports/
# Attendu : S001 S046 S067 S068 S069 S070

# 2. Aucune minuscule restante
ls logs/weekly_reports/ | grep '^s'
# Attendu : (aucun résultat)

# 3. Préservation données
find logs/weekly_reports -name "*.md" | wc -l
# Attendu : 42 fichiers (7 répertoires × 6 fichiers)

# 4. Test génération nouvelle semaine
python3 scripts/organize_weekly_report.py --week 071 --dry-run
# Attendu : Doit créer "S071" (majuscule)
```

## Convention Finale Documentée

### Format Répertoires
**Strict :** `SXXX`
- **S** en MAJUSCULE obligatoire
- **XXX** = 3 chiffres avec padding zéros

**Exemples valides :**
- `S001` ✅
- `S067` ✅
- `S070` ✅
- `S123` ✅

**Exemples invalides :**
- `s067` ❌ (minuscule)
- `S67` ❌ (2 chiffres seulement)
- `s70` ❌ (minuscule + 2 chiffres)
- `Week070` ❌ (préfixe incorrect)

### Format Fichiers
**Convention :** `nom_fichier_sXXX.md` (minuscule acceptée)
- Noms fichiers peuvent rester en minuscule (convention établie)
- Exemples : `bilan_final_s067.md`, `workout_history_s070.md`

## Recommandations Futures

1. **Validation Systématique**
   - Ajouter assertion dans `organize_weekly_report.py` vérifiant majuscule
   - Exemple : `assert week_str[0].isupper(), "Week ID must be uppercase"`

2. **Tests Automatisés**
   - Créer test unitaire vérifiant casse correcte
   - Intégrer dans CI/CD si disponible

3. **Documentation**
   - Ajouter convention dans README.md
   - Documenter dans docstring de organize_weekly_report.py

4. **Audit Périodique**
   - Script de vérification mensuelle structure
   - Alerte si minuscules détectées

## Statut

- **Audit** : ✅ Complet
- **Plan** : ✅ Défini
- **Script correction** : ✅ Prêt (voir fix_weekly_reports_casing.py)
- **Exécution** : ⏸️  En attente validation utilisateur

## Prochaine Étape

**Validation utilisateur requise sur :**
1. ✅ Suppression s067 (doublon identique) ?
2. ✅ Renommage s070 → S070 ?
3. ✅ Correction organize_weekly_report.py ligne 144 ?
4. ✅ Exécution automatique ou manuelle ?

---

**Généré le :** 8 décembre 2025
**Outil :** Claude Code Audit Assistant
