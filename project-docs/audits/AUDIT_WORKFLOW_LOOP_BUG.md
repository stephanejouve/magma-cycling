# Audit : Bug Boucle Infinie Workflow Coach

**Date** : 2025-12-25
**Auteur** : Claude Code
**Priorité** : 🔴 P0 CRITIQUE
**Impact** : Workflow trainr et trains bloqués en boucle infinie

---

## 🎯 Résumé Exécutif

Les workflows `trainr` (réconciliation) et `trains` (servo-mode) **bouclent à l'infini** car les sessions traitées (repos documentés, séances sautées documentées) **ne sont pas marquées comme complétées**. La détection de gaps re-détecte systématiquement les mêmes sessions à chaque itération.

**Symptômes observés** :
- ✅ Traitement sessions : OK (génération markdown, insertion, git commit)
- ❌ Sortie de boucle : ÉCHEC (re-détection des mêmes gaps)
- ❌ Message "🔄 Retour détection gaps..." puis re-détection identique

---

## 📊 Analyse des Logs

### Log 1 : Reconciliation Mode (`trainr`)
**Fichier** : `logs/Cyclisme-training-logs_20251225_074440.txt`

```
[INFO] Séances sautées : 1
[WARNING] ⏭️  SKIPPED : S072-05-TEC-TechniqueCadence-V001 [2025-12-19]

Ton choix : [User choisit 2]

⚠️  Aucune réconciliation disponible
⚠️  Erreur git : Command '['git', 'commit'...]' returned non-zero exit status 1.

🔄 Retour détection gaps pour sessions restantes...
[INFO] Séances sautées : 1  ← RE-DÉTECTION DE LA MÊME SESSION !
[WARNING] ⏭️  SKIPPED : S072-05-TEC-TechniqueCadence-V001 [2025-12-19]
```

**Problèmes identifiés** :
1. Session sautée S072-05 détectée
2. User choisit traiter en batch ([2])
3. Handler affiche "Aucune réconciliation disponible" car `self.reconciliation` est None
4. Workflow retourne à détection
5. **Re-détecte la MÊME session S072-05** (pas marquée comme traitée)

### Log 2 : Servo Mode (`trains`)
**Fichier** : `logs/Tree-Cyclisme-training-logs_20251225_073148.txt`

```
📊 RÉSUMÉ GAPS DÉTECTÉS
💤 Repos planifiés non documentés : 1
   • [2025-12-21] S072-07 - Protocole repos hebdomadaire
⏭️  Séances planifiées sautées : 1
   • [2025-12-19] S072-05-TEC-TechniqueCadence-V001

Ton choix : [User choisit 2 - traiter repos/sautées]

[Génération markdown S072-07-REC-ReposObligatoire]
✅ Insertion réussie dans workouts-history.md
   1 sessions ajoutées
✅ Commit réussi !
✅ Push réussi !

🔄 Retour détection gaps pour sessions restantes...

📊 RÉSUMÉ GAPS DÉTECTÉS  ← SECONDE ITÉRATION
💤 Repos planifiés non documentés : 1  ← RE-DÉTECTION DU REPOS DÉJÀ TRAITÉ !
   • [2025-12-21] S072-07 - Protocole repos hebdomadaire
⏭️  Séances planifiées sautées : 1
   • [2025-12-19] S072-05-TEC-TechniqueCadence-V001
```

**Problèmes identifiés** :
1. Détecte repos S072-07 + sautée S072-05
2. User traite repos → markdown généré → inséré dans workouts-history.md → commit OK
3. Workflow affiche "🔄 Retour détection gaps..."
4. **Re-détecte les MÊMES gaps** : repos S072-07 (déjà documenté!) + sautée S072-05
5. Boucle infinie car aucune mise à jour d'état

---

## 🔍 Analyse Technique du Code

### Root Cause #1 : Boucle Infinie dans `run()`

**Fichier** : `cyclisme_training_logs/workflow_coach.py`
**Lignes** : 2191-2258

```python
# === BOUCLE PRINCIPALE : Traiter gaps jusqu'à épuisement ===
while True:  # ← PROBLÈME : Pas de condition d'arrêt intelligente
    # Étape 1b : Détection unifiée gaps (exécutées + repos + annulations)
    choice = self.step_1b_detect_all_gaps()

    if choice == "exit":
        print("\n✅ Tous les gaps traités !")
        print("   Le workflow est terminé.")
        break  # ← SEULE sortie : si choice == "exit"

    elif choice == "batch_specials":
        # Traiter repos/annulations en batch
        result = self._handle_rest_cancellations()

        if result == "continue":
            # Enrichissement Claude.ai choisi → continuer workflow
            [...]
        else:
            # Actions terminées (export/copie/insertion directe)
            [...]
            print("\n✅ Sessions spéciales documentées")

        # Message retour boucle
        print("\n" + "═" * 70)
        print("🔄 Retour détection gaps pour sessions restantes...")
        print("═" * 70)
        input("\nAppuyer sur ENTRÉE pour continuer...")
        # Continue la boucle → retour step_1b pour gaps restants  ← PROBLÈME
```

