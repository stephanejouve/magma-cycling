# TODO - Servo Mode Issues (Session Suivante)

**Date Création** : 2025-12-28
**Session** : Post-Fix Planning Path
**Priorité** : P2 (Non-bloquant, à traiter après backfill)
**Status** : 🟡 Documenté, en attente

---

## Contexte

3 nouvelles issues découvertes **après** les fixes de planning path (commits d809c83 + 3c86f84).
Ces bugs sont **indépendants** du fix planning path et concernent la logique interne du servo mode.

---

## Issue #2 : Clipboard Manuel Malgré AI Provider Configuré

**Lien** : https://github.com/stephanejouve/cyclisme-training-logs/issues/2
**Titre** : Servo mode prompts for manual clipboard even when AI provider configured
**Créé** : 2025-12-28
**État** : 🟢 Open

### Symptôme
Le servo mode demande une saisie manuelle via clipboard même quand `--provider claude` (ou autre) est configuré.

### Impact
- UX dégradée : Utilisateur doit copier/coller manuellement
- AI provider ignoré : Configuration `--provider` ne fonctionne pas
- Workflow interrompu : Demande intervention manuelle inutile

### Cause Probable
- Logique de fallback clipboard trop agressive
- Condition `if provider is None` incorrecte
- Provider bien initialisé mais non utilisé

### Fichiers à Investiguer
```
cyclisme_training_logs/workflow_coach.py
- Méthode: _get_servo_modifications() ou similaire
- Chercher: "clipboard", "paste", "provider"
- Ligne probable: 2450-2600 (section servo mode)
```

### Commandes Debug
```bash
# Trouver logique clipboard
grep -n "clipboard\|paste.*manual" cyclisme_training_logs/workflow_coach.py

# Trouver où provider est (ou n'est pas) utilisé
grep -n "self\.provider\|ai_provider" cyclisme_training_logs/workflow_coach.py | grep -A 5 -B 5 servo
```

### Fix Suggéré (À Valider)
```python
# AVANT (probable)
if not modifications:
    modifications = get_from_clipboard()  # Fallback systématique

# APRÈS
if self.provider:
    modifications = self.provider.generate(prompt)
else:
    modifications = get_from_clipboard()  # Fallback seulement si no provider
```

---

## Issue #3 : Servo Mode Dit "No Modifications" Avec JSON Valide

**Lien** : https://github.com/stephanejouve/cyclisme-training-logs/issues/3
**Titre** : Servo mode says "no modifications" when AI response contains valid JSON modifications
**Créé** : 2025-12-28
**État** : 🟢 Open

### Symptôme
L'IA retourne un JSON valide avec des modifications, mais le code affiche "Aucune modification recommandée" et skip.

### Impact
- Modifications AI ignorées : JSON valide perdu
- Servo mode inefficace : Ne fait rien alors que coach AI a des recommandations
- Workflow incomplet : Asservissement non appliqué

