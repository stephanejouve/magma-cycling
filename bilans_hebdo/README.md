# Bilans Hebdomadaires

Ce répertoire contient les bilans hebdomadaires archivés, générés à la fin de chaque semaine.

## Structure

Chaque semaine a son propre sous-répertoire :

```
bilans_hebdo/
├── s067/
│   ├── workout_history_s067.md
│   ├── metrics_evolution_s067.md
│   ├── training_learnings_s067.md
│   ├── protocol_adaptations_s067.md
│   ├── transition_s067_s068.md
│   └── bilan_final_s067.md
├── s068/
│   └── ... (6 fichiers)
└── s069/
    └── ... (6 fichiers)
```

## Génération des Bilans

Les bilans sont générés via Claude en fin de semaine :

1. **Upload** des 4 logs continus vers Claude
2. **Demande** : "Génère les 6 fichiers hebdomadaires pour S067"
3. **Download** des 6 fichiers markdown produits
4. **Archivage** dans `bilans_hebdo/s067/`
5. **Commit** avec le script : `./scripts/commit_semaine.sh 067`

## Contenu des 6 Fichiers

1. **workout_history_sXXX.md** : Résumé chronologique de la semaine
2. **metrics_evolution_sXXX.md** : Métriques et évolution (CTL/ATL/TSB)
3. **training_learnings_sXXX.md** : Découvertes et enseignements
4. **protocol_adaptations_sXXX.md** : Ajustements protocoles
5. **transition_sXXX_sXXX.md** : Recommandations semaine suivante
6. **bilan_final_sXXX.md** : Synthèse globale de la semaine

---

_Les bilans seront ajoutés au fur et à mesure des semaines_
