# Shift Sessions - Alias Shell Pratiques

Suggestions d'alias shell pour faciliter l'utilisation de `shift-sessions`.

## Installation

Ajouter ces alias à votre `~/.zshrc` ou `~/.bashrc`:

```bash
# === Session Shifting Aliases ===

# Shift de base (décaler sessions)
alias shift-sessions='cd ~/cyclisme-training-logs && poetry run shift-sessions'

# Swap (échanger deux jours)
alias swap-days='cd ~/cyclisme-training-logs && poetry run shift-sessions --swap-days'
alias swap-sessions='cd ~/cyclisme-training-logs && poetry run shift-sessions --swap'

# Opérations courantes
alias insert-rest='cd ~/cyclisme-training-logs && poetry run shift-sessions --insert-rest-day'
alias remove-session='cd ~/cyclisme-training-logs && poetry run shift-sessions --remove-session'

# Avec sync automatique
alias shift-sync='cd ~/cyclisme-training-logs && poetry run shift-sessions --sync'
alias swap-days-sync='shift-sync --swap-days'
alias swap-sessions-sync='shift-sync --swap'

# Preview (dry-run)
alias shift-preview='cd ~/cyclisme-training-logs && poetry run shift-sessions --dry-run'
```

## Exemples d'Utilisation

### Décaler des sessions

```bash
# Décaler toutes les sessions à partir de jeudi (+1 jour)
shift-sessions --week-id S081 --from-day 4 --shift-days 1

# Avec renumérotation et sync
shift-sync --week-id S081 --from-day 4 --shift-days 1 --renumber

# Preview avant de faire le changement
shift-preview --week-id S081 --from-day 4 --shift-days 1
```

### Échanger/Inverser deux jours

```bash
# Échanger jeudi et vendredi (jours 4 et 5)
swap-days S081 4 5

# Échanger avec sync Intervals.icu
swap-days-sync S081 4 5

# Échanger deux sessions spécifiques
swap-sessions S081 S081-04 S081-05
swap-sessions-sync S081 S081-04 S081-05
```

### Insérer un jour de repos

```bash
# Insérer repos jeudi et décaler le reste
insert-rest S081 4

# Note: décale automatiquement les sessions suivantes
```

### Supprimer une session

```bash
# Supprimer une session du planning
remove-session S081 S081-07
```

## Workflows Typiques

### Scénario 1: Fatigue → Décaler tout d'un jour

```bash
# 1. Preview d'abord
shift-preview --week-id S081 --from-day 4 --shift-days 1 --renumber

# 2. Appliquer les changements
shift-sessions --week-id S081 --from-day 4 --shift-days 1 --renumber

# 3. Sync avec Intervals.icu
shift-sync --week-id S081 --from-day 4 --shift-days 1 --renumber
```

### Scénario 2: Inverser deux séances (météo, logistique)

```bash
# Échanger jeudi (intervalles difficiles) et vendredi (endurance)
swap-days-sync S081 4 5

# Vérifie: S081-04 est maintenant vendredi, S081-05 est jeudi
```

### Scénario 3: Insérer repos et réorganiser

```bash
# Besoin de repos mercredi → insérer et décaler le reste
insert-rest S081 3

# Automatiquement:
# - Crée S081-03 (repos) le mercredi
# - Décale S081-03 original → jeudi (devient S081-04)
# - Décale S081-04 original → vendredi (devient S081-05)
# - etc.
```

## Flags Utiles

```bash
--week-id WEEK_ID          # Semaine cible (ex: S081)
--from-day DAY             # Jour de début (1=lundi, 7=dimanche)
--shift-days N             # Nombre de jours à décaler
--renumber                 # Renumeroter session_id = jour
--swap-days DAY1 DAY2      # Échanger deux jours
--swap S1 S2               # Échanger deux sessions par ID
--insert-rest-day DAY      # Insérer repos et décaler
--remove-session SID       # Supprimer une session
--sync                     # Synchroniser avec Intervals.icu
--dry-run                  # Preview sans sauvegarder
```

## Sécurités Intégrées

✅ **Ne touche PAS aux sessions complétées** (`status=completed`)
✅ **Valide les limites de semaine** (lundi-dimanche)
✅ **Validation Pydantic** des modifications
✅ **Sync optionnel** - contrôle quand synchroniser
✅ **Dry-run** - preview avant application

## Notes Importantes

1. **Sessions complétées**: L'outil refuse de shifter/swapper des sessions avec `status=completed`
2. **Limites de semaine**: Les sessions ne peuvent pas déborder en dehors de lundi-dimanche
3. **Sync**: Seules les sessions avec `intervals_id` seront synchronisées
4. **Renumbering**: `--renumber` ajuste les `session_id` pour matcher les jours (S081-04 = jeudi)

## Dépannage

### "Session already completed"
```
❌ Cannot swap S081-01: session already completed!
```
**Solution**: Ne pas swapper/shifter une session déjà réalisée. Modifier manuellement le planning ou créer une nouvelle session.

### "No sessions found on or after day X"
```
ValueError: No sessions found on or after day 5
```
**Solution**: Aucune session à shifter après ce jour. Normal si vous shiftez à la fin de la semaine.

### Sync échoue
```
⚠️  Warning: Sync with Intervals.icu failed: ...
```
**Solution**:
- Vérifier les credentials (`VITE_INTERVALS_API_KEY`)
- Vérifier que la session a un `intervals_id`
- Le fichier JSON local est quand même sauvegardé

## Exemples Réels

### Cas d'usage: Aujourd'hui S081-04 → Repos

```bash
# Situation: Jeudi épuisé, besoin de repos
# Solution 1: Canceller et décaler tout

# 1. Canceller jeudi
cancel-session-sync --week-id S081 --session S081-04 --reason "Fatigue"

# 2. Décaler vendredi-dimanche d'un jour (impossible, déborde)
# → Pas possible, S081-07 sortirait de la semaine

# Solution 2: Remplacer S081-04 par repos, garder le reste
insert-rest S081 4
remove-session S081 S081-07  # Supprimer dimanche pour garder 7 jours

# Solution 3 (retenue): Laisser jeudi cancelled, tout décaler sans déborder
# → Manuel car complexe
```

Ce qu'on a fait aujourd'hui:
```bash
# Manuel: changé S081-04 de cancelled → rest_day
# Décalé manuellement S081-05, S081-06, supprimé S081-07
# Renommé pour cohérence (Session5 = vendredi, etc.)
```

Avec l'outil maintenant:
```bash
# Option 1: Shift simple (si on veut décaler tout le reste)
shift-sessions --week-id S081 --from-day 5 --shift-days 1 --renumber

# Option 2: Créer repos + remove dernière session
insert-rest S081 4
remove-session S081 S081-07
```
