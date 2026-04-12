# Protocole de saisie des courses dans Intervals.icu

## Objectif

Permettre au planificateur hebdomadaire d'enrichir automatiquement les courses
avec les donnees du circuit (distance, D+, profil, tactique) pour generer
un planning adapte aux jours de competition.

## Comment saisir une course

### 1. Creer un evenement dans Intervals.icu

- Aller dans le **Calendrier**
- Cliquer sur le jour de la course
- Choisir **Event** (pas Workout)
- Categorie : **RACE** (important, pas WORKOUT ni NOTE)

### 2. Nommer correctement

Le nom doit inclure le **nom du circuit** pour permettre le matching automatique.

**Bons exemples :**
- `ZRL - The Classic`
- `ZRL Round 4 - Hell of the North`
- `Tiny Race - Spirit Forest`
- `Tiny Race Downtown Dolphin`

**Mauvais exemples :**
- `Course du mardi` (aucune info sur le circuit)
- `ZRL` (pas assez precis)
- `Entrainement race` (ce n'est pas une course)

### 3. Date et heure

- Mettre la **date exacte** de la course
- Mettre l'**heure de depart** reelle (important pour la planification J-1/J+1)

### 4. Description (optionnel mais recommande)

Ajouter dans la description :
- Categorie (C, D, etc.)
- Nombre de tours si connu
- Objectif personnel (ex: "viser top 10", "rester dans le peloton")

**Exemple de description :**
```
Cat D - 4 tours
Objectif : rester dans le groupe principal, sprinter sur les segments
Format Points Race : points aux sprints intermediaires + arrivee
```

## Circuits connus

Le systeme reconnait automatiquement ces circuits (et leurs variantes) :

| Circuit | Monde | Profil | Distance/tour |
|---------|-------|--------|---------------|
| The Classic | Watopia | Plat | 4.87 km |
| Hell of the North | Makuri Islands | Valonne | 8.6 km |
| Croissant | France | Plat | 10.1 km |
| Double Span Spin | Watopia | Valonne | 8.12 km |
| Spirit Forest | Makuri Islands | Valonne | 6.4 km |
| Downtown Dolphin | Crit City | Plat | 1.25 km |

Pour ajouter un circuit inconnu a la base, contacter l'administrateur.

## Impact sur la planification

Quand une course est correctement saisie, le planificateur :
- Adapte la charge J-1 (repos ou activation legere)
- Prevoit la recuperation J+1
- Evite la pre-fatigue sur les 48h precedentes
- Ajuste les zones d'intensite selon le profil du circuit
