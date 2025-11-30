# Guide de Démarrage - Intégration Withings
**Pour Stéphane - Projet Coaching Cyclisme**

## 🎯 Objectif

Synchroniser automatiquement tes données Withings (poids + sommeil) vers Intervals.icu pour optimiser la planification de tes entraînements, notamment les séances VO2 max.

## ✅ Ce qui a été préparé

J'ai créé **11 fichiers** pour toi :

### Fichiers essentiels (à garder)
1. **withings_integration.py** - Le cœur du système
2. **withings_sync.py** - Synchronisation quotidienne
3. **withings_setup.py** - Configuration initiale
4. **check_withings_install.py** - Vérification
5. **withings_quickstart.py** - Installation automatisée

### Documentation (à consulter)
6. **README_WITHINGS.md** - Mode d'emploi complet
7. **ARCHITECTURE_WITHINGS.md** - Architecture technique
8. **INDEX_WITHINGS.md** - Index de tous les fichiers

### Optionnels (pratiques)
9. **withings_demo.py** - Démonstrations interactives
10. **.gitignore_withings** - Protection fichiers sensibles
11. **.env.withings.example** - Template configuration

## 🚀 Installation (3 options)

### Option 1: Installation automatique (RECOMMANDÉE)

```bash
# Télécharger tous les fichiers que j'ai créés
# Puis exécuter:
python withings_quickstart.py
```

Cette commande va :
- Installer les dépendances Python
- Configurer le .gitignore
- Créer le fichier .env.withings
- Lancer l'authentification Withings
- Vérifier que tout fonctionne

### Option 2: Installation manuelle

```bash
# 1. Installer les packages Python
pip install withings-api requests python-dotenv

# 2. Protéger les fichiers sensibles
cp .gitignore_withings .gitignore

# 3. Créer la configuration
cp .env.withings.example .env.withings
nano .env.withings  # Éditer avec ton Secret Withings

# 4. Authentification
python withings_setup.py

# 5. Vérification
python check_withings_install.py
```

### Option 3: Installation pas à pas détaillée

Voir `README_WITHINGS.md` section "Installation"

## 📝 Configuration requise

### Informations Withings Developer Dashboard

Tu as déjà créé l'application, il te faut juste :

1. **ClientID** (déjà dans le code)
   ```
   c5e8820a701242a8708c54ee9fcc83915f02270f2ae0930b9a5917bbb3d21278
   ```

2. **Secret** (à récupérer du Dashboard)
   - Aller sur https://developer.withings.com
   - Ouvrir ton application "Sync Withings Intervals"
   - Copier le "Secret"

3. **Callback URL** (déjà configuré)
   ```
   https://4f3c-2a01-cb14-8513-df00-2031-d098-d697-75c1.ngrok-free.app/auth/withings/callback
   ```

### Configuration Intervals.icu (déjà OK)

Les valeurs sont déjà dans le code :
- Athlete ID: `i151223`
- API Key: `REDACTED_INTERVALS_KEY`

## 🔑 Première utilisation

### 1. Authentification (une seule fois)

```bash
python withings_setup.py
```

**Ce qui se passe** :
1. Un serveur web local démarre
2. Ton navigateur s'ouvre automatiquement
3. Tu te connectes à Withings et autorises l'application
4. Tu es redirigé automatiquement
5. Les credentials sont sauvegardés dans `withings_credentials.json`

**⚠️ Important** : Le fichier `withings_credentials.json` est **SENSIBLE**. Ne le partage jamais et ne le commite pas sur Git !

### 2. Test de connexion

```bash
python check_withings_install.py
```

Vérifie que :
- ✅ Dépendances installées
- ✅ Fichiers présents
- ✅ Credentials valides
- ✅ Connexion API OK

### 3. Premier sync

```bash
python withings_sync.py sync
```

**Sortie exemple** :
```
📊 SYNCHRONISATION POIDS
✓ Poids synchronisé: 85.8kg le 2025-01-15

😴 SYNCHRONISATION SOMMEIL
✓ Sommeil synchronisé: 7.2h le 2025-01-15

🎯 RECOMMANDATIONS ENTRAÎNEMENT:
   → Conditions optimales pour séance intensive
   ✅ CONDITIONS OPTIMALES POUR VO2 MAX
```

## 📅 Utilisation quotidienne

### Commandes principales

```bash
# 1. Synchronisation quotidienne (à faire chaque matin)
python withings_sync.py sync

# 2. Vérifier si tu peux faire du VO2 max aujourd'hui
python withings_sync.py readiness

# 3. Résumé de la semaine (chaque dimanche)
python withings_sync.py summary
```

### Intégration dans ta routine

