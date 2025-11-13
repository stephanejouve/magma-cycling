# 🚴 Training Logs - Cyclisme

> Suivi structuré d'entraînement cycliste : FTP 220W → 260W+  
> Athlète : Stéphane (54 ans, né 18/08/1971)  
> Coaching assisté par Claude (Anthropic)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/yourusername/cyclisme-training-logs/graphs/commit-activity)

---

## 📋 Table des Matières

- [À Propos](#à-propos)
- [Structure du Projet](#structure-du-projet)
- [Logs Principaux](#logs-principaux)
- [Bilans Hebdomadaires](#bilans-hebdomadaires)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Workflow](#workflow)
- [Métriques Actuelles](#métriques-actuelles)

---

## 📖 À Propos

Ce dépôt documente un programme d'entraînement structuré pour développer la FTP (Functional Threshold Power) avec un suivi data-driven rigoureux.

### Objectifs
- **FTP actuelle** : 220W (2.62 W/kg)
- **FTP cible** : 260W+ (3.10 W/kg)
- **Stratégie** : Indoor-only 2-3 mois puis retour progressif outdoor

### Caractéristiques Athlète
- 🫀 FC repos : 40 bpm (capacités récupération exceptionnelles)
- ⚠️ Facteur limitant : Dette sommeil (5h33 vs cible 7h+)
- 🎯 Défi : Discipline intensité terrain (surcharge systématique)

---

## 📁 Structure du Projet

```
cyclisme-training-logs/
├── logs/                          # 4 logs continus (mis à jour quotidiennement)
│   ├── workouts-history.md        # Chronologie complète séances
│   ├── metrics-evolution.md       # Suivi longitudinal métriques
│   ├── training-learnings.md      # Enseignements cumulés
│   └── workout-templates.md       # Catalogue formats validés
│
├── bilans_hebdo/                  # Bilans hebdomadaires (6 fichiers/semaine)
│   ├── s067/
│   │   ├── workout_history_s067.md
│   │   ├── metrics_evolution_s067.md
│   │   ├── training_learnings_s067.md
│   │   ├── protocol_adaptations_s067.md
│   │   ├── transition_s067_s068.md
│   │   └── bilan_final_s067.md
│   └── s068/
│       └── ...
│
├── references/                    # Documentation système
│   ├── project_prompt_v2.md       # Prompt système Claude
│   ├── guide_utilisation.md       # Guide d'utilisation
│   └── templates_initialisation.md # Templates logs
│
├── scripts/                       # Scripts d'automatisation
│   ├── commit_semaine.sh          # Commit bilan hebdomadaire
│   ├── backup.sh                  # Backup local
│   └── stats.py                   # Génération statistiques
│
└── .github/
    └── workflows/
        └── weekly-backup.yml      # CI/CD (optionnel)
```

---

## 📊 Logs Principaux

### 1. [workouts-history.md](logs/workouts-history.md)
Chronologie complète de toutes les séances avec :
- Fichiers .zwo associés
- Métriques pré/post (CTL/ATL/TSB)
- Exécution réelle (IF, TSS, RPE)
- Découvertes techniques

### 2. [metrics-evolution.md](logs/metrics-evolution.md)
Suivi longitudinal :
- Évolution FTP
- Progression CTL/ATL/TSB quotidienne
- Poids, sommeil, asymétrie pédalage
- Validations techniques

### 3. [training-learnings.md](logs/training-learnings.md)
Enseignements terrain :
- Intensités optimales découvertes
- Patterns physiologiques
- Protocoles validés/invalidés
- Points de surveillance

### 4. [workout-templates.md](logs/workout-templates.md)
Catalogue formats validés :
- Sweet-Spot, Seuil, VO2, Endurance
- Contexte utilisation, TSB recommandé
- Versioning modifications >20%

---

## 📅 Bilans Hebdomadaires

Chaque semaine génère **6 fichiers markdown** :

1. **workout_history** : Résumé semaine
2. **metrics_evolution** : Métriques période
3. **training_learnings** : Découvertes
4. **protocol_adaptations** : Ajustements
5. **transition** : Planification suivante
6. **bilan_final** : Synthèse globale

📂 Voir [bilans_hebdo/](bilans_hebdo/) pour archives complètes

---

## 🛠️ Installation

### Prérequis
- Git
- Python 3.8+ (pour scripts stats, optionnel)
- Éditeur markdown (VS Code recommandé)

### Clone
```bash
git clone https://github.com/yourusername/cyclisme-training-logs.git
cd cyclisme-training-logs
```

### Configuration
```bash
# Personnaliser les infos
cp .env.example .env
nano .env
```

---

## 🚀 Utilisation

### Après Chaque Séance
```bash
# Éditer les logs
vim logs/workouts-history.md
vim logs/metrics-evolution.md

# Commit rapide
git add logs/
git commit -m "S067-03: Sweet-Spot 3x8min @ 90% FTP"
git push
```

### Fin de Semaine
```bash
# Générer les 6 bilans avec Claude
# (Upload logs → Claude génère → Download bilans)

# Organiser les bilans
mkdir -p bilans_hebdo/s067
mv bilan_*.md bilans_hebdo/s067/

# Commit semaine complète
./scripts/commit_semaine.sh 067
```

---

## 🔄 Workflow

### Quotidien
1. **Pré-séance** : Vérifier TSB, sommeil, fatigue
2. **Exécution** : Réaliser séance (Zwift/TrainingPeaks Virtual)
3. **Post-séance** : Mettre à jour logs (workouts-history + metrics-evolution)
4. **Commit** : `git commit -m "SXXX-JJ: Type séance"`

### Hebdomadaire  
1. **Analyse** : Uploader les 4 logs vers Claude
2. **Génération** : Claude produit les 6 fichiers hebdomadaires
3. **Archivage** : Ranger bilans dans `bilans_hebdo/sXXX/`
4. **Planning** : Valider templates semaine suivante
5. **Push** : `./scripts/commit_semaine.sh XXX`

### Mensuel
1. Réviser templates selon apprentissages
2. Ajuster protocoles validés
3. Tag release : `git tag v1.0-2025-11`

---

## 📈 Métriques Actuelles

| Métrique | Valeur | Cible | Progression |
|----------|--------|-------|-------------|
| **FTP** | 220W | 260W+ | 🟡 84.6% |
| **W/kg** | 2.62 | 3.10+ | 🟡 84.5% |
| **Poids** | 83.8kg | 84kg ± | 🟢 Stable |
| **CTL** | 56 | 65-70 | 🟡 86.2% |
| **TSB** | Variable | -10 à +10 | 🟢 Contrôlé |
| **Sommeil** | 5h33 | 7h+ | 🔴 79.3% |

*Dernière mise à jour : S067 (Novembre 2025)*

---

## 🎯 Enseignements Clés

### ✅ Validations
- Sweet-Spot 88-90% FTP consolidé
- Checklist VO2 5 critères opérationnelle
- Découplage <7.5% systématique
- Capacité terrain >> indoor (163 TSS outdoor vs équivalent indoor)

### 🔄 En Cours
- Stratégie indoor-only (discipline intensité)
- Progression Sweet-Spot 88% → 90%+
- Amélioration hygiène sommeil (facteur limitant)

### ⚠️ Points Surveillance
- Dette sommeil (impact VO2 validé)
- Asymétrie pédalage (effort-dépendant, monitoring)
- Retour terrain progressif (après validation discipline indoor)

---

## 📚 Documentation

### Références Complètes
- [Prompt Système Claude](references/project_prompt_v2.md)
- [Guide d'Utilisation](references/guide_utilisation.md)
- [Templates Initialisation](references/templates_initialisation.md)

### Protocoles Critiques
- **VO2 Max** : TSB +5 minimum, sommeil >7h, 48h sans intensité >85% FTP
- **Hydratation** : Fréquence doublée >88% FTP
- **Nutrition Terrain** : 45g glucides/h max, 15min avant montées >5%

### Plateformes Utilisées
- **Analyse** : Intervals.icu, Riducks
- **Exécution** : Zwift, TrainingPeaks Virtual
- **Capteurs** : Wahoo ELEMNT ROAM V2, Withings
- **Terrain** : RideWithGPS (waypoints nutrition)

---

## 🤝 Contribution

Ce projet est personnel mais la méthodologie est ouverte :

- 💡 Suggestions de protocoles → Issues
- 🐛 Erreurs documentation → Pull Requests
- 📊 Scripts stats/analyse → Pull Requests bienvenues

---

## 📝 License

MIT License - Libre utilisation et adaptation de la méthodologie.

---

## 🙏 Remerciements

- **Claude (Anthropic)** : Assistant coach, analyse et documentation
- **Intervals.icu** : Plateforme d'analyse performance
- **Communauté Zwift** : Motivation et templates workouts

---

**Dernière synchronisation** : 13 novembre 2025  
**Semaine actuelle** : S067  
**Version documentation** : 2.0.1
