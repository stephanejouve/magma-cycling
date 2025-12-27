# 📝 TEMPLATE DOCSTRING v2 AVEC TAGS GARTNER TIME

**Version :** 2.0  
**Date :** 26 décembre 2025  
**Usage :** Tous fichiers Python du projet

---

## 🎯 TEMPLATE STANDARD (Fichiers Production)

```python
"""
[Description concise en une ligne]

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Description détaillée en français. Expliquer le rôle du module,
ses responsabilités principales, et son intégration dans le workflow.
Maximum 2-3 phrases claires et concises.

Examples:
    Command-line usage::

        poetry run command --option value
        poetry run command --flag

    Programmatic usage::

        from cyclisme_training_logs.module import Class
        
        # Initialisation
        obj = Class(param="value")
        
        # Utilisation
        result = obj.method()
        print(result)

    Advanced usage::

        # Configuration personnalisée
        obj = Class(
            param1="value1",
            param2="value2",
            debug=True
        )
        
        # Méthodes chaînées
        result = obj.method1().method2().finalize()

Author: Claude Code
Created: YYYY-MM-DD
Updated: 2025-12-26 (Standardization Prompt 3)
"""
```

---

## 🆕 TEMPLATE NOUVEAUX FICHIERS (Création)

```python
"""
[Description concise en une ligne]

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P0
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/module.py
DOCSTRING: v2

Description détaillée en français. Expliquer le rôle du nouveau module,
pourquoi il a été créé, et comment il s'intègre dans l'architecture v2.
Mentionner la source de migration si applicable.

Examples:
    Basic usage::

        from cyclisme_training_logs.core.module import NewClass
        
        # Initialisation
        obj = NewClass()
        
        # Utilisation
        result = obj.process()

    Integration example::

        from cyclisme_training_logs.workflow_coach import WorkflowCoach
        from cyclisme_training_logs.core.module import NewClass
        
        # Intégration dans workflow existant
        workflow = WorkflowCoach()
        processor = NewClass(workflow_config=workflow.config)
        
        result = processor.execute()

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""
```

---

## 🔵 TEMPLATE FICHIERS EN MIGRATION

```python
"""
[Description concise en une ligne]

GARTNER_TIME: M
STATUS: Migration (v1 → v2)
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_TARGET: core/new_module.py
DEPRECATION_PLAN: Replace with NewModule after Prompt 2 Phase 1
DOCSTRING: v2

Description détaillée en français. Expliquer l'état actuel de migration,
ce qui a changé, et le plan de transition vers le module cible.
Indiquer quand le fichier actuel sera déprécié.

Examples:
    Current usage (v1)::

        from cyclisme_training_logs.old_module import OldClass
        
        # Méthode actuelle (sera dépréciée)
        obj = OldClass()
        result = obj.old_method()

    Future usage (v2) - After migration::

        from cyclisme_training_logs.core.new_module import NewClass
        
        # Nouvelle méthode (post-migration)
        obj = NewClass()
        result = obj.new_method()

    Migration helper::

        # Compatibilité temporaire
        from cyclisme_training_logs.old_module import migrate_to_new
        
        old_obj = OldClass()
        new_obj = migrate_to_new(old_obj)

Author: Claude Code
Created: YYYY-MM-DD
Updated: 2025-12-26 (Migration Prompt 2 - In Progress)
"""
```

---

## 🟡 TEMPLATE FICHIERS LEGACY (Tolerate)