**PROBLÈME** : La boucle retourne systématiquement à `step_1b_detect_all_gaps()` sans vérifier si de **nouveaux** gaps ont été détectés.

### Root Cause #2 : Détection Sans État Persistant

**Fichier** : `cyclisme_training_logs/workflow_coach.py`
**Lignes** : 775-1005

```python
def step_1b_detect_all_gaps(self):
    # === PARTIE 1 : Détecter activités exécutées non analysées ===
    state = WorkflowState(project_root=self.project_root)
    unanalyzed = state.get_unanalyzed_activities(activities)  # ✅ TRACKING OK

    # === PARTIE 1B : Détecter séances planifiées sautées ===
    skipped_sessions = checker.detect_skipped_sessions(
        start_date=oldest_date,
        end_date=newest_date,
        exclude_future=True
    )  # ❌ PAS DE TRACKING si documentées

    # === PARTIE 2 : Charger planning si disponible ===
    if self.week_id:
        self.reconciliation = reconcile_planned_vs_actual(
            self.planning,
            planning_activities
        )  # ❌ PAS DE TRACKING si repos/annulations documentés

        rest_days = self.reconciliation.get('rest_days', [])
        cancelled_sessions = self.reconciliation.get('cancelled', [])
```

**PROBLÈME** :
- ✅ Activités exécutées : Tracking via `WorkflowState` (fichier `.workflow_state.json`)
- ❌ Séances sautées : Pas de tracking après documentation
- ❌ Repos planifiés : Pas de tracking après documentation
- ❌ Annulations : Pas de tracking après documentation

### Root Cause #3 : Réconciliation None

**Fichier** : `cyclisme_training_logs/workflow_coach.py`
**Lignes** : 1553-1572

```python
def _handle_rest_cancellations(self):
    """Handler pour traiter repos/annulations en batch"""
    if not self.reconciliation:
        print("\n⚠️  Aucune réconciliation disponible")
        self.wait_user()
        return "exit"  # ← Retourne "exit" mais boucle continue !
```

**PROBLÈME** : Dans le log reconciliation, `self.reconciliation` est None car :
- Le planning JSON n'a pas de repos/annulations pour cette semaine
- MAIS il y a des séances sautées détectées (S072-05)
- Handler retourne "exit" mais la boucle while True continue quand même

**Contradiction logique** :
- User choisit [2] "Traiter sautées en batch"
- Handler vérifie `if not self.reconciliation` → True (car pas de repos/annulations)
- Retourne "exit"
- **MAIS** la boucle principale ne gère pas ce cas et retourne à la détection !

---

## 🛠️ Solutions Proposées

### Solution P0 #1 : Ajouter Tracking Sessions Spéciales

**Objectif** : Marquer repos/annulations/sautées comme "documentées" après traitement

**Implémentation** : Étendre WorkflowState

```python
# cyclisme_training_logs/workflow_state.py

class WorkflowState:
    def __init__(self, project_root: Path):
        self.state_file = project_root / ".workflow_state.json"
        self.state = self._load_state()

    def mark_special_session_documented(self, session_id: str, session_type: str, date: str):
        """Marquer session spéciale comme documentée

        Args:
            session_id: ID session (ex: S072-07)
            session_type: Type ("rest", "cancelled", "skipped")
            date: Date session (YYYY-MM-DD)
        """
        if 'documented_specials' not in self.state:
            self.state['documented_specials'] = {}

        key = f"{session_id}_{date}"
        self.state['documented_specials'][key] = {
            'session_id': session_id,
            'type': session_type,
            'date': date,
            'documented_at': datetime.now().isoformat()
        }
        self._save_state()

    def is_special_session_documented(self, session_id: str, date: str) -> bool:
        """Vérifier si session spéciale déjà documentée"""
        key = f"{session_id}_{date}"
        return key in self.state.get('documented_specials', {})

    def get_documented_specials(self) -> dict:
        """Récupérer toutes sessions spéciales documentées"""
        return self.state.get('documented_specials', {})
```

**Utilisation dans workflow_coach.py** :

