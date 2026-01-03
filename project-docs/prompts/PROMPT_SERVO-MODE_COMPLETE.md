# PROMPT: Fix Servo Mode Complet - Session 28/12/2025

## Contexte Projet

Tu es Claude Code, assistant de développement pour le projet cyclisme-training-logs.
Stéphane (54 ans, cycliste) utilise ce projet pour gérer ses entraînements.

**Architecture:**
- Repo code: `~/cyclisme-training-logs` (Python, Poetry)
- Repo data: `~/training-logs` (données séparées)
- Config centralisée: `cyclisme_training_logs/config.py`

## État Actuel (Fin 27/12)

### ✅ Complété Hier
- Paranoid duplicate detection (9 tests passing)
- Migration docstrings Google Style (27 fichiers, 100%)
- Réorganisation docs/ structure Python standard
- Sphinx build fonctionnel
- Fix planning path detection (8 occurrences hardcodées)
- 17 commits pushés

### 🐛 Bugs Servo Mode Identifiés (3 Issues GitHub)

**Issue #1: Provider Integration Missing**
- Servo mode utilise toujours clipboard, même si `--ai-provider` configuré
- Devrait appeler API directement quand provider disponible
- Fichiers: `servo_mode.py`, `workflow_coach.py`

**Issue #2: JSON Parsing Fails**
- Réponse AI valide (`{"modifications": [...]}`) détectée comme "aucune modification"
- Causes: Regex sans DOTALL, markdown backticks, logging insuffisant
- Fichier: `servo_mode.py` (fonction `parse_ai_response`)

**Issue #3: Feedback Skip Logic**
- Demande permission feedback, puis skip si pas de gaps
- Incohérent avec choix utilisateur
- Fichiers: `collect_athlete_feedback.py`, `workflow_coach.py`

### 🎯 Objectifs Session

