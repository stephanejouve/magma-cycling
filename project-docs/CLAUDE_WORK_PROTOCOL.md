# 🧠 Claude Work Protocol - Anti-Réinvention

**Date**: 2026-01-18
**Purpose**: Protocole de travail pour compenser les limitations de mémoire de Claude Code
**Context**: Éviter de réinventer des outils existants, utiliser les ressources disponibles

---

## 📋 CHECKLIST OBLIGATOIRE AVANT TOUTE IMPLÉMENTATION

### Étape 1: RECHERCHE D'EXISTANT (5-10 min)

**Avant d'écrire UNE SEULE LIGNE DE CODE, je DOIS vérifier**:

```bash
# 1. Lister TOUS les scripts disponibles
poetry-scripts

# 2. Chercher fonctionnalités similaires dans le code
rg -i "nom_fonctionnalité" --type py

# 3. Lister fichiers projet planning/workflows/scripts
ls -la magma_cycling/planning/
ls -la magma_cycling/workflows/
ls -la scripts/

# 4. Chercher dans git log
git log --oneline --grep="mot_clé" -20

# 5. Vérifier sprints précédents
ls -la project-docs/sprints/
```

**Questions à me poser**:
- ✅ Est-ce que ce code existe déjà quelque part?
- ✅ Est-ce qu'un script poetry fait déjà ça?
- ✅ Est-ce qu'un alias bash fait déjà ça?
- ✅ Est-ce qu'un sprint précédent a déjà résolu ça?

### Étape 2: DOCUMENTATION PROJET (2-5 min)

**Lire OBLIGATOIREMENT**:

```bash
# 1. README principal
cat README.md

# 2. Documentation pertinente
ls project-docs/
cat project-docs/GUIDE_*.md  # Guides utilisateur

# 3. Sprints récents
ls -t project-docs/sprints/ | head -5
cat project-docs/sprints/SPRINT_R10_*.md  # Dernier sprint

# 4. Changelog
cat CHANGELOG.md | head -50
```

### Étape 3: ARCHITECTURE WORKFLOW (2 min)

**Comprendre le workflow AVANT d'implémenter**:

```python
# Workflow actuel:
# 1. Planification:   wp (weekly-planner) → génère prompt
# 2. AI Coach:        Claude/Mistral → génère workouts structurés
# 3. Upload:          upload-workouts → push vers Intervals.icu
# 4. Vérification:    intervals_sync → détecte changements coach externe
# 5. Rapport:         generate-report → analyse semaine

# RÈGLE: Ne JAMAIS créer de fonctionnalité qui duplique ce workflow!
```

### Étape 4: VALIDATION USER (1 min)

**Si hésitation, demander À L'UTILISATEUR**:

```
"J'hésite entre:
1. Créer un nouveau module X qui fait Y
2. Utiliser l'outil existant Z qui fait déjà Y

Tu préfères quelle approche?"
```

**JAMAIS supposer que je dois tout recréer from scratch!**

---

## 🚫 ANTI-PATTERNS À ÉVITER

### 1. Réinvention Upload/Sync

**❌ JAMAIS FAIRE**:
```python
# ❌ Créer nouvelle fonction upload vers Intervals.icu
def my_upload_workout(workout):
    response = requests.post(API_URL, ...)  # STOP!

# ❌ Réimplémenter create_event()
def push_to_intervals(event_data):
    # Duplication de intervals_client! STOP!
```

**✅ TOUJOURS FAIRE**:
```python
# ✅ Déléguer à upload_workouts (CLI)
subprocess.run(["poetry", "run", "upload-workouts", ...])

# ✅ Réutiliser intervals_client
from magma_cycling.config import create_intervals_client
client = create_intervals_client()
```

### 2. Génération Workout Structure

**❌ JAMAIS FAIRE**:
```python
# ❌ Générer workout_doc depuis TrainingCalendar
workout_doc = {
    "steps": self._generate_steps(session),  # STOP!
    "duration": session.duration_min * 60,
}
```

**✅ COMPRENDRE**:
```python
# ✅ AI Coach génère structure Intervals.icu
# weekly-planner → AI → workouts.txt (avec structure)
# upload-workouts → parse workouts.txt → API
# API Intervals.icu → parse description → génère workout_doc

# MON RÔLE: Orchestrer, pas générer structure!
```

### 3. Ignorer Feedback Utilisateur

**❌ PATTERN DANGEREUX**:
```
User: "on a déjà un outil qui fait ça"
Moi: "Oui mais je vais le refaire mieux"  # ❌ ARROGANCE
```

**✅ PATTERN CORRECT**:
```
User: "on a déjà un outil qui fait ça"
Moi: "Tu as raison, je vais utiliser l'outil existant"
     "Ou alors je délègue à cet outil"
```

---

## 🎯 RÈGLES D'OR