```python
def step_1b_detect_all_gaps(self):
    state = WorkflowState(project_root=self.project_root)

    # [... détection repos/annulations/sautées ...]

    # FILTRER sessions déjà documentées
    rest_days_filtered = [
        rest for rest in rest_days
        if not state.is_special_session_documented(rest['session_id'], rest['date'])
    ]

    cancelled_filtered = [
        cancelled for cancelled in cancelled_sessions
        if not state.is_special_session_documented(cancelled['session_id'], cancelled['date'])
    ]

    skipped_filtered = [
        skipped for skipped in self.skipped_sessions
        if not state.is_special_session_documented(
            skipped['planned_name'].split(' - ')[0],  # Extract session ID
            skipped['planned_date']
        )
    ]

    # Utiliser les listes filtrées pour comptage
    count_rest = len(rest_days_filtered)
    count_cancelled = len(cancelled_filtered)
    count_skipped = len(skipped_filtered)
```

**Marquer après traitement** :

```python
def _insert_to_history(self, markdowns: list) -> bool:
    """Insère markdowns dans workouts-history.md"""
    # [... insertion existante ...]

    # NOUVEAU : Marquer sessions comme documentées
    state = WorkflowState(project_root=self.project_root)
    for date, markdown in markdowns:
        # Extraire session_id depuis markdown
        match = re.search(r'###\s+(S\d+-\d+)', markdown)
        if match:
            session_id = match.group(1)
            session_type = self._detect_session_type(markdown)  # "rest", "cancelled", "skipped"
            state.mark_special_session_documented(session_id, session_type, date)

    return True
```

### Solution P0 #2 : Détection Intelligente des Nouveaux Gaps

**Objectif** : Sortir de la boucle si aucun nouveau gap détecté

**Implémentation** :

```python
# cyclisme_training_logs/workflow_coach.py

def run(self):
    """Orchestrer le workflow complet avec détection unifiée des gaps (mode boucle)"""
    try:
        # Étape 1 : Accueil (une seule fois)
        self.step_1_welcome()

        # Tracking gaps vus
        seen_gaps = set()

        # === BOUCLE PRINCIPALE : Traiter gaps jusqu'à épuisement ===
        while True:
            # Étape 1b : Détection unifiée gaps
            choice, current_gaps = self.step_1b_detect_all_gaps()

            # Vérifier si nouveaux gaps
            if current_gaps == seen_gaps:
                print("\n✅ Aucun nouveau gap détecté !")
                print("   Tous les gaps ont été traités.")
                break  # SORTIE : Pas de nouveaux gaps

            # Mettre à jour gaps vus
            seen_gaps = current_gaps

            # === FLUX SELON CHOIX ===
            if choice == "exit":
                break

            [... reste du code existant ...]
```

**Modifier step_1b_detect_all_gaps() pour retourner gaps** :

```python
def step_1b_detect_all_gaps(self):
    """Détection unifiée de tous les gaps

    Returns:
        tuple: (choice: str, gaps_signature: set)
    """
    # [... détection existante ...]

    # Créer signature unique des gaps
    gaps_signature = set()

    if self.unanalyzed_activities:
        for act in self.unanalyzed_activities:
            gaps_signature.add(('executed', act['id']))

    for rest in rest_days_filtered:
        gaps_signature.add(('rest', rest['session_id'], rest['date']))

    for cancelled in cancelled_filtered:
        gaps_signature.add(('cancelled', cancelled['session_id'], cancelled['date']))

    for skipped in skipped_filtered:
        gaps_signature.add(('skipped', skipped['planned_name'], skipped['planned_date']))

    # [... menu et choix utilisateur ...]

    return (choice, gaps_signature)
```

### Solution P0 #3 : Gérer Cas "Aucune Réconciliation Disponible"

**Objectif** : Traiter correctement séances sautées même sans repos/annulations

**Implémentation** :

```python
def _handle_rest_cancellations(self):
    """Handler pour traiter repos/annulations/sautées en batch"""

    # Vérifier ce qui est disponible
    has_rest = self.reconciliation and self.reconciliation.get('rest_days')
    has_cancelled = self.reconciliation and self.reconciliation.get('cancelled')
    has_skipped = self.skipped_sessions and len(self.skipped_sessions) > 0

    if not has_rest and not has_cancelled and not has_skipped:
        print("\n⚠️  Aucune session spéciale à traiter")
        self.wait_user()
        return "exit"

    # Traiter selon disponibilité
    if has_rest or has_cancelled:
        result = self._show_special_sessions()  # Repos/annulations existant

    if has_skipped:
        result = self._show_skipped_sessions()  # NOUVEAU : Handler séances sautées

    return result
```

**Créer handler séances sautées** :