**Matin (avant l'entraînement)** :

```bash
# Check ta disponibilité
python withings_sync.py readiness
```

**Sortie si conditions OK** :
```
🎯 DISPONIBILITÉ ENTRAÎNEMENT:
   Sommeil: 7.5h
   Score: 85/100
   Recommandation: ALL_SYSTEMS_GO
   ✅ OK pour VO2 max
```

**Sortie si conditions KO** :
```
🎯 DISPONIBILITÉ ENTRAÎNEMENT:
   Sommeil: 5.8h
   Score: 62/100
   Recommandation: ENDURANCE_MAX
   ⚠️  Sommeil insuffisant - éviter VO2 max
```

## 🤖 Automatisation (optionnel)

### Option 1: Cron (Mac/Linux)

Ajouter à ton crontab (`crontab -e`) :

```bash
# Sync quotidien à 7h du matin
0 7 * * * cd /path/to/project && python withings_sync.py sync

# Résumé hebdomadaire le dimanche à 20h
0 20 * * 0 cd /path/to/project && python withings_sync.py summary
```

### Option 2: Synology NAS (ton setup)

Créer une tâche planifiée :
1. Control Panel > Task Scheduler
2. Create > Scheduled Task > User-defined script
3. Script: `/usr/local/bin/python3 /path/to/withings_sync.py sync`
4. Schedule: Tous les jours à 7h00

## 🎨 Démonstrations interactives

Pour explorer toutes les fonctionnalités :

```bash
python withings_demo.py
```

Menu interactif avec 4 démos :
1. Récupération données basiques
2. Évaluation pour entraînement
3. Analyse historique (7 jours)
4. Scénarios de décision

## 📊 Intégration avec Claude Coach

### Dans tes conversations avec moi

```markdown
Avant de planifier une séance VO2 max, je peux vérifier :

"Voici les données Withings d'hier soir :
[résultat de `python withings_sync.py readiness`]

Est-ce que je peux faire ma séance VO2 prévue aujourd'hui ?"
```

Je pourrai alors :
- Valider ou vétoer la séance
- Proposer une alternative si nécessaire
- Ajuster l'intensité

### Automatisation future possible

Tu pourrais même créer un script qui :
1. Récupère les données Withings
2. Les envoie à Claude via API
3. Reçoit une recommandation
4. Ajuste automatiquement la séance dans Intervals.icu

## 🔧 Maintenance

### Fichiers à NE JAMAIS commiter sur Git

```
withings_credentials.json    ← Tokens OAuth
.env.withings                ← Configuration avec Secret
*.secret                     ← Tout fichier .secret
*.log                        ← Logs (peuvent contenir données perso)
```

**Vérifier** : Le `.gitignore` doit contenir ces patterns

### Mise à jour périodique

```bash
# Tous les 3 mois environ
pip install --upgrade withings-api requests python-dotenv
```

### Si problème de connexion

```bash
# Refaire l'authentification
python withings_setup.py
```

## 📚 Documentation

### Pour aller plus loin

1. **README_WITHINGS.md** - Guide utilisateur complet
   - Installation détaillée
   - Toutes les commandes
   - Troubleshooting
   - Exemples avancés

2. **ARCHITECTURE_WITHINGS.md** - Si tu veux comprendre comment ça marche
   - Architecture du système
   - Flux de données
   - Points d'extension

3. **INDEX_WITHINGS.md** - Index de tous les fichiers
   - Organisation projet
   - Quick reference

## 🆘 En cas de problème

### Problème 1: "Module withings_api not found"

```bash
pip install withings-api
```

### Problème 2: "Credentials not found"

```bash
python withings_setup.py
```

### Problème 3: "No data found"

Vérifier que :
- Ta balance/tracker Withings est synchronisé
- Les données apparaissent dans l'app Withings
- Tu cherches la bonne période

### Problème 4: "Callback timeout"

Vérifier que :
- Ton tunnel ngrok est actif
- L'URL dans Developer Dashboard correspond
- Le port est correct

### Debug complet

```bash
python check_withings_install.py
```

## ✨ Bénéfices attendus

### Court terme (immédiat)

- ✅ Synchronisation automatique poids/sommeil
- ✅ Validation objective avant séances VO2 max
- ✅ Moins de risque de surmenage
- ✅ Données centralisées Intervals.icu

### Moyen terme (1-2 mois)

- 📊 Corrélations sommeil ↔ performances
- 📈 Tendances poids vs charge entraînement
- 🎯 Optimisation planification

### Long terme (3-6 mois)

- 🤖 Recommandations ML personnalisées
- 📱 Dashboard visualisation
- 🔔 Alertes automatiques

## 🎉 Prêt à démarrer ?

### Checklist finale

- [ ] Fichiers téléchargés
- [ ] Dépendances installées (`pip install ...`)
- [ ] Secret Withings récupéré
- [ ] `python withings_setup.py` exécuté
- [ ] Authentification réussie
- [ ] Premier `sync` OK
- [ ] Ajouté au workflow quotidien

### Première action NOW

```bash
python withings_quickstart.py
```

Et c'est parti ! 🚀

---

**Questions ?** Partage les sorties des commandes dans notre conversation et on débogue ensemble.

**Succès ?** Excellent ! Tu peux maintenant utiliser `withings_sync.py` quotidiennement.