**Priorité P0 (Bloquants):**
1. Fix provider integration (Issue #1)
2. Fix JSON parsing (Issue #2)

**Priorité P1 (Important):**
3. Fix feedback skip logic (Issue #3)
4. Fix commit message `\n` littéral (bug Git connu)

**Priorité P2 (Nice to have):**
5. Tests validation servo mode end-to-end
6. Documentation servo mode usage

## Workflow Session

### Phase 1: Diagnostic (15 min)
```bash
# 1. Lire issues GitHub créées
gh issue list --label "servo-mode"

# 2. Localiser code exact
grep -rn "parse_ai_response" cyclisme_training_logs/
grep -rn "Demander recommandations au coach AI" cyclisme_training_logs/
grep -rn "ai_provider\|provider" cyclisme_training_logs/servo_mode.py

# 3. Lire code actuel complet
cat cyclisme_training_logs/servo_mode.py
cat cyclisme_training_logs/workflow_coach.py | grep -A 50 "servo"

# 4. Identifier dépendances
grep -rn "from.*servo_mode import" cyclisme_training_logs/
```

### Phase 2: Fix Provider Integration (45 min)

**Objectif:** Appel API automatique si provider configuré

**Étapes:**
1. Modifier `ServoMode.__init__()` pour accepter `ai_provider`
2. Ajouter méthode `_call_api_provider(prompt)` vs `_clipboard_workflow(prompt)`
3. Logique décision dans `get_ai_recommendations()`
4. Mettre à jour `workflow_coach.py` pour passer provider
5. Tests unitaires mocking provider

**Code Attendu:**
```python
class ServoMode:
    def __init__(self, config, ai_provider=None):
        self.config = config
        self.provider = ai_provider

    def get_ai_recommendations(self, planning_data):
        prompt = self._generate_prompt(planning_data)

        if self.provider:
            logger.info(f"🤖 Appel API {self.provider.name}")
            return self._call_api_provider(prompt)
        else:
            logger.info("📋 Mode manuel (clipboard)")
            return self._clipboard_workflow(prompt)

    def _call_api_provider(self, prompt):
        """Appel API direct."""
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3
        )
        return self._parse_response(response)

    def _clipboard_workflow(self, prompt):
        """Workflow clipboard actuel."""
        copy_to_clipboard(prompt)
        print("📋 Colle dans ton IA...")
        input("ENTER après copie réponse...")
        response = paste_from_clipboard()
        return self._parse_response(response)
```

**Validation:**
```bash
# Test avec provider
poetry run workflow-coach --activity-id <ID> --ai-provider claude --servo-mode

# Attendu: Pas de prompt clipboard, appel API direct

# Test sans provider
poetry run workflow-coach --activity-id <ID> --servo-mode

# Attendu: Workflow clipboard actuel
```

### Phase 3: Fix JSON Parsing (30 min)

**Objectif:** Parser correctement JSON AI (markdown, multi-lignes)

**Étapes:**
1. Refactorer `parse_ai_response()` avec logging détaillé
2. Gérer markdown code blocks (```json...```)
3. Regex DOTALL + MULTILINE
4. Vérifier longueur liste modifications
5. Tests unitaires avec exemples réels

**Code Attendu:**
```python
def _parse_response(self, response_text):
    """Parse réponse AI - robuste."""
    logger.debug(f"Raw response: {response_text[:200]}...")

    if not response_text or not response_text.strip():
        logger.warning("Réponse vide")
        return {"modifications": []}

    # Nettoyer markdown
    text = response_text.strip()
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    logger.debug(f"After markdown cleanup: {text[:200]}...")

    # Extraire JSON (multi-lignes)
    json_match = re.search(
        r'\{.*?"modifications".*?\}',
        text,
        re.DOTALL | re.MULTILINE
    )

    if not json_match:
        logger.error("Pas de JSON trouvé dans réponse")
        return {"modifications": []}

    try:
        data = json.loads(json_match.group())
        logger.debug(f"JSON parsed: {data.keys()}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON invalide: {e}")
        return {"modifications": []}

    # Vérifier modifications
    mods = data.get("modifications", [])

    if not isinstance(mods, list):
        logger.error(f"modifications not a list: {type(mods)}")
        return {"modifications": []}

    logger.info(f"✅ {len(mods)} modification(s) parsée(s)")
    return data
```

**Tests:**
```python
# tests/test_servo_mode.py
def test_parse_json_nu():
    response = '{"modifications": [{"action": "lighten"}]}'
    result = servo._parse_response(response)
    assert len(result["modifications"]) == 1

def test_parse_json_markdown():
    response = '```json\n{"modifications": [...]}\n```'
    result = servo._parse_response(response)
    assert len(result["modifications"]) == 1

def test_parse_json_multilignes():
    response = '''
    {
      "modifications": [
        {
          "action": "lighten",
          "target_date": "2025-12-28"
        }
      ]
    }
    '''
    result = servo._parse_response(response)
    assert len(result["modifications"]) == 1

def test_parse_liste_vide():
    response = '{"modifications": []}'
    result = servo._parse_response(response)
    assert len(result["modifications"]) == 0
```

**Validation:**
```bash
# Tests unitaires
poetry run pytest tests/test_servo_mode.py -v

# Test intégration
echo '{"modifications": [{"action": "lighten"}]}' | pbcopy
poetry run workflow-coach --servo-mode
# Attendu: Détecte 1 modification
```

### Phase 4: Fix Feedback Skip Logic (20 min)

**Objectif:** Cohérence prompt utilisateur vs comportement

**Option Retenue:** Check gaps AVANT prompt

**Code Attendu:**
```python
def collect_athlete_feedback():
    """Collecte feedback - ne demande que si pertinent."""

    # Check gaps AVANT prompt
    gaps = detect_analysis_gaps()

    if not gaps:
        logger.info("✅ Toutes séances analysées, skip feedback")
        return

    # Si gaps: ALORS demander
    print(f"📊 {len(gaps)} séance(s) sans analyse détectée(s)")
    response = input("Collecter feedback ? (o/n): ")

    if response.lower() != 'o':
        return

    mode = input("Mode (1-Quick/2-Full): ")
    collect_feedback_for_gaps(gaps, mode)
```

**Validation:**
```bash
# Cas 1: Gaps présents
# Attendu: Demande permission

# Cas 2: Pas de gaps
# Attendu: Skip silencieux sans demander
```

### Phase 5: Fix Commit Message \n (15 min)

**Objectif:** Vraies newlines au lieu de `\n` littéral

**Fichier:** `servo_mode.py` (fonction commit_modifications)

**Code Attendu:**
```python
def commit_modifications(modifications):
    """Commit avec message multi-lignes propre."""

    # AVANT (bug)
    # message = f"feat: Servo adjustments\n\n{details}"

    # APRÈS (fix)
    message = f"""feat: Servo mode adjustments S{week_id}

Applied {len(modifications)} modification(s):
{format_modifications(modifications)}

Automated by servo mode based on AI recommendations.
"""

    subprocess.run(["git", "commit", "-m", message], check=True)
```

**Validation:**
```bash
# Après commit servo
git log -1 --format=%B

# Attendu: Multi-lignes propres, pas de \n littéral
```

### Phase 6: Tests & Documentation (30 min)

**Tests End-to-End:**
```bash
# Workflow complet avec provider
poetry run workflow-coach --activity-id <ID> --ai-provider claude --servo-mode --auto

# Vérifier:
# 1. Appel API direct (pas clipboard)
# 2. JSON parsé correctement
# 3. Modifications appliquées
# 4. Commit propre
# 5. Git log clean
```

**Documentation:**
```markdown
# docs/servo-mode-usage.md

## Servo Mode - Guide Utilisateur

### Avec Provider AI (Recommandé)
poetry run workflow-coach --activity-id <ID> --ai-provider claude --servo-mode

### Sans Provider (Manuel)
poetry run workflow-coach --activity-id <ID> --servo-mode
# → Workflow clipboard

### Exemples Réponses AI
[...]
```

## Commits Attendus

1. `fix(servo): Integrate AI provider for automatic recommendations`
2. `fix(servo): Robust JSON parsing with markdown support`
3. `fix(feedback): Check gaps before prompting user`
4. `fix(servo): Use proper newlines in commit messages`
5. `test(servo): Add end-to-end validation tests`
6. `docs(servo): Add usage guide and examples`

## Critères Succès

### Must-Have (P0)
- ✅ Provider configuré → API call direct
- ✅ JSON AI parsé correctement (markdown, multi-lignes)
- ✅ Tests unitaires passing (servo_mode.py)

### Should-Have (P1)
- ✅ Feedback skip logic cohérent
- ✅ Commit messages propres (newlines)
- ✅ Tests end-to-end passing

### Nice-to-Have (P2)
- ✅ Documentation usage
- ✅ Logging détaillé pour debug
- ✅ Error handling robuste

## Workflow Git
```bash
# Feature branch
git checkout -b fix/servo-mode-complete

# Commits atomiques par fix
git commit -m "fix(servo): provider integration"
git commit -m "fix(servo): JSON parsing"
# etc.

# Tests avant merge
poetry run pytest tests/ -v

# Merge si tout OK
git checkout main
git merge fix/servo-mode-complete
git push origin main
```

## Notes Importantes

### Config Paths
- ✅ Toujours utiliser `config.get_data_config()` pour paths
- ✅ Jamais hardcoder `"data/week_planning/..."`
- ✅ Architecture double-repo respectée

### AI Provider
- Providers disponibles: `claude`, `openai`, `mistral`, `ollama`
- Config dans `config.py` avec API keys
- Fallback clipboard si provider unavailable

### Paranoid Mode
- `auto_fix_duplicates = True` temporaire (remis à False après)
- Duplicate detection toujours active
- Tests duplicate_detector.py doivent passer

## Fichiers Clés

**À Modifier:**
- `cyclisme_training_logs/servo_mode.py` (3 fixes)
- `cyclisme_training_logs/workflow_coach.py` (integration)
- `cyclisme_training_logs/collect_athlete_feedback.py` (skip logic)

**À Créer:**
- `tests/test_servo_mode.py` (tests unitaires)
- `docs/servo-mode-usage.md` (documentation)

**À Référencer:**
- Issues GitHub #1, #2, #3
- Session 27/12 transcript
- FIX_SERVO_*.md (archives)

## Prêt à Démarrer

**Première Action:**
```bash
# Lire issues GitHub
gh issue list --label "servo-mode"

# Diagnostic code actuel
grep -rn "parse_ai_response" cyclisme_training_logs/
cat cyclisme_training_logs/servo_mode.py

# Confirmer plan avec Stéphane
echo "Plan validé? (Phase 1→6)"
```

---

**Bonne chance pour demain ! 🚀**

Session productive aujourd'hui, tout est tracé pour fix complet servo mode demain.
```

---

## 🎯 **Fichier à Créer**

**Sauvegarde ce prompt dans:**
```
project-docs/sessions/SESSION_20251228_FIX_SERVO_MODE.md
