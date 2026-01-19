# Utiliser le feedback athlète dans Intervals.icu

## 📝 Vue d'ensemble

Le système d'analyse AI utilise automatiquement **3 champs** Intervals.icu comme feedback athlète:
1. **"How did it feel?"** (échelle 1-4) - Ressenti général rapide
2. **Description activité** (texte libre) - Notes spécifiques à la séance
3. **Comments wellness** (texte libre) - Notes générales du jour

Plus besoin de répondre aux questions interactives!

## ✅ Avantages

- **Simple**: Saisir votre feedback directement dans Intervals.icu après la séance
- **Flexible**: Écrivez ce qui vous semble pertinent, format libre
- **Automatique**: Le système récupère automatiquement le feedback
- **Persistant**: Votre feedback est stocké avec l'activité dans Intervals.icu

## 🚴 Comment ça marche

### 1. Après votre séance - 3 champs de feedback

Dans Intervals.icu, vous avez **3 endroits** pour donner votre feedback:

#### A. "How did it feel?" (Ressenti général) ⭐ **NOUVEAU**
Échelle rapide 1-4:
- 😣 **1** = Difficile (mauvaise séance, souffrance)
- 😐 **2** = Moyen (OK mais pas top)
- 🙂 **3** = Bon (séance solide)
- 😊 **4** = Excellent (super séance!)

**Avantage**: 1 clic, 1 seconde!

#### B. Description activité (Notes spécifiques à la séance)
Texte libre dans le champ **"Description"** de l'activité:

**Exemple de feedback efficace**:
```
Bonne séance malgré la fatigue initiale.
Les intervalles Sweet-Spot ont été difficiles surtout les 2 derniers.
Jambes lourdes en début mais mieux après 20min.
Cadence un peu basse, besoin de travailler ça.
```

**Ce qui est utile de mentionner**:
- 🦵 Sensations physiques pendant la séance (jambes lourdes, frais, courbatures)
- 🎯 Difficultés rencontrées (intervalles durs, maintien puissance, cadence)
- ✅ Points positifs (bonne exécution, progrès ressenti)
- 🌡️ Conditions spécifiques (température, vent, équipement)
- 🔧 Problèmes techniques (déconnexions, capteurs)

#### C. Comments wellness (Notes générales du jour) ⭐ **NOUVEAU**
Texte libre dans le champ **"Comments"** du wellness (écran principal):

**Exemple de notes wellness**:
```
Bonne forme aujourd'hui, fait une sieste d'une heure avant la séance.
Me suis senti en bien meilleure forme après la séance.
```

**Ce qui est utile de mentionner**:
- 💪 Forme générale du jour (fatigue, fraîcheur, moral)
- 😴 Qualité du sommeil (profondeur, réveil)
- 🍔 Nutrition du jour (petit-déj, hydratation)
- 💊 Autres facteurs (stress, travail, famille)
- 🛌 Récupération (sieste, repos actif)

### 2. Le système fait le reste

À **21h30** chaque soir:
1. ✅ Le `daily-sync` détecte votre nouvelle activité
2. ✅ Récupère automatiquement vos 3 feedbacks (feel + description + wellness)
3. ✅ Génère l'analyse AI en intégrant votre ressenti
4. ✅ Insère l'analyse dans `workouts-history.md`
5. ✅ Vous envoie l'email avec l'analyse complète

### 3. L'analyse AI utilise votre feedback

Le prompt AI inclut explicitement **les 3 champs**:
```markdown
### Feedback Athlète (saisi dans Intervals.icu)

**Ressenti général** : 😐 Moyen (2/4)

**Notes activité** :
Bonne séance malgré la fatigue initiale.
Les intervalles Sweet-Spot ont été difficiles surtout les 2 derniers...

**Notes wellness** :
Bonne forme aujourd'hui, fait une sieste d'une heure avant la séance.
Me suis senti en bien meilleure forme après la séance.
```

Et les instructions AI mentionnent:
> **Intégrer le feedback athlète** s'il est présent - ressenti général (1-4), notes activité, notes wellness, observations subjectives

## 📊 Comparaison avec l'ancien système

| Ancien (questions interactives) | Nouveau (3 champs Intervals.icu) |
|----------------------------------|-----------------------------------|
| Répondre à 5-6 questions         | 1 clic + 2 champs texte libres   |
| Format structuré imposé          | Format libre, naturel             |
| Feedback perdu si pas sauvé      | Toujours dans Intervals.icu       |
| Saisie lors du workflow          | Saisie quand vous voulez          |

## 🔄 Workflow recommandé

```
1. Finir la séance
2. Synchroniser avec Intervals.icu (Zwift, Garmin, etc.)
3. Ouvrir l'activité dans Intervals.icu
4. Cliquer sur "How did it feel?" (1-4)
5. Saisir notes spécifiques dans "Description" de l'activité
6. Saisir notes générales dans "Comments" du wellness (écran principal)
7. Saisir autres wellness si besoin (sommeil, poids, etc.)
8. Attendre 21h30 → Email avec analyse complète!
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
