# Workflow Bilan Hebdomadaire

Guide complet pour générer et intégrer les bilans hebdomadaires avec Claude.ai

## 🎯 Objectif

En fin de semaine, générer **6 fichiers markdown** d'analyse complète :
1. `workout_history_sXXX.md` - Résumé chronologique
2. `metrics_evolution_sXXX.md` - Évolution métriques
3. `training_learnings_sXXX.md` - Enseignements
4. `protocol_adaptations_sXXX.md` - Ajustements protocoles
5. `transition_sXXX_sXXX.md` - Recommandations semaine suivante
6. `bilan_final_sXXX.md` - Synthèse globale

## 🚀 Workflow Complet (5 minutes)

### Étape 1 : Préparer le Prompt

```bash
./scripts/prepare_weekly_report.py --week 067
```

**Options** :
```bash
# Avec date de début (recommandé si séances pas nommées SXXX)
./scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11

# Aide complète
./scripts/prepare_weekly_report.py --help
```

**Ce que fait le script** :
- ✅ Extrait toutes les séances de la semaine depuis `workouts-history.md`
- ✅ Charge le contexte athlète (`project_prompt_v2.md`)
- ✅ Charge les 4 logs continus (extraits)
- ✅ Génère un prompt structuré pour les 6 fichiers
- ✅ Copie automatiquement dans le presse-papier

### Étape 2 : Générer les Bilans avec Claude.ai

1. **Ouvrir Claude.ai** : https://claude.ai

2. **Coller le prompt** : `Cmd+V`

3. **Attendre génération** : ~2-3 minutes
   - Claude génère les 6 fichiers dans l'ordre
   - Format markdown pour chaque fichier

4. **Copier TOUS les fichiers générés**
   - Sélectionner du premier `# workout_history...` jusqu'au dernier `---`
   - `Cmd+C`

💡 **Astuce** : Claude peut générer les fichiers en plusieurs messages si c'est long. Dans ce cas, copier chaque message et les concaténer avec `---` entre chacun.

### Étape 3 : Organiser les Fichiers

```bash
./scripts/organize_weekly_report.py --week 067
```

**Ce que fait le script** :
- ✅ Lit le presse-papier (tous les fichiers générés)
- ✅ Parse et sépare les 6 fichiers
- ✅ Valide la présence des fichiers obligatoires
- ✅ Crée `bilans_hebdo/s067/`
- ✅ Sauvegarde chaque fichier au bon endroit
- ✅ Affiche `git diff` pour vérification

**Options** :
```bash
# Mode test (affiche sans écrire)
./scripts/organize_weekly_report.py --week 067 --dry-run

# Lire depuis un répertoire au lieu du presse-papier
./scripts/organize_weekly_report.py --week 067 --from-dir /tmp/bilans_s067

# Aide
./scripts/organize_weekly_report.py --help
```

### Étape 4 : Vérifier et Commit

```bash
# Vérifier les fichiers créés
ls bilans_hebdo/s067/

# Vérifier le contenu
git diff bilans_hebdo/s067/

# Ajouter au staging
git add bilans_hebdo/s067/

# Commit
git commit -m "Bilan: Semaine S067 complète"

# Push (optionnel)
git push
```

## 📋 Contenu des 6 Fichiers

### 1. workout_history_sXXX.md
**Résumé chronologique de la semaine**
- Contexte semaine (TSS réalisé vs planifié)
- Chronologie complète de toutes les séances
- Découvertes techniques par séance
- Notes coach factuelles
- Évolution métriques finale vs début
- Enseignements majeurs
- Recommandations semaine suivante

### 2. metrics_evolution_sXXX.md
**Métriques et évolution**
- Tableau FTP complet
- Progression quotidienne TSB/Fatigue/Condition/TSS
- Évolution poids début→fin
- Métriques clés finales (CTL/ATL/TSB)
- Validations techniques semaine

### 3. training_learnings_sXXX.md
**Découvertes et enseignements**
- Découvertes techniques majeures
- Patterns physiologiques identifiés
- Innovations testées
- Limites/seuils découverts
- Protocoles validés/invalidés
- Points surveillance futurs