```python
"""
[Description concise en une ligne]

GARTNER_TIME: T
STATUS: Production (Legacy)
LAST_REVIEW: 2025-12-26
PRIORITY: P3
REPLACEMENT: new_module.py (Planned)
DOCSTRING: v2

Description détaillée en français. Expliquer pourquoi ce module est
en mode "Tolerate", quel module le remplacera à terme, et dans combien
de temps. Indiquer si utilisé activement ou peu fréquent.

Examples:
    Current usage (still supported)::

        from cyclisme_training_logs.legacy_module import LegacyClass
        
        # Méthode actuelle (fonctionnelle mais à éviter)
        obj = LegacyClass()
        result = obj.legacy_method()

    Recommended alternative::

        # Utiliser plutôt le nouveau module
        from cyclisme_training_logs.new_module import NewClass
        
        obj = NewClass()
        result = obj.modern_method()

Warning:
    Ce module est en mode Tolerate. Il est fonctionnel mais non recommandé
    pour nouveau code. Utiliser new_module.py pour nouvelles implémentations.

Author: Claude Code
Created: YYYY-MM-DD
Updated: 2025-12-26 (Marked as Legacy)
"""
```

---

## 🔴 TEMPLATE FICHIERS À ÉLIMINER

```python
"""
[Description concise en une ligne]

GARTNER_TIME: E
STATUS: Deprecated
LAST_REVIEW: 2025-12-26
PRIORITY: P4
DEPRECATION_DATE: 2025-12-26
REMOVAL_DATE: 2026-01-26 (30 days)
REPLACEMENT: new_module.py
DOCSTRING: v2

Description détaillée en français. Expliquer pourquoi ce module est déprécié,
quel module le remplace, et la date de suppression prévue.

Examples:
    Old usage (DEPRECATED - DO NOT USE)::

        from cyclisme_training_logs.deprecated_module import DeprecatedClass
        
        # ❌ NE PLUS UTILISER
        obj = DeprecatedClass()
        result = obj.deprecated_method()

    Migration path::

        # ✅ Utiliser à la place
        from cyclisme_training_logs.new_module import NewClass
        
        obj = NewClass()
        result = obj.new_method()

Deprecated:
    Version: 2.0
    Removal: 2026-01-26
    Replacement: cyclisme_training_logs.new_module.NewClass

Warning:
    Ce module sera supprimé dans 30 jours. Migrer vers new_module.py.

Author: Claude Code
Created: YYYY-MM-DD
Deprecated: 2025-12-26
"""
```

---

## 📊 CHAMPS TAGS - DÉTAILS

### **GARTNER_TIME** (Obligatoire)
```
Valeurs possibles:
  I - Invest      (Stratégique, investissement actif)
  T - Tolerate    (Fonctionnel mais legacy)
  M - Migrate     (En cours de migration)
  E - Eliminate   (À supprimer)
```

### **STATUS** (Obligatoire)
```
Valeurs possibles:
  Production                     # En prod, stable
  Development                    # En développement
  Migration (v1 → v2)           # Migration en cours
  Deprecated                     # Déprécié
  Production (Legacy)           # Prod mais legacy
  Production (Experimental)     # Prod mais expérimental
```

### **LAST_REVIEW** (Obligatoire)
```
Format: YYYY-MM-DD
Cadence:
  I - Monthly
  T - Quarterly
  M - Weekly
  E - One-time
```

### **PRIORITY** (Obligatoire)
```
Valeurs possibles:
  P0 - Critical   (Impact immédiat si échec)
  P1 - High       (Important court terme)
  P2 - Medium     (Important moyen terme)
  P3 - Low        (Nice to have)
  P4 - Cleanup    (Opportuniste)
```

### **MIGRATION_SOURCE** (Optionnel - Pour nouveaux fichiers)
```
Format: cyclisme-training-automation-v2/src/path/file.py
Usage: Tracer l'origine v2 du fichier migré
```

### **MIGRATION_TARGET** (Optionnel - Pour fichiers M)
```
Format: core/new_module.py
Usage: Indiquer le fichier de destination
```

### **REPLACEMENT** (Optionnel - Pour fichiers T/E)
```
Format: new_module.py
Usage: Indiquer le module de remplacement
```

### **DEPRECATION_DATE** (Obligatoire - Pour fichiers E)
```
Format: YYYY-MM-DD
Usage: Date de dépréciation officielle
```

### **REMOVAL_DATE** (Obligatoire - Pour fichiers E)
```
Format: YYYY-MM-DD
Usage: Date de suppression planifiée (généralement +30 jours)
```

