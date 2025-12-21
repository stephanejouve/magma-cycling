# Quick Reference - Cyclisme Training Logs

## 🔄 Workflow Quotidien (Post-Séance)
train                           # Standard: feedback + analyse + commit
trains --week-id S073           # Avec asservissement planning (Mer/Ven)
train-fast                      # Rapide: analyse uniquement (debug)
trainr --week-id S073           # Réconciliation: rattrapage batch

## 📅 Workflow Hebdomadaire (Lundi Matin)
wa --week-id S072 --start-date 2025-12-16       # 1. Analyser semaine passée
wp --week-id S073 --start-date 2025-12-23       # 2. Planifier semaine courante
wu --week-id S073 --start-date 2025-12-23       # 3. Uploader workouts

## 🛠️ Scripts Individuels (Usage Avancé)
prep                            # Préparer analyse
feedback                        # Collecter feedback uniquement
stats                           # Statistiques
sync                            # Sync Intervals.icu
check                           # Vérifier planning

## Navigation
cdtrain  # cd projet
logs     # Voir logs
reports  # Voir rapports

## Post-Redémarrage
✅ Tout fonctionne automatiquement !