### 4. protocol_adaptations_sXXX.md
**Ajustements protocoles**
- Ajustements protocoles suite enseignements
- Nouveaux seuils/critères techniques
- Modifications hydratation/nutrition
- Adaptations matériel/discipline
- Exclusions/interdictions mises à jour
- Surveillance renforcée identifiée

### 5. transition_sXXX_sXXX.md
**Recommandations semaine suivante**
- État final semaine (TSB/Fatigue/Validations)
- Acquisitions confirmées vs échecs
- Options progression semaine suivante (2-3 scénarios)
- Recommandation justifiée
- Timeline objectifs (tests, cycles)
- Risques identifiés progression

### 6. bilan_final_sXXX.md
**Synthèse globale**
- Objectifs visés vs réalisés
- Métriques finales comparées début
- Découvertes majeures (max 3-4 points)
- Séances clés analysées (succès/échecs)
- Protocoles établis/validés
- Ajustements recommandés cycle suivant
- Enseignements comportementaux
- Conclusion synthétique (2-3 phrases)

## 🔧 Extraction des Séances

### Méthode 1 : Par Numéro de Semaine (automatique)

Si vos séances sont nommées avec le pattern `SXXX-JJ-TYPE-Nom` :

```bash
./scripts/prepare_weekly_report.py --week 067
```

Le script cherche toutes les séances contenant `S067` dans leur nom.

### Méthode 2 : Par Plage de Dates (recommandé)

Si vos séances ne suivent pas le pattern SXXX ou viennent de Strava :

```bash
./scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11
```

Le script extrait toutes les séances entre le `2025-11-11` (lundi) et le `2025-11-17` (dimanche).

**Avantage** : Fonctionne avec n'importe quel nom de séance.

## 📊 Exemple Complet

```bash
# Lundi 18 novembre - Fin de semaine S067
$ ./scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11

📊 Préparation bilan hebdomadaire S067
============================================================

📖 Chargement du contexte athlète...
   ✅ Contexte chargé

🔍 Extraction des séances S067...
   ✅ 5 séance(s) trouvée(s)

✍️  Génération du prompt...
📋 Copie dans le presse-papier...
   ✅ Prompt copié !

============================================================
✅ PROMPT PRÊT POUR BILAN S067
============================================================

📝 ÉTAPES SUIVANTES :

1. Ouvrir Claude.ai
   → https://claude.ai

2. Coller le prompt (Cmd+V)

3. Attendre génération des 6 fichiers (~2-3 minutes)

4. Copier chaque fichier généré

5. Exécuter le script d'organisation :
   python3 scripts/organize_weekly_report.py --week 67

============================================================

# → Aller sur Claude.ai
# → Coller (Cmd+V)
# → Attendre génération (~2-3 minutes)
# → Claude génère les 6 fichiers

# → Copier TOUS les fichiers générés (Cmd+C)

$ ./scripts/organize_weekly_report.py --week 067

📦 Organisation bilan hebdomadaire S067
============================================================

📋 Lecture du presse-papier...
🔍 Parsing des fichiers...
   ✅ 6 fichier(s) détecté(s)

📄 Fichiers détectés :
   - workout_history_s067.md (12543 caractères)
   - metrics_evolution_s067.md (8932 caractères)
   - training_learnings_s067.md (6234 caractères)
   - protocol_adaptations_s067.md (4521 caractères)
   - transition_s067_s068.md (5832 caractères)
   - bilan_final_s067.md (7123 caractères)

✓  Validation des fichiers obligatoires...
   ✅ 6 fichier(s) validé(s)

💾 Sauvegarder dans bilans_hebdo/s067/ ? (Y/n) : Y

📁 Répertoire créé : bilans_hebdo/s067

   ✅ workout_history_s067.md (12543 caractères)
   ✅ metrics_evolution_s067.md (8932 caractères)
   ✅ training_learnings_s067.md (6234 caractères)
   ✅ protocol_adaptations_s067.md (4521 caractères)
   ✅ transition_s067_s068.md (5832 caractères)
   ✅ bilan_final_s067.md (7123 caractères)

✅ 6 fichier(s) sauvegardé(s)

============================================================
GIT DIFF STATS
============================================================
 bilans_hebdo/s067/bilan_final_s067.md          | 89 ++++++++++
 bilans_hebdo/s067/metrics_evolution_s067.md    | 112 ++++++++++++
 bilans_hebdo/s067/protocol_adaptations_s067.md | 65 ++++++++
 bilans_hebdo/s067/training_learnings_s067.md   | 78 +++++++++
 bilans_hebdo/s067/transition_s067_s068.md      | 71 ++++++++
 bilans_hebdo/s067/workout_history_s067.md      | 156 +++++++++++++++++
 6 files changed, 571 insertions(+)

============================================================
✅ BILAN S067 ORGANISÉ
============================================================

📝 ÉTAPES SUIVANTES :

1. Vérifier les fichiers :
   ls bilans_hebdo/s067/

2. Vérifier le contenu :
   git diff bilans_hebdo/s067/

3. Ajouter au commit :
   git add bilans_hebdo/s067/

4. Commit :
   git commit -m "Bilan: Semaine S067 complète"

5. Push (optionnel) :
   git push

============================================================

# Vérifier et commit
$ git add bilans_hebdo/s067/
$ git commit -m "Bilan: Semaine S067 complète"
$ git push
```