### **DEPRECATION_PLAN** (Optionnel - Pour fichiers M/T)
```
Format: Texte libre court
Usage: Expliquer le plan de transition
```

### **DOCSTRING** (Obligatoire)
```
Valeurs possibles:
  v1               # Docstring ancienne (à standardiser)
  v1 minimal       # Docstring minimale (à compléter)
  v2               # Docstring standardisée
  None             # Pas de docstring (à créer)
```

---

## 🎯 EXAMPLES SECTION - RÈGLES

### **Minimum 2 Examples**
```python
Examples:
    Basic usage::
        [Code minimal fonctionnel]
    
    Advanced usage::
        [Code avec options/configuration]
```

### **Code DOIT être exécutable**
```python
# ✅ BON - Code complet et fonctionnel
Examples:
    Basic usage::

        from cyclisme_training_logs.module import Class
        
        obj = Class(param="value")
        result = obj.method()
        print(result)  # Output: ...

# ❌ MAUVAIS - Code incomplet
Examples:
    Usage::

        obj = Class()
        result = method()
```

### **Inclure Imports**
```python
# ✅ BON - Imports explicites
Examples:
    Integration::

        from cyclisme_training_logs.workflow_coach import WorkflowCoach
        from cyclisme_training_logs.module import Helper
        
        workflow = WorkflowCoach()
        helper = Helper(workflow.config)
        
        result = helper.process()

# ❌ MAUVAIS - Imports manquants
Examples:
    Integration::

        workflow = WorkflowCoach()  # D'où vient cette classe ?
        result = process()
```

### **Commentaires Explicatifs**
```python
# ✅ BON - Commentaires utiles
Examples:
    Advanced usage::

        # Configuration pour environnement de test
        obj = Class(
            debug=True,
            log_level="DEBUG"
        )
        
        # Exécution avec validation
        result = obj.method(validate=True)
        
        # Vérification résultat
        assert result.success, "Processing failed"

# ⚠️ OK - Pas de commentaires si code évident
Examples:
    Basic usage::

        obj = Class()
        result = obj.method()
```

---

## 📋 CHECKLIST DOCSTRING COMPLÈTE

