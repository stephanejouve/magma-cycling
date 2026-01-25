# Configuration DNS Brevo pour alliancejr.eu
## Instructions Étape par Étape

**Date:** 25 Janvier 2026
**Domaine:** alliancejr.eu
**Gestionnaire:** Gandi (supposé)

---

## 📋 Enregistrements à Ajouter

### 1. Code Brevo (Nouveau - TXT)
```
Type: TXT
Nom: @
Valeur: brevo-code:7103aafe60a52f5a6216068a53dcf4a7
TTL: 10800 (ou laisser défaut)
```

### 2. DKIM 1 (Nouveau - CNAME)
```
Type: CNAME
Nom: brevo1._domainkey
Valeur: b1.alliancejr-eu.dkim.brevo.com
TTL: 10800 (ou laisser défaut)
```

### 3. DKIM 2 (Nouveau - CNAME)
```
Type: CNAME
Nom: brevo2._domainkey
Valeur: b2.alliancejr-eu.dkim.brevo.com
TTL: 10800 (ou laisser défaut)
```

### 4. DMARC (Nouveau - TXT)
```
Type: TXT
Nom: _dmarc
Valeur: v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
TTL: 10800 (ou laisser défaut)
```

### 5. SPF (MODIFIER L'EXISTANT - TXT)
```
Type: TXT
Nom: @
Valeur ACTUELLE: v=spf1 include:icloud.com ~all
Valeur NOUVELLE: v=spf1 include:icloud.com include:spf.brevo.com ~all
TTL: 10800 (garder)
```

**⚠️ IMPORTANT:** Pour SPF, MODIFIER l'enregistrement existant, ne PAS en créer un nouveau!

---

## 🎯 Instructions Gandi (Si c'est ton gestionnaire)

### Accéder à la Zone DNS

1. **Connexion Gandi:**
   - URL: https://admin.gandi.net
   - Login avec tes identifiants

2. **Naviguer vers DNS:**
   ```
   Domaines → alliancejr.eu → Enregistrements DNS
   ```

### Ajouter Enregistrement 1: Code Brevo

3. **Cliquer "Ajouter"**

4. **Remplir formulaire:**
   ```
   Type: TXT
   Nom: @
   Valeur: brevo-code:7103aafe60a52f5a6216068a53dcf4a7
   ```

5. **Cliquer "Ajouter"**

**Note:** Tu auras maintenant 3 enregistrements TXT sur @ (apple-domain, SPF, brevo-code). C'est normal!

### Ajouter Enregistrement 2: DKIM 1

6. **Cliquer "Ajouter"**

7. **Remplir formulaire:**
   ```
   Type: CNAME
   Nom: brevo1._domainkey
   Valeur: b1.alliancejr-eu.dkim.brevo.com
   ```

8. **Cliquer "Ajouter"**

### Ajouter Enregistrement 3: DKIM 2

9. **Cliquer "Ajouter"**

10. **Remplir formulaire:**
    ```
    Type: CNAME
    Nom: brevo2._domainkey
    Valeur: b2.alliancejr-eu.dkim.brevo.com
    ```

11. **Cliquer "Ajouter"**

### Ajouter Enregistrement 4: DMARC

12. **Cliquer "Ajouter"**

13. **Remplir formulaire:**
    ```
    Type: TXT
    Nom: _dmarc
    Valeur: v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
    ```

14. **Cliquer "Ajouter"**

### Modifier Enregistrement 5: SPF (CRITIQUE)

15. **Trouver l'enregistrement existant:**
    ```
    @ TXT "v=spf1 include:icloud.com ~all"
    ```

16. **Cliquer sur l'icône "Modifier" (crayon) de cet enregistrement**

17. **Modifier la valeur:**
    ```
    ANCIEN: v=spf1 include:icloud.com ~all
    NOUVEAU: v=spf1 include:icloud.com include:spf.brevo.com ~all
    ```

18. **Enregistrer la modification**

---

## 🔍 Résultat Final Zone DNS

Après modifications, tu devrais avoir:

```
# Enregistrements @ (racine)
@    A      10800    92.157.168.204
@    MX     10800    10 mx01.mail.icloud.com.
@    MX     10800    10 mx02.mail.icloud.com.
@    TXT    10800    "apple-domain=uj4Aa0brSh7RwvtO"
@    TXT    10800    "v=spf1 include:icloud.com include:spf.brevo.com ~all"  ← MODIFIÉ
@    TXT    10800    "brevo-code:7103aafe60a52f5a6216068a53dcf4a7"  ← NOUVEAU

# DKIM (existant iCloud)
sig1._domainkey    CNAME    10800    sig1.dkim.alliancejr.eu.at.icloudmailadmin.com.

# DKIM Brevo (nouveaux)
brevo1._domainkey  CNAME    10800    b1.alliancejr-eu.dkim.brevo.com  ← NOUVEAU
brevo2._domainkey  CNAME    10800    b2.alliancejr-eu.dkim.brevo.com  ← NOUVEAU

# DMARC (nouveau)
_dmarc             TXT      10800    "v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"  ← NOUVEAU

# Autres (inchangés)
_180a56cfd5bb2c88cf865bb6971ebc4e    CNAME    ...
_dcfd7e2c05db79596751397761ab0fe5    CNAME    ...
nas                                  A         ...
www                                  A         ...
```

