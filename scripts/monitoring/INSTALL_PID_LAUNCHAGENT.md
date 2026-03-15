# Installation LaunchAgent PID Evaluation

## Vue d'ensemble

Ce LaunchAgent optionnel exécute l'évaluation PID quotidienne automatiquement chaque jour à 23:00.

**Important**: Ce LaunchAgent est **optionnel**. L'évaluation PID est déjà intégrée dans le workflow `end-of-week`, donc elle sera exécutée automatiquement en fin de semaine. Ce LaunchAgent permet d'avoir une collecte quotidienne supplémentaire pour un suivi plus fin.

## Que fait ce LaunchAgent ?

- **Quand**: Tous les jours à 23:00 (1h après le check d'adhérence à 22:00)
- **Quoi**: Exécute `pid-daily-evaluation --days-back 7`
- **Données collectées**:
  - Adhérence aux entraînements (depuis workout_adherence.jsonl)
  - Découplage cardiovasculaire (depuis workout_history hebdomadaires)
  - Completion TSS (depuis Intervals.icu API)
- **Résultats**:
  - Log des évaluations: `~/data/monitoring/pid_evaluation.jsonl`
  - Intelligence mise à jour: `~/data/intelligence.json`
  - Logs système: `~/data/monitoring/pid_evaluation.{stdout,stderr}.log`

## Installation

### 1. Copier le fichier plist

```bash
cp examples/launchagents/com.cyclisme.pid_evaluation.plist ~/Library/LaunchAgents/
```

### 2. Charger le LaunchAgent

```bash
launchctl load ~/Library/LaunchAgents/com.cyclisme.pid_evaluation.plist
```

### 3. Vérifier le statut

```bash
launchctl list | grep com.cyclisme.pid_evaluation
```

Vous devriez voir une ligne avec le PID et le statut.

## Test manuel

Pour tester immédiatement sans attendre 23:00:

```bash
launchctl start com.cyclisme.pid_evaluation
```

Puis vérifiez les logs:

```bash
tail -50 ~/data/monitoring/pid_evaluation.stdout.log
```

## Vérifier les évaluations

```bash
# Voir les dernières évaluations
cat ~/data/monitoring/pid_evaluation.jsonl | tail -5 | python3 -m json.tool

# Voir les learnings dans l'intelligence
cat ~/data/intelligence.json | python3 -m json.tool
```

## Désinstallation

Si vous ne souhaitez plus l'évaluation quotidienne automatique:

```bash
# Décharger le LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.cyclisme.pid_evaluation.plist

# Supprimer le fichier (optionnel)
rm ~/Library/LaunchAgents/com.cyclisme.pid_evaluation.plist
```

## Fréquence recommandée

- **Hebdomadaire uniquement** (via end-of-week): Suffisant pour la plupart des cas
- **Quotidien** (avec ce LaunchAgent): Utile pour un suivi plus granulaire et une accumulation plus rapide de learnings

## Troubleshooting

### Le LaunchAgent ne se lance pas

1. Vérifier les permissions du script wrapper:
   ```bash
   chmod +x scripts/monitoring/run_pid_evaluation.sh
   ```

2. Vérifier les logs d'erreur:
   ```bash
   tail -50 ~/data/monitoring/pid_evaluation.stderr.log
   ```

3. Vérifier que poetry est installé:
   ```bash
   which poetry
   ```

### Logs système launchd

```bash
log stream --predicate 'subsystem == "com.apple.launchd"' --level info | grep pid_evaluation
```

## Intégration avec end-of-week

Le workflow `end-of-week` inclut déjà l'évaluation PID (Step 1b). Ce LaunchAgent quotidien est donc complémentaire, pas nécessaire.

Avantages d'avoir les deux:
- **end-of-week**: Évaluation en contexte de transition hebdomadaire
- **LaunchAgent quotidien**: Collecte continue, learnings accumulés plus rapidement
