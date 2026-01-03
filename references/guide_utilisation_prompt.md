# Guide d'Utilisation du Nouveau Prompt Système

## Vue d'Ensemble

Le nouveau prompt système (v2.0) a été restructuré pour refléter l'évolution du projet et clarifier les processus de documentation. Il intègre maintenant de manière cohérente :

1. **Les 4 fichiers logs principaux** (documentation continue)
2. **Les 6 fichiers hebdomadaires** (bilans de fin de semaine)
3. **Les protocoles validés** (enseignements terrain)
4. **Les règles de communication** (factuel, concis, markdown uniquement)

## Comment Utiliser ce Prompt

### Option 1 : Custom Instructions du Projet
1. Dans votre projet Claude, allez dans les paramètres
2. Copiez l'intégralité du fichier `project_prompt_v2.md`
3. Collez-le dans les "Custom Instructions" du projet
4. Sauvegardez

### Option 2 : Référence en Début de Session
Si les custom instructions ne sont pas disponibles :
1. Au début de chaque nouvelle session avec Claude
2. Partagez le fichier `project_prompt_v2.md`
3. Demandez : "Merci de suivre ces instructions pour cette session"

## Changements Principaux

### Structure Clarifiée

**AVANT** : Documentation dispersée dans multiples fichiers projet
**MAINTENANT** : Prompt unique consolidé avec hiérarchie claire :
- Rôle et contexte
- 4 logs principaux (continuité)
- 6 fichiers hebdomadaires (bilans)
- Protocoles et règles

### Documentation Duale

Le système maintient maintenant **deux niveaux** de documentation :

#### Niveau 1 : Logs Continus (4 fichiers)
Mis à jour **au fil de l'eau**, séance après séance :
- `workouts-history.md` → Chronologie complète
- `metrics-evolution.md` → Suivi longitudinal
- `training-learnings.md` → Enseignements cumulés
- `workout-templates.md` → Catalogue évolutif

#### Niveau 2 : Bilans Hebdomadaires (6 fichiers)
Générés **en fin de semaine**, numérotés sXXX :
1. `workout_history_sXXX.md` → Résumé semaine
2. `metrics_evolution_sXXX.md` → Métriques période
3. `training_learnings_sXXX.md` → Découvertes semaine
4. `protocol_adaptations_sXXX.md` → Ajustements
5. `transition_sXXX_sXXX.md` → Vers semaine suivante
6. `bilan_final_sXXX.md` → Synthèse globale

### Protocoles Intégrés

Le prompt intègre maintenant directement :
- ✅ Checklist VO2 (5 critères)
- ✅ Protocoles hydratation
- ✅ Nutrition terrain (waypoints)
- ✅ Règles discipline intensité
- ✅ Enseignements clés établis

### Communication Optimisée

Règles explicites pour économiser crédits :
- Markdown copiable exclusivement
- Pas d'artefacts interactifs
- Factuel et concis
- Cross-validation systématique

## Workflow Recommandé

### Début de Session
```
1. Charger le prompt (si non dans custom instructions)
2. Fournir contexte actuel : "Nous sommes en semaine S067"
3. Partager données récentes si nécessaire
```

### Pendant la Semaine
```
1. Après chaque séance : Documenter dans logs continus
2. Adaptations temps réel : Selon TSB/fatigue
3. Questions ponctuelles : Référence aux protocoles
```

### Fin de Semaine
```
1. Demander : "Génère les 6 fichiers hebdomadaires pour S067"
2. Claude produit dans l'ordre : 1→2→3→4→5→6
3. Créer artefact templates semaine suivante
4. Planifier S068 selon recommandations
```

## Avantages du Nouveau Système

### Pour l'Athlète
- ✅ Continuité assurée (logs permanents)
- ✅ Bilans structurés (6 fichiers/semaine)
- ✅ Protocoles accessibles rapidement
- ✅ Communication claire et concise

### Pour le Coach (Claude)
- ✅ Instructions unifiées et complètes
- ✅ Processus standardisé et reproductible
- ✅ Priorités claires (ordre fichiers)
- ✅ Critères qualité explicites

### Pour la Continuité
- ✅ Transitions coach facilitées
- ✅ Historique traçable
- ✅ Apprentissages cumulés
- ✅ Versioning intégré

## Maintenance du Prompt

### Quand Mettre à Jour
Le prompt doit être mis à jour quand :
- Découverte d'un nouveau protocole majeur
- Changement stratégique (ex: retour outdoor)
- Nouveaux outils/plateformes adoptés
- Enseignements modifiant l'approche globale

### Comment Mettre à Jour
1. Éditer le fichier `project_prompt_v2.md`
2. Incrémenter la version (2.0 → 2.1)
3. Documenter les changements dans un changelog
4. Mettre à jour les custom instructions si applicable

### Versioning
- **Version majeure** (2.0 → 3.0) : Restructuration complète
- **Version mineure** (2.0 → 2.1) : Ajouts/modifications protocoles
- **Patch** (2.1 → 2.1.1) : Corrections, clarifications

## Exemples d'Utilisation

### Exemple 1 : Demander une Séance
```
Utilisateur : "Crée une séance sweet-spot pour demain,
TSB actuel +3, sommeil 6h cette nuit"

Claude :
- Consulte workout-templates.md
- Vérifie protocoles (TSB OK, sommeil limite)
- Adapte intensité si nécessaire
- Génère workout code Intervals.icu
- Documente dans workouts-history.md
```

### Exemple 2 : Bilan Hebdomadaire
```
Utilisateur : "Génère les 6 fichiers pour S067"

Claude :
1. workout_history_s067.md
2. metrics_evolution_s067.md
3. training_learnings_s067.md
4. protocol_adaptations_s067.md
5. transition_s067_s068.md
6. bilan_final_s067.md
+ Artefact : workout_templates_s068
```

### Exemple 3 : Question Protocole
```
Utilisateur : "Est-ce que je peux faire du VO2 demain ?"

Claude :
- Consulte checklist VO2 (5 critères)
- Vérifie TSB actuel
- Regarde historique 48h
- Évalue sommeil
- Répond : OUI/NON avec justification factuelle
```

## FAQ

**Q : Dois-je maintenir les 4 logs ET les 6 fichiers hebdomadaires ?**
R : Oui, les logs sont continuels (histoire complète), les 6 fichiers sont des bilans périodiques (synthèses).

**Q : Puis-je demander des artefacts interactifs ?**
R : Non, le prompt spécifie markdown uniquement pour raisons de maturité technologique et économie de crédits.

**Q : Comment Claude sait-il quelle semaine nous sommes ?**
R : Précisez-le en début de session : "Nous sommes en semaine S067". Claude maintiendra le contexte.

**Q : Que faire si un protocole ne fonctionne pas ?**
R : Documentez dans training-learnings.md, puis mettez à jour protocol_adaptations lors du bilan hebdomadaire.

**Q : Claude garde-t-il la mémoire entre sessions ?**
R : Oui grâce à la mémoire Claude, mais les logs markdown assurent la traçabilité complète et permanente.

## Conclusion

Ce nouveau prompt système unifie et clarifie le processus d'entraînement. Il assure :
- **Continuité** via les logs permanents
- **Structure** via les bilans hebdomadaires
- **Qualité** via les critères explicites
- **Efficacité** via les règles de communication

Pour toute question ou suggestion d'amélioration, documentez-la dans `training-learnings.md` pour révision lors du prochain bilan mensuel.

---

**Guide créé** : Novembre 2025
**Version prompt associée** : 2.0
**Prochaine révision** : Selon besoins terrain