## 🔧 Dépannage

### "Aucune séance trouvée pour SXXX"

**Causes** :
1. Les séances ne sont pas nommées avec le pattern `SXXX-JJ-...`
2. Le numéro de semaine est incorrect
3. Les séances n'ont pas encore été ajoutées à `workouts-history.md`

**Solutions** :
```bash
# Utiliser la plage de dates
./scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11

# Vérifier les séances présentes
grep "Date :" logs/workouts-history.md | tail -10
```

### "Fichiers manquants" lors de l'organisation

**Cause** : Claude n'a pas généré tous les 6 fichiers

**Solutions** :
1. Vérifier que vous avez copié TOUS les messages de Claude
2. Si Claude s'est arrêté, lui demander de continuer
3. Relancer Claude.ai avec le même prompt si nécessaire

### Format de fichiers non reconnu

**Cause** : Le parsing ne détecte pas les séparations entre fichiers

**Solutions** :
```bash
# Sauvegarder manuellement chaque fichier dans un répertoire
mkdir /tmp/bilans_s067
# → Copier chaque fichier dans un .md séparé

# Utiliser --from-dir
./scripts/organize_weekly_report.py --week 067 --from-dir /tmp/bilans_s067
```

### Claude génère du texte explicatif entre les fichiers

**Solution** : Normal, le script parse automatiquement et ignore le texte explicatif. Copier tout quand même.

## 📈 Fréquence Recommandée

**Tous les dimanches soir ou lundis matin** :
1. Fin de la semaine d'entraînement
2. Toutes les séances sont complètes dans les logs
3. Temps de génération : ~5 minutes total

**Timeline** :
- 17h-18h dimanche : Dernière séance de la semaine
- 20h-21h dimanche : Génération du bilan
- Lundi matin : Révision et commit

## 🎯 Bénéfices

**Avant (manuel)** :
- ❌ Upload manuel des 4 logs vers Claude
- ❌ Copier-coller chaque fichier un par un
- ❌ Créer manuellement les répertoires
- ❌ Temps : ~15-20 minutes

**Maintenant (automatisé)** :
- ✅ Un script génère le prompt
- ✅ Claude génère tout
- ✅ Un script organise automatiquement
- ✅ Temps : ~5 minutes

## 📝 Checklist Fin de Semaine

```
☐ Toutes les séances de la semaine sont dans workouts-history.md
☐ Les analyses individuelles sont complètes
☐ Exécuter prepare_weekly_report.py
☐ Coller dans Claude.ai
☐ Attendre génération (2-3 min)
☐ Copier tous les fichiers générés
☐ Exécuter organize_weekly_report.py
☐ Vérifier les 6 fichiers créés
☐ Git diff pour validation
☐ Git commit + push
☐ 🎉 Bilan hebdomadaire archivé !
```

---

**Version** : 1.0
**Dernière mise à jour** : 16 novembre 2025
**Scripts** : prepare_weekly_report.py, organize_weekly_report.py