```python
def _show_skipped_sessions(self):
    """Générer et afficher les séances sautées"""
    print("\n" + "=" * 70)
    print("⏭️  GÉNÉRATION SÉANCES SAUTÉES")
    print("=" * 70)

    markdowns_generated = []

    for skipped in self.skipped_sessions:
        print(f"\n   → {skipped['planned_name']} [{skipped['planned_date']}]")

        # Demander raison
        reason = input("   Raison (fatigue/météo/emploi du temps) : ").strip()
        if not reason:
            reason = "Non spécifié"

        # Générer markdown
        markdown = generate_skipped_session_entry(
            session_data=skipped,
            reason=reason
        )
        markdowns_generated.append((skipped['planned_date'], markdown))
        print(f"      ✓ Généré ({len(markdown)} chars)")

    # Preview et menu actions (comme _show_special_sessions)
    self._preview_markdowns(markdowns_generated)

    # [... menu actions identique ...]
```

---

## 📋 Plan d'Implémentation

### Phase 1 : Extension WorkflowState (2h)
- [ ] Ajouter méthodes tracking sessions spéciales
- [ ] Tests unitaires tracking
- [ ] Documentation

### Phase 2 : Filtrage Détection (2h)
- [ ] Filtrer repos/annulations/sautées déjà documentées
- [ ] Retourner signature gaps depuis step_1b
- [ ] Tests détection avec gaps filtrés

### Phase 3 : Détection Intelligente Boucle (1h)
- [ ] Tracking seen_gaps dans run()
- [ ] Condition sortie si aucun nouveau gap
- [ ] Tests boucle avec gaps répétés

### Phase 4 : Handler Séances Sautées (2h)
- [ ] Créer _show_skipped_sessions()
- [ ] Créer generate_skipped_session_entry()
- [ ] Gérer cas réconciliation None mais skipped présent

### Phase 5 : Tests Intégration (2h)
- [ ] Test scenario trainr mode
- [ ] Test scenario trains mode
- [ ] Test scenario mixte (exécutées + repos + sautées)

**Effort total estimé** : 9 heures

---

## ✅ Validation

### Critères de Succès

1. **Scenario trainr** :
   - ✅ Détecte séances sautées
   - ✅ User traite en batch
   - ✅ Génère markdowns
   - ✅ Insère dans workouts-history.md
   - ✅ Commit git réussi
   - ✅ Retourne à détection → **Aucun gap détecté** (sessions marquées documentées)
   - ✅ Sort de la boucle proprement

2. **Scenario trains** :
   - ✅ Détecte repos + sautées
   - ✅ User traite repos
   - ✅ Génère markdown repos
   - ✅ Insère dans workouts-history.md
   - ✅ Commit git réussi
   - ✅ Retourne à détection → **Repos disparu, sautée reste** (filtrage OK)
   - ✅ User traite sautée
   - ✅ Retourne à détection → **Aucun gap détecté**
   - ✅ Sort de la boucle proprement

3. **Scenario mixte** :
   - ✅ Détecte 2 exécutées + 1 repos + 1 sautée
   - ✅ User traite exécutée #1 → Retour détection → 1 exécutée + 1 repos + 1 sautée
   - ✅ User traite repos → Retour détection → 1 exécutée + 1 sautée
   - ✅ User traite sautée → Retour détection → 1 exécutée
   - ✅ User traite exécutée #2 → Retour détection → **Aucun gap**
   - ✅ Sort de la boucle

---

## 📎 Références

- **Fichier principal** : `cyclisme_training_logs/workflow_coach.py`
- **Logs analysés** :
  - `logs/Cyclisme-training-logs_20251225_074440.txt` (trainr mode)
  - `logs/Tree-Cyclisme-training-logs_20251225_073148.txt` (trains mode)
- **WorkflowState** : `cyclisme_training_logs/workflow_state.py`
- **Templates** : `cyclisme_training_logs/templates/`

---

## 📊 Impact Business

**Sans fix** :
- ❌ Workflow trainr inutilisable (boucle infinie)
- ❌ Workflow trains inutilisable (boucle infinie)
- ❌ User doit Ctrl+C pour sortir (expérience dégradée)
- ❌ Documentation incomplète (repos/sautées non traitables)

**Avec fix** :
- ✅ Workflows trainr/trains utilisables normalement
- ✅ Toutes sessions documentables (exécutées + repos + annulations + sautées)
- ✅ Sortie propre de la boucle après traitement complet
- ✅ Expérience utilisateur fluide

---

**Priorité recommandée** : 🔴 P0 CRITIQUE
**À implémenter** : Phase 3 immédiat
