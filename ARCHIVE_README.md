# Archive Référence v1 - cyclisme-training-logs

## Vue d'Ensemble

Système automatisation analyses entraînement cyclisme (version production actuelle).  
Cette archive sert de **référence UNIQUEMENT** pour développement v2.

**Statut :** Production stable, workflow quotidien opérationnel (3-6 min)  
**Objectif v2 :** Architecture modulaire, workflow hebdomadaire automatisé (10-15 min)  
**Date archive :** 2025-01-15

---

## 📊 Qualité Code v1

### ⚠️ Limitations Connues

**Documentation :**
- ❌ Pas de docstrings modules/fonctions
- ❌ Comments minimaux
- ❌ Pas de guide API modules

**Architecture :**
- ❌ Duplication code (client API, parsing, validation)
- ❌ Scripts monolithiques indépendants
- ❌ Pas de factorisation logique commune

**Tests :**
- ❌ Aucun test unitaire
- ❌ Validation manuelle uniquement
- ❌ Pas de CI/CD

**Logging :**
- ⚠️ Print statements basiques
- ❌ Pas de rotation logs
- ❌ Niveaux logging inconsistants

### ✅ Points Forts (À Conserver)

**Architecture workflow :**
- ✅ Orchestration séquentielle robuste (`workflow_coach.py`)
- ✅ Gestion erreurs et interruptions (Ctrl+C)
- ✅ Menu interactif utilisateur
- ✅ État workflow persistant (WorkflowState)

**Intégrations :**
- ✅ API Intervals.icu fonctionnelle
- ✅ Presse-papier macOS automatique
- ✅ Git commit automatisé
- ✅ Support mode batch multi-séances

**Validation :**
- ✅ Convention casse stricte (S MAJUSCULE)
- ✅ Détection fichiers non conformes
- ✅ Propositions corrections automatiques

---

## 📁 Contenu Archive

### Scripts Workflow Quotidien (Production Stable)

| Script | Lignes | Rôle | État | Réutilisation v2 |
|--------|--------|------|------|------------------|
| `workflow_coach.py` | 1485 | Orchestrateur 7 étapes | ✅ Mature | Architecture modèle |
| `collect_athlete_feedback.py` | 419 | Collecte RPE + ressenti | ✅ Validé | Logique intégrer |
| `prepare_analysis.py` | 1163 | API + prompt génération | ✅ Validé | Factoriser core |
| `insert_analysis.py` | 439 | Insertion analyses markdown | ✅ Validé | Logique intégrer |

**Performance actuelle :**
- Temps moyen : 3-6 minutes ✅
- Étapes : 7 (+ 1b conditionnelle si multi-séances)
- Mode batch : Supporte analyse multiple séances
- Taux succès : ~95%

**Fonctionnalités clés :**
- Collecte feedback athlète (RPE 1-10, ressenti, contexte)
- Génération prompt Claude optimisé (contexte complet)
- Copie automatique presse-papier macOS
- Insertion analyse validée dans `workouts-history.md`
- Commit git automatique avec message descriptif
- Gestion interruptions propres

### Scripts Workflow Hebdomadaire (Partiel)

| Script | Lignes | État | Problèmes | Action v2 |
|--------|--------|------|-----------|-----------|
| `weekly_analysis.py` | 730 | ✅ Extraction OK | Pas de compilation dataset | Extraire logique parser |
| `prepare_weekly_report.py` | 367 | ⚠️ Bugs casse | Convention s minuscule (lignes 154-205) | NE PAS réutiliser |
| `organize_weekly_report.py` | 330 | ⚠️ Bugs casse | Validation s minuscule (lignes 116-121) | Extraire logique parsing |

**Problème critique identifié :**
- Génération prompts avec `s067` (minuscule) au lieu de `S067` (MAJUSCULE)
- Validation fichiers attend format incorrect
- Impact : 50% fichiers production non conformes (S067, S070)
- Correction : Scripts v2 doivent respecter convention stricte

### Scripts Utilitaires

