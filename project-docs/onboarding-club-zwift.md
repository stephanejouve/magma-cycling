# Magma Cycling — Ton coach IA personnel

**Guide de demarrage pour les membres du club**

---

## C'est quoi en une phrase ?

Un assistant IA qui tourne **sur ton ordinateur**, connecte a ta plateforme d'entrainement (Intervals.icu), et qui fait le travail d'un coach : planifier tes semaines, analyser tes sorties, adapter les seances a ta fatigue et a ton sommeil.

Tu lui parles en francais, comme a un coach humain. Il repond avec des donnees.

Magma est **agnostique** : il fonctionne avec Claude Desktop, mais aussi avec tout autre client IA compatible MCP (Cursor, Windsurf, Continue, ou tout futur agent desktop).

---

## Ce que ca change concretement

### Avant (sans Magma)

- Tu ouvres Zwift, tu choisis un workout au hasard
- Tu n'as aucune idee si c'est adapte a ta fatigue du jour
- Apres la seance, personne ne te dit ce que tu as bien fait ou rate
- Ta semaine d'entrainement n'a pas de structure

### Avec Magma

- L'IA genere ta semaine complete (lundi-dimanche) en fonction de ton etat
- Avant de monter sur le velo, elle te dit si c'est le bon jour pour un interval ou s'il vaut mieux rouler cool
- Apres la seance, elle analyse ta puissance, ta cadence, ta compliance au plan
- Elle apprend de ton historique — plus tu l'utilises, plus elle te connait

---

## Comment ca marche (vue d'ensemble)

```
Toi sur Zwift / route
       |
       v
  Intervals.icu          Withings (sommeil, poids)
  (tes activites)        (optionnel)
       |                       |
       +-----------+-----------+
                   |
                   v
           Magma Cycling
           (ton ordinateur)
                   |
                   v
    Ton agent IA desktop (au choix)
   Claude Desktop / Cursor / Windsurf / ...
```

**Tout reste chez toi.** Tes donnees ne partent pas dans le cloud d'un tiers. Magma tourne sur ton ordinateur, et l'IA ne voit que ce que tu lui montres (tes activites Intervals.icu).

---

## D'ou viennent les donnees ?

Magma est un **moteur d'analyse** — il ne stocke pas tes sorties, il les lit depuis Intervals.icu via leur API. Le flux est simple :

```
Ton compteur (Garmin / Wahoo / Hammerhead / Zwift)
       |
       v
  Intervals.icu  <--- connexion directe (automatique)
       |
       v
  Magma lit tes donnees via l'API
       |
       v
  Ton agent IA analyse et te repond
```

### Configurer la connexion directe de ton compteur

Dans Intervals.icu, va dans **Settings > Connections** et active la synchro avec ton compteur. Les principales :

- **Garmin Connect** : toggle dans Connections, tes sorties arrivent automatiquement
- **Wahoo** : idem, connexion native
- **Zwift** : synchro automatique via Strava ou Garmin Connect

C'est un toggle, ca prend 2 minutes, et apres chaque sortie remonte automatiquement dans Intervals.icu — donc dans Magma.

### Et Strava dans tout ca ?

Tu peux garder Strava pour le cote social (segments, kudos, clubs). Mais l'API Strava **interdit contractuellement le re-export de donnees vers un tiers** — c'est leur politique, pas la notre, et ca empeche toute integration directe Strava → Magma.

Soyons honnetes : si tu as des annees d'historique uniquement dans Strava, le demarrage demande un effort initial. Il faut exporter ton historique Strava (archive ZIP depuis les parametres de ton compte), puis l'importer dans Intervals.icu (Settings > Import). C'est une operation unique mais longue (24-48h pour un gros historique). Une fois fait, les donnees restent dans Intervals.icu definitivement, meme si tu deconnectes Strava ensuite.

Pour la suite, configure ton compteur pour envoyer les fichiers FIT **directement** vers Intervals.icu, en parallele de Strava. Les deux cohabitent sans probleme — ton compteur envoie les donnees aux deux plateformes independamment.

### J'ai deja un historique Intervals.icu

