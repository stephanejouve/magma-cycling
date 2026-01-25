# Configuration DKIM/SPF pour Brevo Email
## Guide Configuration Gestionnaire de Domaine

**Date:** 25 Janvier 2026
**Objectif:** Authentifier les emails envoyés via Brevo avec ton propre domaine
**Durée:** 15-30 minutes

---

## 🎯 Pourquoi DKIM/SPF ?

**Sans DKIM/SPF:**
- Emails marqués comme spam ❌
- Délivrabilité faible (~50-60%)
- Gmail/Outlook bloquent ou filtrent
- `EMAIL_FROM=noreply@tondomaine.com` → REJETÉ

**Avec DKIM/SPF:**
- Emails authentifiés ✅
- Délivrabilité excellente (~95%+)
- Inbox direct (pas spam)
- Ton domaine validé et de confiance

---

## 📋 Prérequis

1. ✅ Compte Brevo créé ([brevo.com](https://www.brevo.com))
2. ✅ API Key Brevo générée (déjà dans `.env`)
3. ✅ Accès au gestionnaire DNS de ton domaine
4. ⚠️ Nom du domaine à authentifier (ex: `mondomaine.com`)

**Quel domaine utilises-tu pour `EMAIL_FROM` ?**

---

## 🚀 Étape 1: Obtenir les Enregistrements DNS Brevo

### A. Connexion Brevo

1. **Aller sur Brevo:**
   - URL: https://app.brevo.com
   - Login avec tes identifiants

2. **Naviguer vers Configuration:**
   ```
   Settings (⚙️ en haut à droite)
   → Senders & IP
   → Domains
   ```

### B. Ajouter Ton Domaine

3. **Cliquer "Add a Domain":**
   - Entrer ton domaine: `mondomaine.com` (sans www, sans https://)
   - Cliquer "Add"

4. **Brevo génère automatiquement 3 enregistrements DNS:**

   **Enregistrement 1: DKIM (Authentification)**
   ```
   Type: TXT
   Host: mail._domainkey.mondomaine.com
   Valeur: v=DKIM1; k=rsa; p=MIGfMA0GCSqGS... (longue clé publique)
   TTL: 3600
   ```

   **Enregistrement 2: SPF (Autorisation serveurs)**
   ```
   Type: TXT
   Host: mondomaine.com (ou @)
   Valeur: v=spf1 include:spf.brevo.com ~all
   TTL: 3600
   ```

   **Enregistrement 3: DMARC (Politique) - Optionnel**
   ```
   Type: TXT
   Host: _dmarc.mondomaine.com
   Valeur: v=DMARC1; p=none; rua=mailto:ton.email@example.com
   TTL: 3600
   ```

5. **Copier ces 3 enregistrements** (Brevo les affiche dans une interface)

---

## 🔧 Étape 2: Configurer Ton Gestionnaire DNS

**Gestionnaires courants:**
- OVH
- Gandi
- Cloudflare
- GoDaddy
- Google Domains
- Namecheap

### Instructions Génériques (tous gestionnaires)

#### A. Accéder à la Zone DNS

1. **Connexion gestionnaire domaine**
2. **Trouver section DNS:**
   - OVH: "Noms de domaine" → Ton domaine → "Zone DNS"
   - Gandi: "Domaines" → Ton domaine → "Enregistrements DNS"
   - Cloudflare: Ton domaine → "DNS" → "Records"

#### B. Ajouter Enregistrement DKIM

3. **Cliquer "Ajouter un enregistrement" ou "Add Record"**

4. **Remplir champs DKIM:**
   ```
   Type: TXT
   Nom/Host: mail._domainkey
   Valeur/Value: (coller la clé DKIM de Brevo, commence par "v=DKIM1; k=rsa; p=...")
   TTL: 3600 (ou laisser par défaut)
   ```

   **⚠️ Important:**
   - Certains gestionnaires ajoutent automatiquement `.mondomaine.com`
   - Si c'est le cas, mettre juste `mail._domainkey` (sans le domaine)
   - Sinon, mettre `mail._domainkey.mondomaine.com` (avec le domaine)

5. **Enregistrer/Sauvegarder**

#### C. Ajouter Enregistrement SPF

6. **Ajouter un 2e enregistrement:**
   ```
   Type: TXT
   Nom/Host: @ (ou laisser vide, ou "mondomaine.com")
   Valeur/Value: v=spf1 include:spf.brevo.com ~all
   TTL: 3600
   ```

   **⚠️ Si tu as déjà un enregistrement SPF:**
   - Ne PAS créer un 2e enregistrement SPF (1 seul autorisé)
   - MODIFIER l'existant pour ajouter `include:spf.brevo.com`
   - Exemple existant: `v=spf1 include:_spf.google.com ~all`
   - Nouveau: `v=spf1 include:_spf.google.com include:spf.brevo.com ~all`

7. **Enregistrer/Sauvegarder**

#### D. Ajouter Enregistrement DMARC (Optionnel mais recommandé)

8. **Ajouter un 3e enregistrement:**
   ```
   Type: TXT
   Nom/Host: _dmarc
   Valeur/Value: v=DMARC1; p=none; rua=mailto:ton.email@example.com
   TTL: 3600
   ```

   **Explications politique DMARC:**
   - `p=none` : Surveillance seulement (recommandé début)
   - `p=quarantine` : Mettre en spam si échec (après validation)
   - `p=reject` : Rejeter si échec (production, après tests)
   - `rua=mailto:...` : Recevoir rapports agrégés

9. **Enregistrer/Sauvegarder**

---

## ⏳ Étape 3: Attendre Propagation DNS

**Délai propagation:** 15 minutes à 48 heures (généralement 1-4h)

### Vérifier Propagation DNS

**Commandes terminal:**

```bash
# Vérifier DKIM
dig TXT mail._domainkey.mondomaine.com +short

# Vérifier SPF
dig TXT mondomaine.com +short | grep spf

# Vérifier DMARC
dig TXT _dmarc.mondomaine.com +short
```

**Résultats attendus:**
- DKIM: `"v=DKIM1; k=rsa; p=MIGfMA0GCS..."`
- SPF: `"v=spf1 include:spf.brevo.com ~all"`
- DMARC: `"v=DMARC1; p=none; rua=mailto:..."`

**Outils en ligne:**
- MXToolbox: https://mxtoolbox.com/SuperTool.aspx
- Google Admin Toolbox: https://toolbox.googleapps.com/apps/dig/

---

## ✅ Étape 4: Valider dans Brevo

1. **Retourner sur Brevo:**
   ```
   Settings → Senders & IP → Domains
   ```

2. **Cliquer sur ton domaine**

3. **Cliquer "Verify" ou "Check DNS"**

4. **Brevo vérifie les 3 enregistrements:**
   - ✅ DKIM: Authenticated
   - ✅ SPF: Configured
   - ✅ DMARC: Configured (si ajouté)

5. **Status domaine devient "Verified" ✅**

---

## 🧪 Étape 5: Tester l'Envoi Email

### Test depuis le Projet

```bash
# Tester avec daily-sync (envoie un email de test)
poetry run daily-sync --send-email --week-id S078

# Vérifier les logs
tail -f ~/Library/Logs/cyclisme-daily-sync.log
```

### Vérifier Authentification Email Reçu

1. **Ouvrir l'email reçu dans Gmail/Outlook**

2. **Afficher les headers complets:**
   - Gmail: Ouvrir email → ⋮ (menu) → "Show original"
   - Outlook: Ouvrir email → File → Properties → Internet headers

3. **Chercher lignes d'authentification:**
   ```
   Authentication-Results: spf=pass smtp.mailfrom=mondomaine.com;
       dkim=pass header.d=mondomaine.com;
       dmarc=pass (policy=none) header.from=mondomaine.com
   ```

4. **Résultat attendu:**
   - `spf=pass` ✅
   - `dkim=pass` ✅
   - `dmarc=pass` ✅

---

## 🐛 Troubleshooting

### Problème 1: "DKIM record not found"

**Causes possibles:**
- Propagation DNS pas encore complète (attendre 1-4h)
- Mauvais nom host (vérifier `mail._domainkey` vs `mail._domainkey.mondomaine.com`)
- Enregistrement mal copié (vérifier valeur complète)

**Solutions:**
```bash
# Vérifier avec dig
dig TXT mail._domainkey.mondomaine.com

# Si vide, attendre propagation
# Si mauvais, corriger dans gestionnaire DNS
```

### Problème 2: "SPF record conflict"

**Cause:** Plusieurs enregistrements SPF (interdit)

**Solution:**
```bash
# Lister tous les TXT du domaine
dig TXT mondomaine.com

# Identifier les SPF multiples
# Fusionner en UN SEUL enregistrement SPF
```

### Problème 3: "Authentication failed" lors envoi

**Causes possibles:**
- Domaine pas vérifié dans Brevo
- `EMAIL_FROM` utilise un domaine différent
- API Key invalide

**Solutions:**
1. Vérifier `EMAIL_FROM` dans `.env` correspond au domaine configuré
2. Re-vérifier domaine dans Brevo (Settings → Domains)
3. Tester API Key dans Brevo dashboard

### Problème 4: Emails tombent en spam malgré DKIM/SPF

**Causes possibles:**
- DMARC policy trop stricte (`p=reject` trop tôt)
- Réputation domaine neuve (normal début)
- Contenu email ressemble à spam

**Solutions:**
1. Commencer avec `p=none` pour DMARC
2. Envoyer petit volume initialement (10-20 emails/jour)
3. Éviter mots-clés spam ("FREE", "CLICK HERE", etc.)
4. Améliorer contenu (texte + HTML, images optimisées)

---

## 📊 Vérification Délivrabilité

### Outils Recommandés

**1. Mail-Tester:**
- URL: https://www.mail-tester.com
- Envoyer email test à adresse fournie
- Score /10 (viser 9-10/10)

**2. MXToolbox:**
- URL: https://mxtoolbox.com/emailhealth/
- Vérifier santé domaine
- Blacklists, DKIM, SPF, DMARC

**3. Google Postmaster Tools:**
- URL: https://postmaster.google.com
- Surveiller réputation Gmail
- Taux spam, authentification

---

## 🔐 Sécurité & Best Practices

### Configuration Recommandée Production

```
# SPF strict (après validation)
v=spf1 include:spf.brevo.com -all

# DMARC strict (après 2-4 semaines)
v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc@mondomaine.com

# DKIM rotation
Regénérer clé DKIM tous les 6-12 mois (Brevo permet rotation)
```

### Monitoring Continue

```bash
# Ajouter surveillance cron DNS
# Alerte si DKIM/SPF changent (attaque DNS possible)

# Analyser rapports DMARC
# Identifier sources email non-autorisées
```

---

## 📝 Checklist Complète

### Configuration Initiale
- [ ] Compte Brevo créé
- [ ] Domaine ajouté dans Brevo
- [ ] Enregistrements DNS copiés (DKIM, SPF, DMARC)
- [ ] Enregistrements ajoutés dans gestionnaire DNS
- [ ] Attendre propagation DNS (1-4h)
- [ ] Vérifier propagation avec `dig`
- [ ] Valider domaine dans Brevo (status "Verified")

### Tests
- [ ] Email test envoyé (`daily-sync --send-email`)
- [ ] Email reçu (check inbox + spam)
- [ ] Headers vérifiés (spf=pass, dkim=pass, dmarc=pass)
- [ ] Score Mail-Tester ≥9/10
- [ ] Aucun blacklist (MXToolbox)

### Production
- [ ] `EMAIL_FROM` configuré avec domaine vérifié
- [ ] `.env` à jour (BREVO_API_KEY, EMAIL_FROM, EMAIL_TO)
- [ ] Daily-sync fonctionne avec `--send-email`
- [ ] Monitoring DMARC rapports activé
- [ ] Documentation projet mise à jour

---

## 🔗 Ressources

### Documentation Officielle
- **Brevo DKIM Setup:** https://help.brevo.com/hc/en-us/articles/209467485
- **SPF Record Syntax:** https://tools.ietf.org/html/rfc7208
- **DMARC Guide:** https://dmarc.org/overview/

### Outils Validation
- **Mail-Tester:** https://www.mail-tester.com
- **MXToolbox:** https://mxtoolbox.com
- **DMARC Analyzer:** https://dmarcian.com

### Gestionnaires DNS Guides
- **OVH:** https://docs.ovh.com/fr/domains/editer-ma-zone-dns/
- **Gandi:** https://docs.gandi.net/fr/domaines/records/
- **Cloudflare:** https://developers.cloudflare.com/dns/

---

## 💡 Prochaines Étapes

Après configuration DKIM/SPF:

1. **Tester régulièrement:**
   ```bash
   poetry run daily-sync --send-email --week-id S078
   ```

2. **Surveiller délivrabilité:**
   - Vérifier emails arrivent inbox (pas spam)
   - Analyser rapports DMARC hebdomadaires
   - Ajuster politique DMARC progressivement

3. **Documenter configuration:**
   - Noter enregistrements DNS dans gestionnaire mots de passe
   - Archiver configuration Brevo
   - Mettre à jour README projet si nécessaire

---

**Besoin d'aide ?**

Si blocage sur une étape, fournis:
1. Nom du gestionnaire DNS utilisé (OVH, Gandi, etc.)
2. Nom du domaine à configurer
3. Screenshot ou logs d'erreur Brevo
4. Résultat commande `dig TXT mail._domainkey.mondomaine.com`

---

**Créé:** 25 Janvier 2026
**Pour:** Configuration emails daily-sync via Brevo
**Status:** Guide complet - Prêt à suivre