| Script | Lignes | Rôle | Réutilisation v2 |
|--------|--------|------|------------------|
| `validate_naming_convention.py` | 251 | Validation casse stricte | Adapter `src/core/file_validator.py` |

**Validation convention :**
- Détection automatique fichiers non conformes
- Regex : `^[a-z_]+_S\d{3}(?:_S\d{3})?\.md$`
- Propositions corrections batch
- Génération rapport audit complet

### Documentation

| Fichier | Taille | Contenu |
|---------|--------|---------|
| `docs/WORKFLOW_COMPLET.md` | ~510 lignes | Guide workflow quotidien complet |
| `references/project_prompt_v2_1_revised.md` | ~15k tokens | Contexte athlète détaillé |
| `references/cycling_training_concepts.md` | ~8k tokens | Concepts entraînement cyclisme |
| `AUDIT_NAMING_FILES.md` | Variable | Audit convention casse (si généré) |

### Données Exemple

| Fichier | Rôle |
|---------|------|
| `logs/workouts-history.md` | Historique toutes séances (structure référence) |

---

## 🔧 Logique à Extraire (Factorisation v2)

### 1. Client API Intervals.icu

**Source :** `prepare_analysis.py` (lignes ~50-250)  
**Destination v2 :** `src/core/intervals_api.py`  
**Raison :** Dupliqué dans 3+ scripts

**Fonctionnalités à extraire :**
```python
class IntervalsAPI:
    def __init__(self, athlete_id: str, api_key: str)
    def get_activities(self, oldest=None, newest=None) -> List[Dict]
    def get_activity(self, activity_id: str) -> Dict
    def get_wellness(self, oldest=None, newest=None) -> List[Dict]
    def get_events(self, oldest=None, newest=None) -> List[Dict]
    def _create_session(self) -> requests.Session  # Retry logic
```

**Points d'attention :**
- Gestion retry automatique (3 tentatives)
- Timeout configuré (30s)
- Headers auth Basic
- Gestion erreurs HTTP cohérente

### 2. Parsing Markdown Séances

**Source :** `weekly_analysis.py` (lignes ~104-150)  
**Destination v2 :** `src/core/markdown_parser.py`  
**Raison :** Logique réutilisable tous niveaux (semaine, micro-cycle, macro-cycle)

**Fonctionnalités à extraire :**
```python
def extract_sections(
    content: str, 
    level: int = 3,
    date_filter: Optional[tuple] = None
) -> List[Dict]:
    """Extraire sections ### avec filtrage dates optionnel"""
```

**Regex clés :**
```python
# Titre section
r'^###\s+(.+)$'

# Date séance
r'Date\s*:\s*(\d{2}/\d{2}/\d{4})'

# Métriques
r'TSS\s*:\s*(\d+)'
r'IF\s*:\s*([\d.]+)'
r'RPE\s*:\s*(\d+)/10'
```

### 3. Validation Casse Fichiers

**Source :** `validate_naming_convention.py` (lignes ~40-100)  
**Destination v2 :** `src/core/file_validator.py`  
**Raison :** Validation nécessaire partout (daily, weekly, cycles)

**Fonctionnalités à extraire :**
```python
def validate_filename(filename: str, pattern: str) -> bool
def detect_non_compliant_files(directory: Path) -> List[Path]
def suggest_corrections(files: List[Path]) -> Dict[Path, Path]
def generate_audit_report(directory: Path) -> str
```

**Convention stricte (NON-NÉGOCIABLE) :**
```
Format : type_SXXX.md  (S MAJUSCULE obligatoire)

Valides :
✅ bilan_final_S067.md
✅ metrics_evolution_S067.md
✅ transition_S067_S068.md

Invalides :
❌ bilan_final_s067.md   (s minuscule)
❌ BilanFinal_S067.md    (CamelCase)
❌ bilan-final-S067.md   (tirets)
```

### 4. Parsing Presse-Papier

**Source :** `organize_weekly_report.py` (lignes ~60-93)  
**Destination v2 :** `src/utils/clipboard.py`  
**Raison :** Réutilisable workflows multiples (weekly, cycles)

