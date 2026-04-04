# mTLS — Stack pré-prod MCP

Chiffrement et authentification mutuelle entre Claude Desktop (Mac) et le MCP server (NAS).

```
PROD (inchangée) :
  Claude Desktop → supergateway → http://192.168.1.78:3000/sse

PRÉ-PROD mTLS :
  Claude Desktop → supergateway → http://localhost:3001/sse
                                        ↓
                                  stunnel (Mac :3001)
                                        ↓ mTLS
                                  Nginx (NAS :8443)
                                        ↓
                                  mcp-server-mtls (:3000 interne)
```

---

## 1. Générer les certificats (sur le Mac)

```bash
bash docker/mtls/generate-certs.sh ~/.magma-certs 192.168.1.78
```

Résultat dans `~/.magma-certs/` :

| Fichier | Usage | Destination |
|---------|-------|-------------|
| `ca.crt` | Autorité de certification | Mac + NAS |
| `ca.key` | Clé privée CA | Mac uniquement (ne pas copier) |
| `server.crt` | Cert serveur | NAS |
| `server.key` | Clé privée serveur | NAS |
| `client.crt` | Cert client | Mac |
| `client.key` | Clé privée client | Mac |

## 2. Copier les certs serveur sur le NAS

```bash
# Créer le répertoire sur le NAS
ssh admin@192.168.1.78 "mkdir -p /volume1/docker/magma-cycling/certs"

# Copier les 3 fichiers nécessaires côté serveur
scp ~/.magma-certs/ca.crt ~/.magma-certs/server.crt ~/.magma-certs/server.key \
    admin@192.168.1.78:/volume1/docker/magma-cycling/certs/
```

> Adapter le chemin `/volume1/docker/magma-cycling/certs` selon votre configuration NAS.

## 3. Déployer la stack pré-prod dans Portainer

1. Ouvrir Portainer : `https://192.168.1.78:9443`
2. **Stacks → Add stack** → nom : `magma-cycling-mtls`
3. Coller le contenu de `docker/docker-compose.mtls.yml`
4. Configurer les variables d'environnement :

| Variable | Valeur |
|----------|--------|
| `TRAINING_DATA_PATH` | Même valeur que la stack prod |
| `MTLS_CERTS_PATH` | `/volume1/docker/magma-cycling/certs` |

5. Cliquer **Deploy the stack**
6. Vérifier que les 2 containers démarrent (`magma-mcp-server-mtls`, `magma-nginx-mtls`)

> Le fichier `stack.env` doit être présent dans le répertoire de la stack (même contenu que la prod).

## 4. Installer stunnel sur le Mac

```bash
brew install stunnel
```

## 5. Lancer stunnel

```bash
stunnel docker/stunnel/stunnel.conf
```

Vérifier qu'il écoute :

```bash
lsof -i :3001
```

> Pour arrêter stunnel : `pkill stunnel`

## 6. Tester la connexion

### Test 1 — mTLS enforced (sans cert client → refusé)

```bash
curl -v --cacert ~/.magma-certs/ca.crt https://192.168.1.78:8443/sse
# Attendu : erreur SSL (400 No required SSL certificate was sent)
```

### Test 2 — mTLS avec cert client

```bash
curl -v \
  --cert ~/.magma-certs/client.crt \
  --key ~/.magma-certs/client.key \
  --cacert ~/.magma-certs/ca.crt \
  https://192.168.1.78:8443/sse
# Attendu : réponse SSE du MCP server
```

### Test 3 — Via stunnel (tunnel local)

```bash
curl -v http://localhost:3001/sse
# Attendu : réponse SSE (stunnel gère le mTLS de manière transparente)
```

## 7. Repointer Claude Desktop

Modifier la config Claude Desktop pour utiliser le tunnel mTLS :

```
npx supergateway --sse http://localhost:3001/sse
```

Au lieu de :

```
npx supergateway --sse http://192.168.1.78:3000/sse
```

Redémarrer Claude Desktop pour appliquer.

## 8. Validation bout en bout

Checklist dans Claude Desktop :
- [ ] Les outils MCP apparaissent dans la liste
- [ ] Un appel outil fonctionne (ex: `get-weekly-plan`)
- [ ] Les logs nginx confirment le mTLS : `docker logs magma-nginx-mtls`

## 9. Basculement prod (quand validé)

Une fois la pré-prod validée :

1. Mettre à jour `docker-compose.yml` (prod) pour ajouter le nginx-mtls en remplacement du port 3000 exposé
2. Repointer Claude Desktop définitivement sur `localhost:3001`
3. Fermer le port 3000 sur le NAS (plus de HTTP en clair)
4. Supprimer la stack `magma-cycling-mtls` (absorbée par la prod)

---

## Fichiers de référence

| Fichier | Rôle |
|---------|------|
| `docker/docker-compose.mtls.yml` | Stack pré-prod isolée |
| `docker/docker-compose.yml` | Stack prod (inchangée) |
| `docker/nginx/nginx-mtls.conf` | Config nginx pour la pré-prod (upstream = `mcp-server-mtls`) |
| `docker/nginx/nginx.conf` | Config nginx originale (upstream = `mcp-server`) |
| `docker/mtls/generate-certs.sh` | Générateur de certificats |
| `docker/stunnel/stunnel.conf` | Config stunnel côté Mac |

## Sécurité

- **Ne jamais commiter les fichiers `.key`** — ils sont dans `~/.magma-certs/` (hors repo)
- Les certs ont une durée de vie de 825 jours (serveur/client) et 10 ans (CA)
- TLS 1.3 uniquement (pas de fallback TLS 1.2)
- `verifyChain = yes` dans stunnel : vérifie toute la chaîne de certificats
