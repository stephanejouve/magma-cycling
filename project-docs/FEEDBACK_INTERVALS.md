# Utiliser le feedback athlète dans Intervals.icu

## 📝 Vue d'ensemble

Le système d'analyse AI utilise automatiquement le champ **description** de vos activités Intervals.icu comme feedback athlète. Plus besoin de répondre aux questions interactives!

## ✅ Avantages

- **Simple**: Saisir votre feedback directement dans Intervals.icu après la séance
- **Flexible**: Écrivez ce qui vous semble pertinent, format libre
- **Automatique**: Le système récupère automatiquement le feedback
- **Persistant**: Votre feedback est stocké avec l'activité dans Intervals.icu

## 🚴 Comment ça marche

### 1. Après votre séance

Dans Intervals.icu, ouvrez votre activité et ajoutez votre feedback dans le champ **Description**:

**Exemple de feedback efficace**:
```
Bonne séance malgré la fatigue initiale.
Les intervalles Sweet-Spot ont été difficiles surtout les 2 derniers.
Jambes lourdes en début mais mieux après 20min.
Cadence un peu basse, besoin de travailler ça.
Sommeil correct cette nuit (7h).
```

**Ce qui est utile de mentionner**:
- 💪 Ressenti général (forme, fatigue, motivation)
- 🦵 Sensations physiques (jambes lourdes, frais, courbatures)
- 🎯 Difficultés rencontrées (intervalles durs, maintien puissance, cadence)
- ✅ Points positifs (bonne exécution, progrès ressenti)
- 😴 Sommeil de la nuit précédente si pas saisi dans wellness
- 🍔 Nutrition pré-séance si pertinent
- 🌡️ Conditions (température, vent, équipement)

### 2. Le système fait le reste

À **21h30** chaque soir:
1. ✅ Le `daily-sync` détecte votre nouvelle activité
2. ✅ Récupère automatiquement votre feedback de la description
3. ✅ Génère l'analyse AI en intégrant votre ressenti
4. ✅ Insère l'analyse dans `workouts-history.md`
5. ✅ Vous envoie l'email avec l'analyse complète

### 3. L'analyse AI utilise votre feedback

Le prompt AI inclut explicitement:
```markdown
### Feedback Athlète (saisi dans Intervals.icu)
[Votre description Intervals.icu]
```

Et les instructions AI mentionnent:
> **Intégrer le feedback athlète** s'il est présent - ressenti, difficultés, observations subjectives

## 📊 Comparaison avec l'ancien système

| Ancien (questions interactives) | Nouveau (description Intervals.icu) |
|----------------------------------|--------------------------------------|
| Répondre à 5-6 questions         | Écrire librement dans Intervals.icu |
| Format structuré imposé          | Format libre, naturel                |
| Feedback perdu si pas sauvé      | Toujours dans Intervals.icu          |
| Saisie lors du workflow          | Saisie quand vous voulez             |

## 🔄 Workflow recommandé

```
1. Finir la séance
2. Synchroniser avec Intervals.icu (Zwift, Garmin, etc.)
3. Ouvrir l'activité dans Intervals.icu
4. Saisir votre feedback dans "Description"
5. Saisir wellness si besoin (sommeil, poids, etc.)
6. Attendre 21h30 → Email avec analyse complète!
```

## 💡 Exemples de feedback

### Séance facile d'endurance
```
Séance récup facile, jambes fraîches.
Bon découplage ressenti.
Cadence fluide autour de 90rpm.
```

### Séance intense avec difficultés
```
Intervalle VO2max très durs.
Impossible de maintenir la cible sur le 4ème interval (-15W).
Jambes qui brûlent, FC qui monte vite.
Peut-être encore fatigué de la séance de mardi.
Besoin de repos supplémentaire.
```

### Séance avec observations techniques
```
Travail Sweet-Spot bien réalisé.
Cadence un peu basse (82rpm) sur les intervalles,
à améliorer pour être plus efficient.
Bonne gestion de l'effort, découplage minimal.
```

## ⚠️ Important

- **Saisissez avant 21h30**: Pour que le feedback soit inclus dans l'analyse du soir
- **Si oublié**: Vous pouvez éditer la description plus tard et relancer `workflow-coach` manuellement si nécessaire
- **Format libre**: Pas de structure imposée, écrivez naturellement
- **Optionnel**: Si pas de feedback, l'analyse est générée quand même (basée uniquement sur les métriques)

## 🔧 Ancien système (toujours disponible)

Le système de questions interactives via `collect-feedback` est toujours disponible si vous préférez:

```bash
poetry run collect-feedback
poetry run workflow-coach
```

Mais le système automatique via description Intervals.icu est plus simple et intégré!

## 📈 Résultat

Votre email quotidien contient maintenant:
- 📊 Métriques objectives (TSS, puissance, FC, découplage)
- 💭 Votre ressenti subjectif (feedback de la description)
- 🤖 Analyse AI qui croise les deux perspectives
- 💡 Recommandations personnalisées basées sur données + ressenti

**Exemple d'analyse enrichie par le feedback**:
> Les intervalles Sweet-Spot ont été globalement bien exécutés (IF 0.88) malgré
> la fatigue ressentie en début de séance. Votre observation sur les jambes lourdes
> initialement est cohérente avec le TSB légèrement négatif (-8). La progression
> durant la séance (découplage 3.2%) confirme que l'échauffement a bien fonctionné...

---

*Guide créé le 19/01/2026*