**Fonctionnalités à extraire :**
```python
def get_clipboard_content() -> str
def parse_markdown_blocks(content: str, separator: str = "---") -> List[str]
def copy_to_clipboard(content: str) -> bool
```

**Format attendu parsing :**
```
Fichier 1 contenu markdown
---
Fichier 2 contenu markdown
---
...
---
Fichier N contenu markdown
```

### 5. Git Operations

**Source :** `workflow_coach.py` (lignes ~800-900)  
**Destination v2 :** `src/core/git_operations.py`  
**Raison :** Pattern commit/backup répété dans workflows

**Fonctionnalités à extraire :**
```python
def git_commit(
    files: List[Path],
    message: str,
    skip_git: bool = False
) -> bool

def create_backup(
    target_dir: Path,
    backup_suffix: str = None
) -> Path

def git_diff_preview(files: List[Path]) -> str
```

**Format message commit :**
```
Analyse séance S067-03 (S067/DATE)
- TSS: 54
- Type: INT-SweetSpot
```

### 6. Workflow State Management

**Source :** `workflow_coach.py` (lignes ~100-200)  
**Destination v2 :** `src/utils/workflow_state.py`  
**Raison :** Tracking état nécessaire tous workflows

**Fonctionnalités à extraire :**
```python
class WorkflowState:
    def __init__(self, state_file: Path)
    def load_state(self) -> Dict
    def save_state(self, state: Dict)
    def get_last_analyzed_workout(self) -> Optional[str]
    def mark_workout_analyzed(self, workout_name: str)
    def get_unanalyzed_workouts(self, all_workouts: List[str]) -> List[str]
```

---

## 🚨 Problèmes Connus v1 (À Corriger v2)

### 1. Convention Casse Incorrecte (CRITIQUE)

**Scripts concernés :**
- `prepare_weekly_report.py` (lignes 154, 166, 175, 185, 195, 205)
- `organize_weekly_report.py` (lignes 116-121)

**Exemple bug :**
```python
# ❌ INCORRECT (v1 - génère fichiers invalides)
expected_files = [
    f"workout_history_s{week}.md",      # s minuscule
    f"metrics_evolution_s{week}.md",
    # ...
]

# ✅ CORRECT (v2 - convention stricte)
expected_files = [
    f"workout_history_S{week:03d}.md",  # S MAJUSCULE + padding
    f"metrics_evolution_S{week:03d}.md",
    # ...
]
```

**Impact production :**
- 12/24 fichiers générés non conformes (50%)
- Semaines affectées : S067, S070
- Nécessite renommage manuel post-génération

**Correction v2 :**
- Validation stricte avant écriture
- Regex pattern : `^[a-z_]+_S\d{3}(?:_S\d{3})?\.md$`
- Tests unitaires convention
- Fail-fast si non conforme

### 2. Duplication Code (MAINTENANCE)

**Patterns dupliqués identifiés :**

| Pattern | Occurrences | Impact |
|---------|-------------|--------|
| Client API Intervals.icu | 3 scripts | Bugs propagés, maintenance x3 |
| Parsing markdown séances | 2 scripts | Logique divergente |
| Validation casse | 2 scripts | Conventions inconsistantes |
| Git operations | 2 scripts | Messages commit différents |

**Solution v2 :**
- Modules core factorisés (`src/core/`)
- Import unique depuis modules
- Tests unitaires modules core
- Documentation API centralisée

### 3. Absence Tests (QUALITÉ)

**État actuel :**
- ❌ 0 test unitaire
- ❌ 0 test intégration
- ⚠️ Validation manuelle uniquement

**Risques :**
- Régressions non détectées
- Refactoring dangereux
- Bugs production fréquents

**Solution v2 :**
- Tests unitaires obligatoires (>70% couverture)
- Tests intégration workflows
- CI/CD avec pytest
- Fixtures pour mocking API

### 4. Logging Basique (DEBUG)

**État actuel :**
```python
# ❌ Print statements partout
print("Processing workout...")
print(f"Error: {e}")
```

**Problèmes :**
- Pas de niveaux (DEBUG/INFO/WARNING/ERROR)
- Pas de timestamps
- Pas de rotation logs
- Output console uniquement