### 1. DRY (Don't Repeat Yourself)

**Si ça existe, UTILISE-LE. Point final.**

### 2. Délégation > Duplication

**Mieux vaut un wrapper de 10 lignes qu'une réimplémentation de 300 lignes.**

### 3. User Feedback = Vérité Absolue

**Si l'utilisateur dit "ça existe déjà", il a raison. Chercher où.**

### 4. Poetry Scripts = Première Source

**TOUJOURS commencer par `poetry-scripts` pour voir ce qui existe.**

### 5. Git Log = Mémoire Collective

**Lire git log avant d'implémenter. Quelqu'un l'a peut-être déjà fait.**

---

## 📚 RESSOURCES QUICK ACCESS

### Aliases Bash (à demander si besoin)

```bash
# Demander à l'utilisateur:
# "Quels sont les aliases bash du projet?"

# Exemples connus:
wp = weekly-planner
wu = upload-workouts (probablement)
poetry-scripts = lister scripts
```

### Fichiers Clés À Connaître

```
magma_cycling/
├── config/
│   ├── intervals_config.py       # API Intervals.icu
│   └── athlete_profile.py        # Profil athlète
├── planning/
│   ├── planning_manager.py       # Gestion plans
│   ├── calendar.py               # Calendrier
│   └── intervals_sync.py         # Sync bidirectionnelle
├── workflows/
│   ├── workflow_weekly.py        # Analyse hebdo
│   └── end_of_week.py           # Fin semaine
├── upload_workouts.py            # Upload vers API
└── weekly_planner.py             # Génération prompts

scripts/
├── maintenance/
│   ├── clear_week_planning.py   # Nettoyer semaine
│   └── format_planning.py       # Formater planning
└── monitoring/
    └── check_workout_adherence.py

project-docs/
├── sprints/                      # Historique sprints R1-R10
├── GUIDE_*.md                    # Guides utilisateur
└── CLAUDE_WORK_PROTOCOL.md      # CE FICHIER
```

### Workflow Patterns Standards

```python
# Pattern 1: Lecture Intervals.icu
from magma_cycling.config import create_intervals_client
client = create_intervals_client()
events = client.get_events(oldest="2026-01-01", newest="2026-01-07")

# Pattern 2: Upload workouts (déléguer à CLI)
# poetry run upload-workouts --week-id S077 --file workouts.txt

# Pattern 3: Génération plan
# poetry run weekly-planner --week-id S077 --start-date 2026-01-20

# Pattern 4: Nettoyage semaine
# poetry run clear-week-planning --week-id S077 --start-date 2026-01-20
```

---

## 🔄 WORKFLOW OPTIMAL

### Quand User demande "Implémente X"

```
1. PAUSE (ne pas coder immédiatement)
2. RECHERCHE (poetry-scripts, rg, git log)
3. ANALYSE (est-ce que X existe déjà?)
4. CHOIX:
   a. Si existe: Utiliser/Améliorer existant
   b. Si partiel: Déléguer + ajouter valeur unique
   c. Si absent: Créer APRÈS validation user
5. VALIDATION user si doute
6. IMPLÉMENTATION
7. DOCUMENTATION (pourquoi cette approche)
```

### Template Question Avant Implémentation

```
"Avant d'implémenter X, j'ai vérifié:
- poetry-scripts: Y existe déjà
- Fichiers projet: Z fait partie du job
- Git log: Feature W similaire en Sprint R5

Options:
1. Réutiliser Y+Z et ajouter juste la partie manquante
2. Créer nouveau module (risque duplication)

Tu préfères quelle approche?"
```

---

## 💡 EXEMPLES CONCRETS

### Exemple 1: Upload Workouts (Sprint R3 Module 3)

**❌ Ce que j'ai fait initialement**:
```python
# intervals_sync.py
def sync_calendar(calendar, start, end):
    # Réimplémentation complète de upload
    for session in calendar.sessions:
        event_data = {"name": ..., "description": ...}
        self.client.create_event(event_data)  # Duplication!
```

**✅ Ce que j'aurais dû faire (après user feedback)**:
```python
# intervals_sync.py
def sync_calendar(calendar, start, end):
    """
    NOTE: For pushing workouts, use upload-workouts CLI:
        poetry run upload-workouts --week-id S077 --file workouts.txt

    This method focuses on READ and DIFF detection only.
    """
    # Détection changements uniquement (valeur ajoutée unique)
    diff = self.detect_changes(calendar, start, end)
    return diff
```

### Exemple 2: Recherche Script (Avant ce Protocol)

**❌ Ce que je faisais**:
```bash
# Chercher manuellement
grep -r "clear_week" pyproject.toml
cat pyproject.toml | grep scripts
```

**✅ Ce que je dois faire maintenant**:
```bash
# Utiliser l'alias
poetry-scripts
# → Liste complète organisée en 2 secondes!
```