**Tu n'as rien a changer.** Magma lit ton historique existant tel quel. Des la connexion, tu peux demander "analyse ma forme des 6 dernieres semaines" ou "montre-moi mes activites de mars" — tout est deja accessible.

Magma ne modifie jamais ton historique. Il ecrit uniquement sur ton calendrier quand tu lui demandes de synchroniser un plan d'entrainement, et seulement sur les jours futurs.

---

## Les 5 fonctions que tu vas utiliser tout le temps

### 1. Planification de la semaine

> "Planifie ma semaine prochaine"

L'IA regarde ton etat actuel (charge d'entrainement, fatigue, sommeil) et genere 5 a 7 seances avec des objectifs precis : endurance, intervalles, recuperation. Chaque seance a une duree, un TSS cible, et une description du contenu.

### 2. Check avant la seance

> "Est-ce que je suis en etat de faire mes intervalles aujourd'hui ?"

L'IA verifie ton sommeil de la nuit, ta balance fatigue/forme, et te dit si tu devrais maintenir le plan, le remplacer par un endurance, ou carritement te reposer.

### 3. Analyse post-sortie

> "Analyse ma sortie d'aujourd'hui"

Apres synchronisation avec Intervals.icu, l'IA compare ce que tu as fait vs ce qui etait prevu. Elle te donne un score d'adherence (0-100%) et un feedback detaille : puissance, cadence, gestion de l'effort, recommandations pour la suite.

### 4. Bilan mensuel

> "Fais le bilan du mois de mars"

Resume : volume total, distribution d'intensite (combien de temps en zone 2 vs zone 4), evolution du FTP, tendances de poids/sommeil, et insights IA.

### 5. Adaptation terrain (sorties outdoor)

> "Adapte mon workout de 3x20min sweet spot au parcours de la cote de Meudon"

L'IA prend le profil de ta route (denivele, pentes) et ajuste les objectifs segment par segment : cadence, braquet, puissance. Utile quand tu sors de Zwift pour rouler dehors.

---

## Ce dont tu as besoin

| Element | Obligatoire ? | Commentaire |
|---------|:---:|-------------|
| **Intervals.icu** (compte gratuit) | Oui* | Plateforme d'entrainement testee et supportee. L'architecture est concue pour accueillir d'autres plateformes (TrainingPeaks, Strava, etc.) mais seul Intervals.icu est valide a ce jour |
| **Un client MCP** (Claude Desktop, Cursor, Windsurf...) | Oui | L'interface pour parler a l'IA — c'est lui qui fournit le LLM |
| **Python 3.11+** | Non* | Le moteur — sauf si tu utilises l'executable standalone (Mac ou Windows) |
| **Withings Sleep Analyzer** | Non | Pour le suivi automatique du sommeil |
| **Cle API IA** (Claude ou Mistral) | Non | Uniquement pour les analyses automatiques (crons). En usage interactif, c'est ton agent desktop qui fait le travail |

**Zwift, Garmin, Wahoo** : configure la connexion directe vers Intervals.icu (Settings > Connections). Tes sorties remontent automatiquement et Magma les voit. Tu peux garder Strava en parallele sans probleme.

---

## Installation en 15 minutes

Choisis ta methode selon ton systeme. Mac ou Windows, le resultat est le meme.

### Installation Mac

Tu as **2 options** selon ton confort technique. Le resultat est le meme.

#### Option A — Executable standalone (recommande)

Aucune installation technique requise. Telecharge, autorise, lance.