**Solution v2 :**
```python
# ✅ Logging structuré
logger.info("Processing workout %s", workout_name)
logger.error("API error: %s", e, exc_info=True)
```

**Configuration v2 :**
- Logging centralisé (`src/utils/logging_config.py`)
- Rotation fichiers (10MB, 5 backups)
- Timestamps ISO format
- Niveaux cohérents

### 5. Gestion Erreurs Inconsistante

**État actuel :**
```python
# ❌ Exceptions génériques
except Exception as e:
    print(f"Error: {e}")
    return None
```

**Problèmes :**
- Erreurs trop génériques
- Messages peu explicites
- Pas de traçabilité
- Recovery incohérent

**Solution v2 :**
```python
# ✅ Hiérarchie exceptions personnalisées
class CyclismeAutomationError(Exception): pass
class APIError(CyclismeAutomationError): pass
class ValidationError(CyclismeAutomationError): pass

try:
    data = api.get_activities()
except requests.RequestException as e:
    raise APIError(f"Failed to fetch activities: {e}") from e
```

---

## 📐 Architecture Production v1

### Structure Répertoires
```
/Users/stephanejouve/cyclisme-training-logs/
│
├── scripts/                              # 39 scripts Python
│   ├── collect_athlete_feedback.py       # Collecte feedback
│   ├── prepare_analysis.py               # Génération prompts
│   ├── insert_analysis.py                # Insertion analyses
│   ├── workflow_coach.py                 # Orchestrateur daily
│   ├── weekly_analysis.py                # Extraction séances semaine
│   ├── prepare_weekly_report.py          # Génération prompt hebdo
│   ├── organize_weekly_report.py         # Organisation rapports
│   ├── validate_naming_convention.py     # Validation casse
│   └── ...                               # Autres utilitaires
│
├── logs/
│   ├── daily/
│   │   └── workouts-history.md           # Historique complet séances
│   └── weekly_reports/
│       ├── S067/                         # 6 fichiers markdown
│       │   ├── bilan_final_S067.md
│       │   ├── metrics_evolution_S067.md
│       │   ├── training_learnings_S067.md
│       │   ├── protocol_adaptations_S067.md
│       │   ├── transition_S067_S068.md
│       │   └── workout_history_S067.md
│       ├── S068/
│       └── ...
│
├── data/
│   ├── prompts/                          # Prompts générés
│   │   └── daily/
│   └── .athlete_feedback/                # Feedback JSON
│       └── last_feedback.json
│
├── references/
│   ├── project_prompt_v2_1_revised.md    # Contexte athlète
│   ├── cycling_training_concepts.md      # Concepts entraînement
│   └── ...
│
├── docs/
│   └── WORKFLOW_COMPLET.md               # Documentation workflow
│
└── .git/                                 # Version control
```