### Cause Probable
- Regex JSON extraction qui échoue silencieusement
- Parsing JSON qui catch exception et retourne None
- Validation schema trop stricte (rejette JSON valide)
- Mauvais format attendu (```json vs json direct)

### Exemple Probable
```python
# IA retourne:
{
  "modifications": [
    {
      "day": 3,
      "old_workout": "END",
      "new_workout": "INT",
      "reason": "Fatigue détectée"
    }
  ]
}

# Mais code cherche peut-être:
```json
{...}
```

# Ou attend différent schema
```

### Fichiers à Investiguer
```
cyclisme_training_logs/workflow_coach.py
- Méthode: _parse_servo_response() ou _extract_modifications()
- Chercher: "json.loads", "no modifications", "parse.*response"
- Section: Servo mode parsing (après appel AI)
```

### Commandes Debug
```bash
# Trouver parsing JSON servo
grep -n "json\.loads\|json\.dumps" cyclisme_training_logs/workflow_coach.py | grep -A 10 -B 10 servo

# Trouver message "no modifications"
grep -n "no modifications\|aucune modification\|Aucune modification" cyclisme_training_logs/workflow_coach.py

# Trouver regex extraction JSON
grep -n "```json\|re\.search.*json" cyclisme_training_logs/workflow_coach.py
```

### Fix Suggéré (À Valider)
```python
# Ajouter logging détaillé:
logger.debug(f"Raw AI response: {ai_response}")

try:
    # Essayer plusieurs patterns
    if "```json" in ai_response:
        json_str = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        modifications = json.loads(json_str.group(1))
    else:
        modifications = json.loads(ai_response)

    logger.debug(f"Parsed modifications: {modifications}")

except json.JSONDecodeError as e:
    logger.error(f"JSON parse error: {e}")
    logger.error(f"Failed content: {ai_response[:200]}")  # Log début pour debug
```

---

## Issue #4 : Feedback Collection Demande Permission Puis Skip

**Lien** : https://github.com/stephanejouve/cyclisme-training-logs/issues/4
**Titre** : Feedback collection asks permission then skips if no gaps detected
**Créé** : 2025-12-28
**État** : 🟢 Open

### Symptôme
Le workflow demande "Collecter feedback athlète ? [o/N]", utilisateur dit oui, puis code dit "Aucun gap détecté, skip feedback".

### Impact
- UX confuse : Demande permission inutilement
- Double-check redondant : Vérifie gaps deux fois
- Temps perdu : Utilisateur interrompu pour rien

### Cause Probable
- Check gaps APRÈS prompt permission (devrait être AVANT)
- Logique inversée : Demande permission inconditionnellement
- Gap detection dans mauvais ordre

### Flux Actuel (Probable)
```
1. Afficher: "Collecter feedback ? [o/N]"
2. User input: "o"
3. Check gaps → Aucun gap trouvé
4. Skip feedback
```

### Flux Correct
```
1. Check gaps silencieusement
2. SI gaps trouvés:
   a. Afficher: "X gaps détectés, collecter feedback ? [o/N]"
   b. User input: "o"
   c. Collecter feedback
3. SINON:
   Skip silencieusement (pas de prompt)
```

### Fichiers à Investiguer
```
cyclisme_training_logs/workflow_coach.py
- Méthode: _collect_feedback() ou step_feedback()
- Chercher: "feedback", "gaps", "skip"
- Section: Étape feedback collection
```

### Commandes Debug
```bash
# Trouver logique feedback
grep -n "collect.*feedback\|Collecter feedback" cyclisme_training_logs/workflow_coach.py

# Trouver check gaps
grep -n "gaps.*detected\|aucun gap\|no gap" cyclisme_training_logs/workflow_coach.py

# Trouver ordre des checks
grep -n "input.*feedback" cyclisme_training_logs/workflow_coach.py -A 20
```

### Fix Suggéré (À Valider)
```python
# AVANT (probable)
def collect_feedback(self):
    response = input("Collecter feedback ? [o/N]: ")

    if response.lower() == 'o':
        gaps = self.detect_gaps()
        if not gaps:
            print("Aucun gap, skip")
            return
        # ... collect

# APRÈS
def collect_feedback(self):
    gaps = self.detect_gaps()

    if not gaps:
        # Skip silencieusement
        return

    print(f"{len(gaps)} gap(s) détecté(s)")
    response = input("Collecter feedback ? [o/N]: ")

    if response.lower() == 'o':
        # ... collect
```

---

## Plan d'Action Session Suivante

### Phase 1 : Investigation (30-45 min)
1. **Lire body complet des 3 issues** (détails utilisateur)
   ```bash
   curl -s -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/stephanejouve/cyclisme-training-logs/issues/2 \
     | jq -r '.body'
   ```

2. **Chercher code problématique** (grep + read)
   ```bash
   grep -n "clipboard\|no modifications\|feedback.*gaps" cyclisme_training_logs/workflow_coach.py
   ```

3. **Identifier lignes exactes** (3 locations)

### Phase 2 : Fix (30-60 min)
1. **Issue #4** (feedback) - Plus simple, commencer par celle-ci
2. **Issue #2** (clipboard) - Moyenne complexité
3. **Issue #3** (JSON parsing) - Plus complexe, logger d'abord

### Phase 3 : Test (15-30 min)
1. Test manuel workflow avec servo mode
2. Vérifier chaque fix individuellement
3. Validation end-to-end

### Phase 4 : Commit + Close Issues (15 min)
```bash
# Commit fixes
git add cyclisme_training_logs/workflow_coach.py
git commit -m "fix(servo): Fix 3 servo mode issues (#2, #3, #4)"

# Close issues avec référence commit
gh issue close 2 --comment "Fixed in commit abc1234"
gh issue close 3 --comment "Fixed in commit abc1234"
gh issue close 4 --comment "Fixed in commit abc1234"
```

---

## Priorités

**P0** : Aucune (non-bloquant pour backfill)
**P1** : Issue #3 (JSON parsing - fonctionnalité core servo)
**P2** : Issue #2 (clipboard fallback - workaround existe)
**P3** : Issue #4 (feedback UX - cosmétique)

**Ordre suggéré fix** : #4 → #2 → #3 (simple → complexe)

---

## Notes Importantes

### Environnement Test
```bash
cd ~/training-logs
poetry run workflow-coach --activity-id <TEST_ID> --servo-mode --provider claude --auto
```

### Logs Debug
```bash
# Activer logging verbose
export LOG_LEVEL=DEBUG
poetry run workflow-coach ...
```

### Rollback Si Problème
```bash
# Commit avant fixes (reference point)
git log --oneline | head -5
# → 3c86f84 fix(servo): Fix ALL 7 hardcoded planning paths

# Rollback si besoin
git reset --hard 3c86f84
```

---

## Dépendances

**Prérequis** :
- ✅ Planning path fixé (commits d809c83 + 3c86f84)
- ✅ Auto-fix duplicates activé (config.py)
- ✅ GitHub token configuré (.env)

**Bloquants** :
- ❌ Aucun - Peut commencer immédiatement

**Nice-to-have** :
- Exemples concrets de JSON AI qui échouent (Issue #3)
- Screenshots comportement feedback (Issue #4)
- Logs complets workflow avec clipboard (Issue #2)

---

## Estimation Temps

**Total** : 1.5 - 2.5 heures

- Investigation : 30-45 min
- Fixes : 30-60 min (selon complexité JSON parsing)
- Tests : 15-30 min
- Commit + Close : 15 min
- Buffer : 15-30 min

**Recommandation** : Session dédiée, pas en fin de backfill (fatigue)

---

## Ressources

**GitHub Issues** :
- https://github.com/stephanejouve/cyclisme-training-logs/issues/2
- https://github.com/stephanejouve/cyclisme-training-logs/issues/3
- https://github.com/stephanejouve/cyclisme-training-logs/issues/4

**Code Principal** :
- `cyclisme_training_logs/workflow_coach.py` (lignes 2400-2700)

**Config** :
- `.env` (GITHUB_TOKEN configuré)

**Docs Session Actuelle** :
- `project-docs/SESSION_27DEC2025_RECOVERY_AND_COMPLETION.md`

---

**Prêt pour session suivante ! 🚀**
