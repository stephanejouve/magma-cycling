# Convention de Nommage des Sprints

**Version :** 1.0
**Date :** 4 janvier 2026

---

## Structure

**Format :** `Sprint [Type][Numéro] - [Nom Descriptif]`

### Types de Sprints

- **S** (Story) - Sprints fonctionnels (features utilisateur)
  - Exemple : S070, S071, S072
  - Numérotation par semaine calendaire

- **R** (Refactor/Release) - Sprints techniques (qualité, architecture)
  - Exemple : R1, R2, R3, R4, R5
  - Numérotation séquentielle simple

---

## Numérotation

### Sprints Techniques (R)
- **Séquence simple :** R1, R2, R3, R4, R5, etc.
- **Incrémentation :** +1 par sprint technique
- **Rationale :** Clarté et traçabilité linéaire

### Sprints Fonctionnels (S)
- **Format :** SXXX où XXX = numéro de semaine
- **Exemple :** S070 = semaine 70 de l'année
- **Rationale :** Alignement calendrier entraînement

---

## Historique Projet

### Sprints Techniques (Type R)

| Sprint | Date | Description | Version | Commits |
|--------|------|-------------|---------|---------|
| R1 | 2025-XX-XX | Initial setup | v1.0.0 | - |
| R2 | 2025-XX-XX | Core refactoring | v2.0.0 | - |
| R3 | 2025-XX-XX | API cleanup | v2.1.0 | - |
| **R4** | **2026-01-03/04** | **Qualité (PEP 8/257, MyPy)** | **v2.2.0** | **33** |
| **R5** | **2026-01-04** | **Organization & Automation** | **v2.2.0** | **5** |

### Détails Sprint R4 (Qualité)
**Période :** 3-4 janvier 2026 (matin)
**Objectifs :**
- PEP 8 compliance : 1137 → 0 violations
- PEP 257 docstrings : 179 → 0 errors
- MyPy type safety : 38 → 0 errors
- Pre-commit hooks : 13 → 14 actifs
- Complexité : F-48 → B-7

**Résultats :**
- ✅ 100% conformité standards Python
- ✅ 497 tests passing
- ✅ CI/CD fonctionnel
- ✅ Documentation Sphinx (36 pages)

### Détails Sprint R5 (Organization)
**Période :** 4 janvier 2026 (après-midi)
**Objectifs :**
- Cleanup structure projet
- Bot maintenance automatisé
- Package revue de code
- Documentation organisation

**Résultats :**
- ✅ 14 fichiers réorganisés
- ✅ Bot `project_cleaner.py` opérationnel
- ✅ Script `generate_code_review_package.sh`
- ✅ Structure docs/ standardisée

---

## Version Projet

**Version actuelle :** v2.2.0

### Correspondance Sprint → Version

- Sprint R4 : v2.1.x → **v2.2.0** (bump majeur)
- Sprint R5 : **v2.2.0** (maintenue)

**Rationale :**
- R4 = changements qualité majeurs → bump version
- R5 = organisation/tooling → pas de bump (même version)

---

## Convention Anti-Confusion

### ❌ À Éviter

- **"R21"** : Peut être confondu avec "Release 2.1"
- **"R2.1"** : Idem, confusion version vs sprint
- **Numérotation incohérente** : R4 → R21 → R6

### ✅ À Utiliser

- **Séquence simple :** R1, R2, R3, R4, R5, R6...
- **Noms descriptifs :** "Sprint R5 - Organization"
- **Clarté immédiate :** Pas d'ambiguïté

---

## Références

- **PEP 440 :** Version Identification (versioning Python)
- **Semantic Versioning :** https://semver.org/
- **Git Tags :** Convention `v2.2.0` (avec 'v' prefix)

---

**Maintenu par :** MOA
**Dernière mise à jour :** 4 janvier 2026