### Workflow Daily (Production Actuelle)
```
┌─────────────────────────────────────────────────────────────┐
│ WORKFLOW QUOTIDIEN (3-6 min)                                │
│                                                              │
│  Étape 1   │ Welcome & Vérifications                        │
│            │ - Version script                               │
│            │ - Branche git                                  │
│            │ - Workouts non analysés                        │
│            │                                                 │
│  Étape 1b  │ Sélection Workout (si multi-séances)          │
│ (Cond.)    │ - Option 1: Dernière séance                   │
│            │ - Option 2: Choisir séance                     │
│            │ - Option 3: Mode batch                         │
│            │                                                 │
│  Étape 2   │ Collecte Feedback Athlète                     │
│            │ - RPE (1-10)                                   │
│            │ - Ressenti général                             │
│            │ - Contexte (mode quick/full)                   │
│            │ - Sauvegarde JSON                              │
│            │                                                 │
│  Étape 3   │ Préparation Analyse                           │
│            │ - Extraction données séance                    │
│            │ - Récupération métriques API                   │
│            │ - Génération prompt Claude                     │
│            │ - Copie presse-papier auto                     │
│            │                                                 │
│  Étape 4   │ Attente Analyse Claude                        │
│            │ - Utilisateur colle prompt dans Claude.ai      │
│            │ - Claude génère analyse complète               │
│            │ - Copie analyse dans presse-papier             │
│            │                                                 │
│  Étape 5   │ Validation Analyse                            │
│            │ - Lecture presse-papier                        │
│            │ - Vérification format markdown                 │
│            │ - Confirmation utilisateur                     │
│            │                                                 │
│  Étape 6   │ Insertion Analyse                             │
│            │ - Backup workouts-history.md                   │
│            │ - Insertion analyse validée                    │
│            │ - Mise à jour fichier                          │
│            │                                                 │
│  Étape 7   │ Commit Git                                    │
│            │ - Message auto-généré                          │
│            │ - Commit fichiers modifiés                     │
│            │ - Push optionnel                               │
│            │                                                 │
│            │ ✅ TERMINÉ - Durée: 3-6 min                    │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Weekly (Manuel Actuel)
```
┌─────────────────────────────────────────────────────────────┐
│ WORKFLOW HEBDOMADAIRE (Plusieurs heures - MANUEL)           │
│                                                              │
│  Phase 1   │ Extraction Données                             │
│            │ - Lire workouts-history.md                     │
│            │ - Filtrer semaine SXXX                         │
│            │ - Compiler métriques manuellement              │
│            │                                                 │
│  Phase 2   │ Analyse Manuelle                              │
│            │ - Relire 7 séances                             │
│            │ - Identifier patterns                          │
│            │ - Calculer évolutions                          │
│            │                                                 │
│  Phase 3   │ Rédaction 6 Rapports                          │
│            │ - workout_history_SXXX.md                      │
│            │ - metrics_evolution_SXXX.md                    │
│            │ - training_learnings_SXXX.md                   │
│            │ - protocol_adaptations_SXXX.md                 │
│            │ - transition_SXXX_SXXX.md                      │
│            │ - bilan_final_SXXX.md                          │
│            │                                                 │
│  Phase 4   │ Organisation                                  │
│            │ - Créer répertoire SXXX/                       │
│            │ - Copier 6 fichiers                            │
│            │ - Validation manuelle                          │
│            │                                                 │
│  Phase 5   │ Templates Semaine Suivante                    │
│            │ - Rédaction manuelle                           │
│            │ - Adaptation selon acquis                      │
│            │                                                 │
│            │ ⚠️ PROBLÈME: Plusieurs heures manuelles        │
│            │ 🎯 OBJECTIF v2: 10-15 min automatisées         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Métriques v1

### Performance Workflow Quotidien

| Métrique | Valeur | Cible |
|----------|--------|-------|
| Temps moyen | 3-6 min | ✅ Atteint |
| Taux succès | ~95% | ✅ Excellent |
| Étapes manuelles | 2 (coller prompt, copier analyse) | ✅ Acceptable |
| Interruptions possibles | Oui (Ctrl+C propre) | ✅ Robuste |

### Limitations Workflow Hebdomadaire

| Métrique | Valeur Actuelle | Cible v2 |
|----------|-----------------|----------|
| Temps total | Plusieurs heures | 10-15 min |
| Étapes manuelles | 5 phases complètes | 3 étapes guidées |
| Compilation données | Manuelle | Automatisée |
| Génération rapports | Manuelle (6 fichiers) | Automatisée |
| Validation casse | Manuelle post-génération | Automatique pré-écriture |

### Statistiques Production

**Séances analysées :** 312+ (depuis début système)  
**Rapports hebdo générés :** 15+ semaines (S067-S082+)  
**Taux conformité casse :** 50% (problème bugs scripts)  
**Temps économisé daily :** ~2-3h/semaine (vs analyse manuelle)  
**Temps perdu weekly :** ~4-6h/semaine (workflow manuel)

---

## 🎯 Utilisation Archive v2

### ✅ À FAIRE

**Étudier architecture éprouvée :**
- `workflow_coach.py` : Orchestration séquentielle modèle
- WorkflowState : Tracking état séances
- Menu interactif : Pattern UX validé
- Gestion erreurs : Try/except robuste