### **Header Section**
- [ ] Description une ligne claire et concise
- [ ] GARTNER_TIME tag présent et correct
- [ ] STATUS reflète l'état actuel
- [ ] LAST_REVIEW à jour (aujourd'hui si nouveau)
- [ ] PRIORITY appropriée au fichier
- [ ] Tags optionnels si pertinents (MIGRATION_SOURCE, etc.)
- [ ] DOCSTRING version indiquée

### **Description Section**
- [ ] 2-3 phrases en français
- [ ] Rôle du module expliqué
- [ ] Intégration dans workflow mentionnée
- [ ] Langage clair et professionnel

### **Examples Section**
- [ ] Minimum 2 examples
- [ ] Code exécutable et complet
- [ ] Imports explicites
- [ ] Commentaires si utiles
- [ ] Cas d'usage réalistes
- [ ] Output attendu mentionné si pertinent

### **Metadata Section**
- [ ] Author: Claude Code
- [ ] Created: Date originale
- [ ] Updated: Date modification (si applicable)
- [ ] Note migration/standardization si pertinent

---

## 🔧 VALIDATION AUTOMATIQUE

### **Script de Vérification**

```python
# scripts/validate_docstrings.py

import ast
import re
from pathlib import Path

def validate_docstring(file_path: Path) -> dict:
    """
    Valider qu'un fichier Python a une docstring complète v2.
    
    Returns:
        {
            'valid': bool,
            'errors': list[str],
            'warnings': list[str]
        }
    """
    with open(file_path) as f:
        content = f.read()
    
    tree = ast.parse(content)
    docstring = ast.get_docstring(tree)
    
    errors = []
    warnings = []
    
    if not docstring:
        errors.append("Missing module docstring")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Check required tags
    required_tags = ['GARTNER_TIME', 'STATUS', 'LAST_REVIEW', 'PRIORITY', 'DOCSTRING']
    for tag in required_tags:
        if f'{tag}:' not in docstring:
            errors.append(f"Missing required tag: {tag}")
    
    # Check GARTNER_TIME value
    if 'GARTNER_TIME:' in docstring:
        match = re.search(r'GARTNER_TIME:\s*([ITME])', docstring)
        if not match:
            errors.append("Invalid GARTNER_TIME value (must be I, T, M, or E)")
    
    # Check Examples section
    if 'Examples:' not in docstring:
        warnings.append("Missing Examples section")
    elif docstring.count('::') < 2:
        warnings.append("Examples section should have at least 2 code blocks")
    
    # Check Author/Created
    if 'Author:' not in docstring:
        warnings.append("Missing Author metadata")
    if 'Created:' not in docstring:
        warnings.append("Missing Created metadata")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

def validate_all_files():
    """Valider tous les fichiers Python du projet."""
    project_root = Path(__file__).parent.parent / 'cyclisme_training_logs'
    
    results = {}
    for py_file in project_root.rglob('*.py'):
        if '__pycache__' not in str(py_file):
            results[py_file] = validate_docstring(py_file)
    
    return results

if __name__ == '__main__':
    results = validate_all_files()
    
    print("📊 DOCSTRING VALIDATION REPORT\n")
    
    valid_count = sum(1 for r in results.values() if r['valid'])
    total_count = len(results)
    
    print(f"Valid: {valid_count}/{total_count} ({valid_count/total_count*100:.1f}%)\n")
    
    # Print errors
    files_with_errors = {f: r for f, r in results.items() if r['errors']}
    if files_with_errors:
        print("❌ FILES WITH ERRORS:\n")
        for file_path, result in files_with_errors.items():
            print(f"  {file_path.name}:")
            for error in result['errors']:
                print(f"    - {error}")
            print()
    
    # Print warnings
    files_with_warnings = {f: r for f, r in results.items() if r['warnings']}
    if files_with_warnings:
        print("⚠️  FILES WITH WARNINGS:\n")
        for file_path, result in files_with_warnings.items():
            print(f"  {file_path.name}:")
            for warning in result['warnings']:
                print(f"    - {warning}")
            print()
```

---

## 📈 INTÉGRATION DANS PROMPTS

### **Prompt 2 (Nouveaux Fichiers)**

Template automatique pour tous nouveaux fichiers créés :

```python
"""
{description_une_ligne}

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: {today}
PRIORITY: {priority}
MIGRATION_SOURCE: {source_v2_file}
DOCSTRING: v2

{description_detaillee}

Examples:
    {examples_automatiques}

Author: Claude Code
Created: {today} (Migrated from v2)
"""
```

### **Prompt 3 (Standardisation)**

Template de remplacement pour fichiers existants :

```python
"""
{description_une_ligne}

GARTNER_TIME: {tag_actuel_ou_nouveau}
STATUS: Production
LAST_REVIEW: {today}
PRIORITY: {priority_evaluee}
DOCSTRING: v2

{description_detaillee_amelioree}

Examples:
    {examples_realistes_ajoutes}

Author: Claude Code
Created: {date_originale}
Updated: {today} (Standardization Prompt 3)
"""
```

---

## ✅ CONCLUSION

**Template docstring v2 créé** avec intégration complète tags Gartner TIME ✅

**Avantages :**
- Classification claire de chaque fichier
- Traçabilité état projet
- Roadmap migrations visible
- Maintenance proactive
- Validation automatisable

**Utilisation :**
1. Tous nouveaux fichiers (Prompt 2) → Template automatique
2. Standardisation fichiers existants (Prompt 3) → Template remplacement
3. Validation post-modification → Script check automatique
4. Review périodique → Update LAST_REVIEW

---

**Version :** 2.0  
**Date :** 2025-12-26  
**Status :** Production Ready ✅
