# Magma Cycling — Installation Mac pas a pas

Guide pour installer le coach IA cyclisme sur ton Mac.
Temps estime : 15-20 minutes. Aucune connaissance technique requise.

---

## Ce qu'il te faut avant de commencer

- [ ] Un Mac sous macOS 12 (Monterey) ou plus recent
- [ ] Un compte Intervals.icu (gratuit) avec tes activites synchronisees
- [ ] Ton **identifiant athlete** Intervals.icu (commence par `i`, ex: `i123456`)
- [ ] Ta **cle API** Intervals.icu

> **Ou trouver ta cle API ?**
> Va sur https://intervals.icu > clique sur ton nom en haut a droite >
> **Settings** > **Developer Settings** > **API Key**.
> Si tu n'en as pas, clique "Generate" pour en creer une.
> Copie-la quelque part (bloc-notes), tu en auras besoin a l'etape 5.

---

## Etape 1 — Ouvrir le Terminal

Le Terminal est l'application qui permet de taper des commandes sur Mac.
Pas de panique, tu vas juste copier-coller ce qui suit.

**Comment l'ouvrir :**
1. Appuie sur **Cmd + Espace** (ca ouvre Spotlight, la barre de recherche)
2. Tape **Terminal**
3. Appuie sur **Entree**

Une fenetre noire (ou blanche) s'ouvre avec un curseur qui clignote. C'est la.

> **Astuce** : pour copier-coller dans le Terminal, utilise **Cmd+C** / **Cmd+V**
> comme d'habitude. Colle une commande a la fois, puis appuie sur Entree.

---

## Etape 2 — Installer Homebrew (le "magasin d'apps" du Terminal)

Copie-colle cette commande dans le Terminal et appuie sur Entree :

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

- Le Mac va te demander ton **mot de passe** (celui de ta session Mac). Tape-le et appuie sur Entree. C'est normal que rien ne s'affiche pendant que tu tapes — c'est une securite.
- Ca prend 2-3 minutes. Attends que le curseur revienne.

**Verification :** tape `brew --version` et Entree. Tu dois voir un numero de version (ex: `Homebrew 4.x.x`).

> **Si tu avais deja Homebrew** : cette etape te le dit et ne fait rien de plus. Pas de risque.

> **Sur les Mac Apple Silicon (M1/M2/M3)** : Homebrew peut afficher un message te demandant d'ajouter une ligne a ton profil. Si tu vois un bloc "Next steps", copie-colle les commandes indiquees.

---

## Etape 3 — Installer Python et Git

Toujours dans le Terminal, copie-colle ces commandes **une par une** :

```bash
brew install python@3.12
```

Attends que ca finisse (1-2 minutes), puis :

```bash
brew install git
```

Puis :

```bash
pip3 install poetry
```

**Verification :** tape ces 3 commandes une par une :

```bash
python3 --version
```
> Attendu : `Python 3.12.x` (ou plus recent)

```bash
git --version
```
> Attendu : `git version 2.x.x`

```bash
poetry --version
```
> Attendu : `Poetry (version 1.x.x)` ou `2.x.x`

Si les 3 repondent, c'est bon. Passe a la suite.

---

## Etape 4 — Telecharger et installer Magma Cycling

Copie-colle ces commandes **une par une** :

```bash
git clone https://github.com/stephanejouve/magma-cycling.git ~/magma-cycling
```

> Ca telecharge le projet dans un dossier `magma-cycling` dans ton dossier personnel.

```bash
cd ~/magma-cycling
```

```bash
poetry install
```

> Ca installe les dependances. Attends 1-2 minutes que ca finisse.
> Tu verras defiler des lignes — c'est normal. Attends le retour du curseur.

---

## Etape 5 — Lancer l'assistant de configuration

```bash
cd ~/magma-cycling
poetry run setup
```

L'assistant te guide avec des questions. Voici ce qu'il va te demander :

1. **Identifiant athlete** — tape ton ID Intervals.icu (ex: `i151223`) puis Entree
2. **Cle API** — colle ta cle API puis Entree (le texte ne s'affiche pas, c'est normal — c'est masque par securite)
3. **Prenom, age, poids, FTP** — reponds a chaque question puis Entree. Si tu ne connais pas ta FTP, tape juste Entree (valeur par defaut : 150W)
4. **Coach IA** — tape **1** (Mode manuel) puis Entree, sauf si tu as une cle API Claude ou Mistral
5. L'assistant ecrit ta configuration et **configure Claude Desktop automatiquement**

> **"Connexion echouee"** : verifie que tu as bien copie l'ID athlete ET la cle API.
> L'ID commence par `i`. La cle est une longue chaine de caracteres.

---

## Etape 6 — Installer Claude Desktop

1. Va sur https://claude.ai/download
2. Telecharge la version Mac
3. Ouvre le fichier `.dmg` telecharge
4. Glisse l'icone Claude dans le dossier Applications
5. Ouvre Claude depuis le dossier Applications (ou via Spotlight : Cmd+Espace > "Claude")
6. Cree un compte Anthropic si tu n'en as pas (email + mot de passe, gratuit)

> **Si Claude Desktop etait deja installe** : quitte-le completement avec **Cmd+Q** et relance-le pour qu'il prenne en compte la configuration Magma.

---

## Etape 7 — Verifier que tout fonctionne

1. Dans Claude Desktop, regarde en bas a gauche de la fenetre de chat
2. Tu dois voir une **icone marteau** avec le chiffre correspondant aux outils disponibles
3. Clique dessus — **magma-cycling** doit apparaitre dans la liste

**Test final :** tape dans le chat :

> Montre-moi mon etat d'entrainement actuel

Si l'IA te repond avec tes metriques Intervals.icu (CTL, ATL, TSB...), c'est gagne.

---

## Depannage

### "magma-cycling n'apparait pas dans Claude Desktop"

1. Dans Claude Desktop, va dans **Settings** (icone engrenage)
2. **Developer** > **Edit Config**
3. Un fichier s'ouvre. Tu dois voir :

```json
{
  "mcpServers": {
    "magma-cycling": {
      "command": "poetry",
      "args": ["run", "mcp-server"],
      "cwd": "/Users/TON_NOM/magma-cycling"
    }
  }
}
```

4. Si ce n'est pas la, copie-colle ce bloc (remplace `TON_NOM` par ton nom d'utilisateur Mac — celui qui apparait quand tu tapes `whoami` dans le Terminal)
5. Sauvegarde (Cmd+S), ferme le fichier
6. Quitte Claude Desktop (Cmd+Q) et relance

### "poetry: command not found"

```bash
python3 -m pip install poetry
```

Puis ferme le Terminal et rouvre-le pour que la commande soit reconnue.

### "xcrun: error: invalid active developer path"

Ca veut dire que les outils de dev Apple ne sont pas installes. Tape :

```bash
xcode-select --install
```

Une fenetre apparait, clique "Installer", attends 5-10 minutes, puis reprends a l'etape 3.

### "permission denied" ou "operation not permitted"

Prefixe la commande qui bloque avec `sudo` :

```bash
sudo la-commande-qui-bloque
```

Le Mac te demande ton mot de passe de session.

### Autre blocage

Contacte Stephane — un partage d'ecran de 5 minutes et c'est regle.

---

## Mises a jour futures

Quand une nouvelle version sort, ouvre le Terminal et tape :

```bash
cd ~/magma-cycling
git pull
poetry install
```

Puis relance Claude Desktop (Cmd+Q et rouvre). C'est tout.