**Extraire logique modules core :**
- IntervalsAPI → `src/core/intervals_api.py`
- Parsing markdown → `src/core/markdown_parser.py`
- Validation casse → `src/core/file_validator.py`
- Git operations → `src/core/git_operations.py`

**Réutiliser patterns éprouvés :**
- Collecte feedback athlète (RPE, ressenti, contexte)
- Génération prompts optimisés (contexte complet)
- Copie presse-papier automatique
- Commit git avec messages descriptifs

**Respecter conventions strictes :**
- Format fichiers : `type_SXXX.md` (S MAJUSCULE)
- Validation pre-flight avant écriture
- Regex pattern strict
- Tests unitaires convention

### ❌ À NE PAS FAIRE

**Copier/coller aveuglément :**
- Code non documenté
- Duplication logique
- Bugs connus (casse incorrecte)

**Reproduire limitations v1 :**
- Absence tests unitaires
- Logging basique
- Exceptions génériques
- Pas de factorisation

**Ignorer problèmes identifiés :**
- Convention casse incorrecte (scripts hebdo)
- Duplication client API
- Validation inconsistante
- Workflow hebdo manuel

**Négliger qualité :**
- Documentation incomplète
- Tests manquants
- Gestion erreurs faible
- Pas de type hints

---

## 🚀 Recommandations Développement v2

### Architecture Modulaire (Obligatoire)
```
src/
├── core/                    # Modules communs factorisés
│   ├── intervals_api.py     # Client API unique
│   ├── markdown_parser.py   # Parsing générique
│   ├── prompt_generator.py  # Génération prompts
│   ├── file_validator.py    # Validation stricte
│   └── git_operations.py    # Git commit/backup
│
├── analyzers/               # Analyseurs par niveau
│   ├── workout_analyzer.py  # Séance (migré v1)
│   └── weekly_analyzer.py   # Semaine (nouveau)
│
├── workflows/               # Orchestrateurs
│   ├── workflow_daily.py    # Quotidien (migré)
│   └── workflow_weekly.py   # Hebdo (nouveau)
│
└── utils/                   # Utilitaires
    ├── date_utils.py
    ├── naming_conventions.py
    └── clipboard.py
```

### Standards Qualité (Non-Négociables)

**1. Documentation obligatoire :**
- Docstring module complet
- Docstring fonction/méthode avec Args/Returns/Raises
- Type hints partout
- Examples usage

**2. Tests unitaires :**
- Couverture >70%
- Pytest + fixtures
- Mocking API externes
- Tests intégration workflows

**3. Logging structuré :**
- Configuration centralisée
- Rotation fichiers logs
- Niveaux cohérents (DEBUG/INFO/WARNING/ERROR)
- Timestamps ISO

**4. Gestion erreurs :**
- Hiérarchie exceptions personnalisées
- Messages explicites
- Logging erreurs critiques
- Recovery cohérent

**5. Factorisation stricte :**
- DRY (Don't Repeat Yourself)
- Duplication >5 lignes → fonction
- Pattern répété 3+ fois → classe abstraite
- Logique commune → module core

### Migration Progressive

**Phase 1 : Workflow Hebdo (Prioritaire)**
- Développer modules core
- Implémenter workflow_weekly.py
- Tests validation
- Documentation

**Phase 2 : Validation Production**
- Tester sur S072, S073, S074
- Identifier bugs/améliorations
- Itérer corrections

**Phase 3 : Migration Daily (Optionnel)**
- Migrer workflow quotidien vers architecture modulaire
- Bénéficier modules core partagés
- Déprécier scripts v1 progressivement

---

## 📞 Support & Contact

**Développement v2 :** Supervisé par Stéphane Jouve  
**Date archive :** 2025-01-15  
**Version production :** v1 (stable, workflow daily opérationnel)  
**Objectif v2 :** Architecture modulaire, workflow hebdo automatisé

**Notes importantes :**
- Archive fournie référence uniquement
- Ne pas modifier code production v1 directement
- Développement v2 en parallèle (zéro risque production)
- Migration progressive après validation v2

---

**FIN ARCHIVE_README.md**