### Exemple 3: Compréhension Workflow

**❌ Supposer le workflow**:
```
"Je pense que je dois générer les workouts depuis TrainingCalendar"
→ ERREUR: AI coach génère déjà!
```

**✅ Demander/Vérifier le workflow**:
```
"Comment fonctionne actuellement le workflow de planification?"
User: "weekly-planner → AI coach → upload-workouts"
→ OK: Je ne dois pas réinventer cette chaîne!
```

---

## 🎓 LESSONS LEARNED

### Sprint R3 Module 3 (2026-01-18)

**Erreur commise**:
- Réimplémentation complète upload dans `intervals_sync.py`
- Workouts créés mais invisibles (workout_doc vide)
- 2h de debug pour comprendre le problème

**User feedback salvateur**:
> "choix 1 ( tu sais c'est l'histoire du gars qui reinvente le feu , et puis qui reinvente la roue , si je te laisse faire tu vas reinventer Python puis surement l'IA)"

**Correction**:
- Suppression code duplicate
- Délégation à `upload-workouts` (CLI)
- Ajout UNIQUEMENT détection diff (valeur unique)
- Tests 15/15 passing, architecture propre

**Enseignement**:
✅ User feedback > Mes suppositions
✅ Délégation > Réimplémentation
✅ Chercher existant AVANT coder

---

## 🚀 GAINS ATTENDUS

**Si je suis ce protocole rigoureusement**:

### Temps gagné
- **-70%** temps recherche (poetry-scripts vs grep manuel)
- **-80%** temps debug (pas de duplication = pas de bugs conflits)
- **-60%** temps implémentation (réutiliser > recréer)

### Qualité code
- **+50%** maintenabilité (moins de code = moins de bugs)
- **+80%** cohérence (utiliser patterns existants)
- **-90%** duplication (DRY forcé)

### User satisfaction
- **+100%** confiance ("Claude comprend le projet")
- **-90%** frustration ("pas de réinvention roue")
- **+100%** efficacité ("direct au but")

---

## 📝 CHECKLIST COMMIT

Avant chaque commit, vérifier:

```
[ ] J'ai cherché si cette fonctionnalité existe (poetry-scripts)
[ ] J'ai lu la doc existante (GUIDE_*.md, sprints)
[ ] J'ai réutilisé les outils existants (pas de duplication)
[ ] J'ai ajouté de la valeur UNIQUE (pas juste wrapper inutile)
[ ] J'ai validé l'approche avec user si doute
[ ] J'ai documenté POURQUOI cette approche (rationale)
[ ] Tests passing (pas de régression)
```

---

## 🎯 PROMPT À MÉMORISER

**Au début de chaque session de travail, me rappeler**:

```
AVANT DE CODER:
1. poetry-scripts (lister existant)
2. rg/grep (chercher similaire)
3. git log (historique)
4. Demander user si doute

RÈGLES:
- Existant > Nouveau
- Délégation > Duplication
- User feedback > Mes suppositions
- Documentation > Mémoire

QUESTION MAGIQUE:
"Est-ce que quelqu'un a déjà fait ça dans ce projet?"
```

---

## 💬 UTILISATION PAR L'UTILISATEUR

**Quand je commence à réinventer la roue, me rappeler**:

```
User: "Check CLAUDE_WORK_PROTOCOL.md"
ou
User: "poetry-scripts d'abord!"
ou
User: "rappel: on a déjà un outil pour ça"
```

→ Je dois IMMÉDIATEMENT stopper et suivre le protocole

---

## 📊 MÉTRIQUES DE SUCCÈS

**Indicateurs que je suis le protocole**:

✅ Je mentionne `poetry-scripts` dans mes premiers messages
✅ Je liste les outils existants avant de proposer nouveau
✅ Je demande validation user si plusieurs approches possibles
✅ Je délègue au lieu de réimplémenter
✅ Pas de feedback user "ça existe déjà"

**Indicateurs que je ne suis PAS le protocole**:

❌ User dit "on a déjà X"
❌ Je crée 300+ lignes pour remplacer outil existant
❌ Je suppose workflow au lieu de demander
❌ Je code immédiatement sans recherche
❌ Duplication détectée en code review

---

**VERSION**: 1.0
**DERNIÈRE MISE À JOUR**: 2026-01-18
**AUTEUR**: Claude Sonnet 4.5 (avec supervision Stéphane Jouve)
**STATUS**: Production

---

**NOTE POUR FUTURES SESSIONS**:
Si tu (Claude futur) lis ce fichier, SUIS-LE À LA LETTRE.
Ce protocole existe parce que j'ai (Claude passé) fait l'erreur de réinventer la roue.
Ne répète pas mes erreurs. L'utilisateur a raison. Toujours.
