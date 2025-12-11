# Rapport de Corrections Documentation

**Date d'analyse :** $(date +"%Y-%m-%d %H:%M:%S")
**Post-migration :** logs/weekly_reports/

---

## 📊 Résumé

- ✅ Tests OK : 19
- ⚠️ Avertissements : 7
- ❌ Erreurs : 2

## 🔴 CORRECTIONS URGENTES

### Références obsolètes "bilans_hebdo"

Les fichiers suivants contiennent des références à l'ancien chemin `bilans_hebdo/` :

#### docs/CHANGELOG.md

**1 occurrence(s) détectée(s)**

```bash
19:- Correction références obsolètes `bilans_hebdo/` dans tous scripts
```

**Correction recommandée :**
```bash
sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' docs/CHANGELOG.md
```

#### docs/GUIDE_COMMIT_GITHUB.md

**1 occurrence(s) détectée(s)**

```bash
95:- Migration références bilans_hebdo → logs/weekly_reports
```

**Correction recommandée :**
```bash
sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' docs/GUIDE_COMMIT_GITHUB.md
```

## 🔧 Scripts à Vérifier

Liste des scripts mentionnés dans la documentation :

- ✅ `scripts/weekly_analysis.py` : Cohérent (logs/weekly_reports)
- ✅ `scripts/upload_workouts.py` : OK (pas d'accès direct chemins)
- ✅ `scripts/prepare_analysis.py` : OK (pas d'accès direct chemins)
- ✅ `scripts/insert_analysis.py` : OK (pas d'accès direct chemins)
- ✅ `scripts/workflow_coach.py` : OK (pas d'accès direct chemins)
- ✅ `scripts/organize_weekly_report.py` : Cohérent (logs/weekly_reports)
- ✅ `scripts/prepare_weekly_report.py` : Cohérent (logs/weekly_reports)

---

## 🎯 Plan d'Action Recommandé

### 1. Corrections Urgentes

#### A. Remplacer toutes les références 'bilans_hebdo' dans la documentation

```bash
sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' docs/CHANGELOG.md
sed -i '' 's|bilans_hebdo|logs/weekly_reports|g' docs/GUIDE_COMMIT_GITHUB.md
```

### 2. Vérifications Complémentaires

- [ ] Vérifier cohérence des workflows (6 phases)
- [ ] Mettre à jour dates de dernière modification
- [ ] Vérifier liens internes documentation
- [ ] Tester les commandes décrites dans les guides

### 3. Mise à Jour CHANGELOG

Ajouter une entrée :

```markdown
## [1.1.0] - YYYY-MM-DD

### Changed
- Migration complète vers logs/weekly_reports/
- Correction références obsolètes bilans_hebdo/ dans documentation
- Mise à jour scripts organize_weekly_report.py et prepare_weekly_report.py

### Fixed
- Cohérence chemins dans tous les fichiers de documentation
```

---

**Généré par :** analyze_documentation.sh