1. Va sur la page [Releases](https://github.com/stephanejouve/magma-cycling/releases) du projet
2. Telecharge le fichier correspondant a ton Mac :
   - **Mac Intel** (avant 2020) : `magma-cycling-vX.X.X-macos-x86_64`
   - **Mac Apple Silicon** (M1/M2/M3/M4) : `magma-cycling-vX.X.X-macos-arm64`
   - _Pas sur ?_ Clique  > **A propos de ce Mac** — si tu vois "Puce Apple M...", c'est ARM64. Sinon c'est Intel.
3. Ouvre le Terminal (Cmd+Espace > "Terminal") et copie-colle ces **trois commandes** une par une, en appuyant sur Entree apres chacune.

**Commande 1** — lever la quarantaine macOS (ne produit aucune sortie, c'est normal) :

```bash
xattr -d com.apple.quarantine ~/Downloads/magma-cycling-*-macos-*
```

**Commande 2** — rendre le fichier executable (ne produit aucune sortie, c'est normal) :

```bash
chmod +x ~/Downloads/magma-cycling-*-macos-*
```

**Commande 3** — lancer le programme :

```bash
~/Downloads/magma-cycling-*-macos-*
```

> **Qu'est-ce que ces etoiles `*` ?** C'est un raccourci du Terminal qui veut dire "n'importe quel texte".
> Le Terminal trouvera tout seul le fichier que tu as telecharge, quel que soit le numero de version.
> Tu n'as rien a remplacer — copie-colle tel quel.

> **Pourquoi la commande `xattr` ?** Les fichiers telecharges depuis Internet sont mis en quarantaine
> par macOS. Sans cette commande, le Mac tue silencieusement le programme sans message d'erreur.

4. Un menu interactif s'affiche — tape **1** pour lancer l'assistant de configuration

> Si Claude Desktop est deja installe, le wizard configure le MCP automatiquement.
> Sinon, il affiche "Claude Desktop non detecte" — c'est normal. Installe Claude Desktop
> ensuite (voir plus bas), puis relance le setup pour que la connexion se fasse.

#### Option B — Python + Poetry

Pour ceux qui veulent le code source et les mises a jour en `git pull` :

Ouvre le Terminal et copie-colle :

```bash
# Installer Python et Poetry (gestionnaire de paquets)
brew install python@3.12
pip3 install poetry

# Cloner le projet
git clone https://github.com/stephanejouve/magma-cycling.git
cd magma-cycling

# Installer les dependances
poetry install
```

> **Pas de panique** : ces commandes ne modifient rien sur ton Mac.
> Elles installent le programme dans un dossier isole.

### Installation Windows

Tu as **3 options** selon ton confort technique. Le resultat est le meme.

#### Option A — Executable standalone (recommande)

Aucune installation technique requise. Telecharge, double-clique, c'est parti.

1. Va sur la page [Releases](https://github.com/stephanejouve/magma-cycling/releases) du projet
2. Telecharge `magma-cycling-vX.X.X-windows.exe` (la derniere version)
3. Place le fichier ou tu veux (ex: `C:\magma-cycling\`)
4. **Double-clique sur l'exe** — un menu interactif s'affiche :

```
  magma-cycling v3.4.0

  Configuration
    ok .env trouve
    -- Intervals.icu non configure
    -- Withings non configure
    -- Espace donnees non trouve

  Connexion IA
    -- Claude Desktop non detecte
    -- MCP magma-cycling non enregistre

  Actions :
    1. Lancer le setup (configuration)
    2. Demarrer le serveur MCP
    3. Quitter
```

5. Tape **1** pour lancer l'assistant de configuration (5 questions)
6. A la fin du setup, Claude Desktop est configure automatiquement

Python, Poetry, dependances — tout est embarque dans l'executable.

#### Option B — Python + Poetry

Pour ceux qui veulent le code source et les mises a jour en `git pull` :

1. Telecharge et installe **Python 3.12** depuis python.org
   (coche "Add Python to PATH" pendant l'installation)
2. Telecharge et installe **Git** depuis git-scm.com
3. Ouvre **PowerShell** et copie-colle :

```powershell
pip install poetry
git clone https://github.com/stephanejouve/magma-cycling.git
cd magma-cycling
poetry install
```

#### Option C — Docker

Si tu preferes ne rien installer sur ta machine :

1. Installe **Docker Desktop** depuis docker.com
2. Ouvre **PowerShell** :

```powershell
docker run -it -v $HOME\training-logs:/data/training-logs `
    ghcr.io/stephanejouve/magma-cycling:latest mcp-server
```

### Suite commune (Mac option B et Windows option B)

**Etape 2 — Lancer l'assistant de configuration**

> **Utilisateurs executable standalone (Mac option A / Windows option A)** :
> pas besoin de cette etape manuellement. Lance l'executable et tape 1 dans le menu — le setup se lance tout seul.

```bash
# Si Python + Poetry :
poetry run setup
```

L'assistant te pose 5 questions :

1. **Ta cle API Intervals.icu** — tu la trouves dans Intervals.icu > Settings > Developer Settings
2. **Ton profil athlete** — poids, FTP, age, frequence cardiaque max
3. **Fournisseur IA** (optionnel) — une cle Claude ou Mistral, seulement si tu veux les analyses automatiques (crons la nuit). En usage interactif, c'est ton agent desktop qui genere les analyses
4. **Ton dossier de donnees** — un dossier local pour stocker ton historique
5. **Validation** — l'assistant verifie que tout fonctionne

A la fin, il ecrit un fichier `.env` avec ta configuration. Tu ne touches plus jamais a ce fichier.

**Etape 3 — Connecter ton agent IA desktop**

Magma utilise le protocole **MCP** (Model Context Protocol), un standard ouvert.
Tu peux utiliser n'importe quel client compatible. Voici les principaux :

| Client | Plateforme | Gratuit ? | Comment configurer |
|--------|-----------|:---------:|-------------------|
| **Claude Desktop** | Mac, Windows | Oui (base) | Settings > Developer > Edit Config |
| **Cursor** | Mac, Windows, Linux | Freemium | Settings > MCP |
| **Windsurf** | Mac, Windows, Linux | Freemium | Settings > MCP Servers |
| **Continue** | VS Code / JetBrains | Oui | config.json > mcpServers |

La config MCP depend de ton mode d'installation :

**Si Python + Poetry (Mac ou Windows option B) :**

```json
{
  "mcpServers": {
    "magma-cycling": {
      "command": "poetry",
      "args": ["run", "mcp-server"],
      "cwd": "/chemin/vers/magma-cycling"
    }
  }
}
```

**Si executable standalone (Mac option A / Windows option A) :**

> L'assistant de configuration fait ca automatiquement.
> En cas de besoin, voici la config manuelle :

Mac :

```json
{
  "mcpServers": {
    "magma-cycling": {
      "command": "/chemin/vers/magma-cycling",
      "args": ["mcp-server"]
    }
  }
}
```

Windows :

```json
{
  "mcpServers": {
    "magma-cycling": {
      "command": "C:\\magma-cycling\\magma-cycling.exe",
      "args": ["mcp-server"]
    }
  }
}
```

**Si Docker (option C) :**

```json
{
  "mcpServers": {
    "magma-cycling": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
        "-v", "/chemin/vers/training-logs:/data/training-logs",
        "ghcr.io/stephanejouve/magma-cycling:latest", "mcp-server"]
    }
  }
}
```

Redemarre ton client apres l'ajout. C'est fait — tu peux parler a ton coach IA.

---

## A quoi ca ressemble ? (conversations reelles)

Voici des echanges typiques dans Claude Desktop. Tu tapes en haut,
l'IA repond en dessous — exactement comme un chat.

---

### Scenario 1 : "Je viens de commencer, planifie ma semaine"

**Toi :**
> Salut, je suis en semaine 14, phase de build. Mon FTP est a 220W,
> je peux rouler mardi, mercredi, jeudi et samedi. Planifie-moi ca.

**Magma :**
> J'ai regarde ton etat actuel :
> - CTL (forme) : 58 — en progression reguliere
> - ATL (fatigue) : 52 — correcte
> - TSB (fraicheur) : +6 — tu es frais, bon moment pour charger
> - Sommeil moyen cette semaine : 6h45
>
> Voici ta semaine S14 :
>
> | Jour | Seance | Contenu | Duree | TSS |
> |------|--------|---------|-------|-----|
> | Mar | S14-01 Intervalles VO2max | 5x4min @ 242W (110%) / 3min recup | 60 min | 75 |
> | Mer | S14-02 Endurance Z2 | Pedalage souple 145-160W, cadence 85+ | 1h30 | 55 |
> | Jeu | S14-03 Sweet Spot | 3x15min @ 194W (88%) / 5min recup | 75 min | 80 |
> | Sam | S14-04 Sortie longue | Endurance Z2, dernier 30min a 176W (80%) | 2h30 | 110 |
>
> **Total semaine : 320 TSS** (+7% vs S13)
> CTL projete fin de semaine : 62
>
> J'ai synchronise les 4 seances sur ton calendrier Intervals.icu.
> Tu veux que j'attache des workouts structures (.zwo) pour Zwift ?

**Toi :**
> Oui, mets des .zwo pour mardi et jeudi

**Magma :**
> C'est fait. Les workouts sont dans ton dossier et lies aux seances :
> - S14-01 : `VO2max_5x4min_110pct.zwo`
> - S14-03 : `SweetSpot_3x15min_88pct.zwo`
>
> Tu les trouveras directement dans Zwift > Custom Workouts.

---

### Scenario 2 : "J'ai mal dormi, je fais quoi ?"

**Toi :**
> Check pre-seance. J'ai l'impression d'etre cuit aujourd'hui.

**Magma :**
> J'ai verifie ton etat :
>
> - **Sommeil** : 4h52 (score 4/4 = mauvais)
> - **TSB** : -8 (fatigue legere)
> - **Seance prevue** : S14-01 Intervalles VO2max (5x4min @ 110%)
>
> **Mon avis : ne fais PAS les intervalles VO2max aujourd'hui.**
>
> Avec moins de 5h de sommeil, ta capacite a maintenir 110% FTP
> pendant 4 minutes est tres reduite. Le risque de seance ratee
> (et de frustration) est eleve.
>
> Options :
> 1. **Remplacer par endurance Z2** (60 min, 145-160W, cadence libre)
> 2. **Decaler les intervalles a demain** et faire l'endurance aujourd'hui
> 3. **Repos complet** si la fatigue est aussi physique
>
> Qu'est-ce que tu preferes ?

**Toi :**
> On decale. Intervalles demain, endurance aujourd'hui.

**Magma :**
> Fait. J'ai echange mardi et mercredi dans le planning :
> - Aujourd'hui (mar) : Endurance Z2, 1h30
> - Demain (mer) : Intervalles VO2max 5x4min
>
> Le calendrier Intervals.icu est mis a jour. Bonne seance cool !

---

### Scenario 3 : "Analyse ma sortie Zwift"

**Toi :**
> J'ai fait ma seance d'intervalles ce matin, analyse.

**Magma :**
> J'ai recupere ton activite sur Intervals.icu et compare au plan.
>
> **Seance S14-01 — Intervalles VO2max**
> Adherence globale : **87%**
>
> | Metrique | Plan | Realise | Ecart |
> |----------|------|---------|-------|
> | TSS | 75 | 72 | -4% OK |
> | IF | 0.95 | 0.91 | -4% |
> | Duree | 60 min | 58 min | -2 min OK |
> | Puissance moy. intervalles | 242W | 234W | -3% |
> | Cadence moy. intervalles | — | 93 RPM | bien |
> | Decouplage cardiaque | — | 3.2% | excellent |
>
> **Ce qui va bien :**
> - Cadence reguliere a 93 RPM sur les 5 blocs — bon controle
> - Decouplage a 3.2% = ton coeur n'a pas derive, signe de bonne forme aerobique
> - Les 3 premiers intervalles sont tres bien executes (239-244W)
>
> **Point d'attention :**
> - Les 2 derniers blocs faiblissent : 228W et 224W. C'est classique
>   en VO2max quand le sommeil etait moyen (5h12 la nuit precedente).
> - Suggestion : la semaine prochaine, maintiens 5x4min plutot que
>   d'augmenter a 6 blocs. Consolide d'abord la regularite.
>
> **Pour demain :**
> Seance prevue : Sweet Spot 3x15min. Aucune contre-indication.

---

### Scenario 4 : "Bilan du mois"

**Toi :**
> Fais-moi le bilan de mars.

**Magma :**
> **Bilan Mars 2026**
>
> **Volume :**
> - 18 seances completees sur 22 planifiees (82% de compliance)
> - TSS total : 1,280 (moyenne 320/semaine)
> - Heures : 24h15
>
> **Intensite :**
> - Zone 2 (endurance) : 62% du temps — bien, c'est la base
> - Zone 4 (seuil) : 18% — equilibre
> - Zone 5 (VO2max) : 8% — suffisant pour progresser
> - Zone 1 (recup) : 12%
>
> **Progression :**
> - FTP : 215W → 220W (+2.3%) — test valide le 22/03
> - CTL : 48 → 58 (+21%) — belle montee en charge
> - Poids : 78.2 kg → 77.5 kg (-0.9%)
>
> **Tendances :**
> - Sommeil moyen : 6h12 (insuffisant, cible > 7h)
> - Les seances du lundi sont systematiquement ratees ou sautees
>   (3 sur 4). Suggestion : programmer le repos le lundi.
> - Meilleure seance : S12-03 Sweet Spot (adherence 96%)
> - Plus grosse progression : VO2max, +12W en puissance moyenne
>   sur les intervalles entre debut et fin mars.
>
> Tu veux que je tienne compte de ces tendances pour planifier avril ?

---

### Scenario 5 : "Je vais rouler dehors dimanche"

**Toi :**
> Dimanche je fais la boucle de la vallee de Chevreuse avec le club.
> 85 km, 900m de D+. Adapte mon sweet spot prevu a ce parcours.

**Magma :**
> J'ai le profil de la boucle Chevreuse dans tes circuits sauvegardes
> (extrait de ta sortie du 12 fevrier).
>
> **Adaptation du Sweet Spot (3x15min @ 194W) au terrain :**
>
> | Km | Segment | Pente | Consigne |
> |----|---------|-------|----------|
> | 12-18 | Cote de Port-Royal | 4.2% | 200W, cadence 75, braquet 34x21 |
> | 28-35 | Faux plat D. de Limours | 1.8% | 190W, cadence 85, braquet 50x19 |
> | 45-52 | Cote de Chevreuse | 5.1% | 210W, cadence 70, braquet 34x23 |
> | Reste | Plat / descentes | 0% | 160-170W, cadence 90+, recup active |
>
> **Strategie globale :**
> - Place tes 3 blocs sweet spot sur les 3 cotes (naturellement)
> - En descente : mouline leger, ne pedale pas inutilement
> - Hydratation : 500ml/h minimum (prevu 3h30)
> - TSS estime sortie complete : ~180 (au lieu de 80 en indoor)
>
> Attention : le TSS sera plus eleve que prevu a cause du D+.
> J'ai ajuste ta semaine suivante pour compenser.

---

### Scenario 6 : "C'est quoi mon etat la ?"

**Toi :**
> Montre-moi ou j'en suis.

**Magma :**
> **Etat au 4 avril 2026 :**
>
> | Metrique | Valeur | Tendance |
> |----------|--------|----------|
> | FTP | 220W | +5W depuis mars |
> | CTL (forme) | 58 | en hausse |
> | ATL (fatigue) | 52 | stable |
> | TSB (fraicheur) | +6 | frais |
> | Poids | 77.5 kg | -0.7 kg/mois |
> | W/kg | 2.84 | +0.10 depuis fevrier |
> | Sommeil moy. 7j | 6h12 | insuffisant |
>
> **En resume :** tu es dans une bonne dynamique. La forme monte
> regulierement, la fatigue est geree. Le seul point faible reste
> le sommeil — chaque heure en plus = meilleure recup = plus de watts.

---

### Scenario 7 : "J'ai pas envie mais faut que je roule"

**Toi :**
> Flemme totale. Mais je veux pas louper la seance.
> Propose-moi un truc court et efficace.

**Magma :**
> Je comprends. Voici une option "minimum viable" qui preserve
> ta progression sans te demolir :
>
> **Express Sweet Spot — 35 minutes**
> - 10 min echauffement progressif
> - 2x8min @ 88% FTP (176W) / 3min recup
> - 4 min retour au calme
>
> TSS : 38. C'est court mais ca maintient le stimulus seuil.
> Mieux que rien, et tu seras content de l'avoir fait.
>
> Je l'attache en .zwo et je marque la seance S14-03 comme modifiee ?

---

## FAQ

**Q : Est-ce que je dois etre bon en informatique ?**
Non. L'installation prend 15 minutes et apres tu ne touches plus au terminal. Tout se passe dans ton client IA (Claude Desktop, Cursor, etc.), en francais, comme un chat.

**Q : Ca coute combien ?**
Intervals.icu est gratuit. Le code Magma est open source et gratuit. Ton agent desktop (Claude Desktop, Cursor, etc.) a son propre modele de tarification. En usage interactif, c'est lui qui fournit l'IA — pas besoin de cle API supplementaire. Une cle API (Claude/Mistral, 2-5 euros/mois) n'est utile que si tu actives les analyses automatiques de nuit (crons).

**Q : Mes donnees restent privees ?**
Oui. Le serveur tourne sur ton Mac (ou ton NAS). Tes donnees ne passent par aucun serveur tiers sauf Intervals.icu (que tu utilises deja) et le fournisseur IA pour les analyses textuelles (pas de donnees personnelles transmises, seulement les metriques d'entrainement).

**Q : Je peux l'utiliser sur Windows ?**
Oui, 3 options : un executable standalone (zero installation technique), Python classique, ou Docker. Voir la section "Installation Windows" plus haut.

**Q : Je peux l'utiliser sur Mac ?**
Oui, 2 options : un executable standalone (zero installation technique) ou Python + Poetry. Voir la section "Installation Mac" plus haut.

**Q : Ca remplace un vrai coach ?**
Non. Ca automatise les taches repetitives d'un coach : planification, suivi d'adherence, feedback post-seance. Si tu as un coach humain, Magma est un complement. Si tu n'en as pas, c'est une excellente base structuree.

**Q : Je roule uniquement sur Zwift, c'est utile ?**
Oui. La majorite des fonctions (planification, analyse, suivi de charge) sont independantes du terrain. L'adaptation terrain est un bonus pour les sorties outdoor.

**Q : Je n'utilise pas Intervals.icu, ca marche quand meme ?**
Pas encore. Aujourd'hui seul Intervals.icu est teste et supporte. Le code est concu avec une couche d'abstraction (provider agnostique) qui permettra d'ajouter d'autres plateformes sans tout recoder. Si tu es sur une autre plateforme et motive pour contribuer, fais signe. Intervals.icu est gratuit et s'alimente directement depuis ton compteur (Garmin, Wahoo, Zwift) — voir la section "D'ou viennent les donnees" plus haut.

**Q : J'ai deja des annees de donnees dans Intervals.icu, je dois tout recommencer ?**
Non. Magma lit ton historique existant via l'API. Tu connectes ton compte et tout est disponible immediatement — activites, metriques, courbe de puissance. Magma ne modifie jamais ton historique, il le consulte.

**Q : Et si mes donnees sont dans Strava ?**
L'API Strava interdit le re-export vers des tiers, donc Magma ne peut pas lire Strava directement. La solution : configure ton compteur pour envoyer les FIT vers Intervals.icu en parallele (Settings > Connections, 2 minutes). Pour importer ton historique Strava existant, utilise l'outil d'import natif d'Intervals.icu (Settings > Import). C'est un processus long (24-48h pour plusieurs annees) mais c'est une operation unique.

---

## Glossaire rapide

| Terme | Definition |
|-------|-----------|
| **TSS** | Training Stress Score — mesure la charge d'une seance (plus c'est haut, plus c'est dur) |
| **FTP** | Functional Threshold Power — ta puissance seuil sur 1h (la reference pour tes zones) |
| **CTL** | Chronic Training Load — ta forme sur 42 jours (monte = tu progresses) |
| **ATL** | Acute Training Load — ta fatigue recente sur 7 jours |
| **TSB** | Training Stress Balance — CTL minus ATL. Positif = frais. Negatif = fatigue |
| **IF** | Intensity Factor — ratio puissance moyenne / FTP. 0.75 = endurance, 0.95 = seuil |
| **MCP** | Model Context Protocol — standard ouvert qui permet a n'importe quel agent IA de parler a Magma |
| **Adherence** | Score 0-100% — a quel point ta sortie correspond au plan |

---

## Besoin d'aide ?

Contacte Stephane sur le Discord/groupe du club. Si tu bloques a l'installation, on peut faire un partage d'ecran de 10 minutes.

---

*Magma Cycling — open source, local-first, pour cyclistes exigeants.*