---

## ⏳ Attendre Propagation DNS

**Délai:** 15 minutes à 4 heures (généralement 1-2h)

### Vérifier Propagation

```bash
# Code Brevo
dig TXT alliancejr.eu +short | grep brevo-code

# DKIM 1
dig CNAME brevo1._domainkey.alliancejr.eu +short

# DKIM 2
dig CNAME brevo2._domainkey.alliancejr.eu +short

# DMARC
dig TXT _dmarc.alliancejr.eu +short

# SPF (doit montrer icloud ET brevo)
dig TXT alliancejr.eu +short | grep spf
```

**Résultats attendus:**
```
# Code Brevo
"brevo-code:7103aafe60a52f5a6216068a53dcf4a7"

# DKIM 1
b1.alliancejr-eu.dkim.brevo.com.

# DKIM 2
b2.alliancejr-eu.dkim.brevo.com.

# DMARC
"v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"

# SPF
"v=spf1 include:icloud.com include:spf.brevo.com ~all"
```

---

## ✅ Valider dans Brevo

1. **Retourner sur Brevo:**
   ```
   Settings → Senders & IP → Domains → alliancejr.eu
   ```

2. **Cliquer "Check Authentication" ou "Verify"**

3. **Brevo vérifie les 4 enregistrements:**
   - ✅ Code Brevo: Verified
   - ✅ DKIM 1: Authenticated
   - ✅ DKIM 2: Authenticated
   - ✅ DMARC: Configured

4. **Status domaine devient "Verified" ✅**

---

## 🧪 Tester l'Envoi

### Test depuis le Projet

```bash
# Tester avec daily-sync
poetry run daily-sync --send-email --week-id S078

# Vérifier les logs
tail -f ~/Library/Logs/cyclisme-daily-sync.log
```

### Configurer EMAIL_FROM

Dans ton `.env`:
```bash
EMAIL_FROM=noreply@alliancejr.eu
EMAIL_FROM_NAME=Training Logs
EMAIL_TO=ton.email.personnel@example.com
```

---

## 📋 Checklist

### Configuration DNS
- [ ] Code Brevo ajouté (@ TXT)
- [ ] DKIM 1 ajouté (brevo1._domainkey CNAME)
- [ ] DKIM 2 ajouté (brevo2._domainkey CNAME)
- [ ] DMARC ajouté (_dmarc TXT)
- [ ] SPF modifié (@ TXT avec include:spf.brevo.com)

### Validation
- [ ] Attendre propagation DNS (1-4h)
- [ ] Vérifier avec commandes `dig`
- [ ] Valider dans Brevo (status "Verified")
- [ ] Email test envoyé et reçu
- [ ] Headers email vérifiés (spf=pass, dkim=pass)

---

## 🐛 Troubleshooting

### "Domain not verified" après 4h

**Vérifier SPF:**
```bash
dig TXT alliancejr.eu +short | grep spf
```

Doit contenir `include:spf.brevo.com`

### "DKIM not found"

**Vérifier CNAME:**
```bash
dig CNAME brevo1._domainkey.alliancejr.eu
```

Doit pointer vers `b1.alliancejr-eu.dkim.brevo.com`

### Emails toujours en spam

- Attendre 24-48h (réputation domaine neuve)
- Vérifier headers email (Authentication-Results)
- Tester avec Mail-Tester: https://www.mail-tester.com

---

## 📌 Notes Importantes

1. **iCloud Mail non affecté:**
   - Réception emails iCloud fonctionne normalement
   - DKIM iCloud (sig1._domainkey) reste actif
   - SPF autorise iCloud ET Brevo

2. **Configuration hybride:**
   - Recevoir: iCloud Mail (MX icloud.com)
   - Envoyer auto: Brevo (noreply@alliancejr.eu)

3. **Sécurité:**
   - Code Brevo secret (ne pas partager)
   - DKIM keys gérées par Brevo
   - DMARC en mode surveillance (p=none)

---

**Créé:** 25 Janvier 2026
**Domaine:** alliancejr.eu
**Status:** Prêt à configurer
