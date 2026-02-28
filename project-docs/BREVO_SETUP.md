# Configuration Brevo pour Daily Sync Email

Ce guide explique comment configurer l'envoi automatique d'emails quotidiens via Brevo (service français d'email transactionnel).

## 1. Créer un compte Brevo

1. Aller sur [https://www.brevo.com](https://www.brevo.com)
2. Créer un compte gratuit (300 emails/jour inclus)
3. Aucune carte bancaire requise pour le plan gratuit

## 2. Obtenir votre clé API

1. Se connecter à votre compte Brevo
2. Aller dans **Paramètres** (Settings) → **Clés API** (API Keys)
3. Cliquer sur **Créer une nouvelle clé API**
4. Donner un nom (ex: "Training Logs Daily Sync")
5. Copier la clé générée (format: `xkeysib-...`)

## 3. Vérifier votre adresse email d'expéditeur

1. Aller dans **Paramètres** → **Expéditeurs et Domaines** (Senders & Domains)
2. Cliquer sur **Ajouter un expéditeur**
3. Entrer votre email (ex: `training@votredomaine.com` ou votre email personnel)
4. Vérifier l'email (cliquer sur le lien reçu par email)
5. ⚠️ Important: Cet email doit être vérifié pour pouvoir envoyer

## 4. Configuration .env

Ajouter les variables suivantes dans votre fichier `.env` :

```bash
# Brevo API Configuration
BREVO_API_KEY=xkeysib-votre-cle-api-ici
EMAIL_TO=votre-email@example.com
EMAIL_FROM=training@votredomaine.com
EMAIL_FROM_NAME="Training Logs"
```

**Variables expliquées** :
- `BREVO_API_KEY`: Clé API obtenue à l'étape 2
- `EMAIL_TO`: Votre adresse email (destinataire des rapports)
- `EMAIL_FROM`: Email vérifié dans Brevo (expéditeur)
- `EMAIL_FROM_NAME`: Nom affiché comme expéditeur (optionnel)

## 5. Test de configuration

Tester l'envoi d'un rapport :

```bash
# Test avec rapport S076 (15 janvier)
poetry run daily-sync --date 2026-01-15 --week-id S076 --start-date 2026-01-13 --send-email
```

Vérifier dans la console :
```
📧 Envoi email via Brevo...
  ✅ Email envoyé avec succès (ID: <message-id>)
  📬 Destinataire: votre-email@example.com
```

## 6. Automatisation avec Cron

Pour recevoir automatiquement le rapport chaque soir à 22h :

```bash
# Éditer crontab
crontab -e

# Ajouter (adapter les chemins) :
0 22 * * * cd /Users/stephanejouve/magma-cycling && /usr/local/bin/poetry run daily-sync --date $(date +\%Y-\%m-\%d) --week-id S077 --start-date 2026-01-19 --send-email
```

## 7. Format de l'email

L'email envoyé contient :
- **Sujet**: 📊 Rapport Quotidien Training - DD/MM/YYYY
- **Format HTML**: Markdown converti en HTML avec CSS styling professionnel
- **Format texte**: Markdown brut en fallback
- **Contenu**:
  - Activités complétées (TSS, durée, type)
  - Modifications planning (suppressions, ajouts, modifications avec diff)

## 8. Limites et Quotas

**Plan Gratuit Brevo**:
- ✅ 300 emails/jour
- ✅ API illimitée
- ✅ 100,000 contacts
- ✅ Support 24/7

**Pour notre usage** :
- 1 email/jour = largement dans le quota gratuit
- Possibilité d'upgrade à 15$/mois pour 20,000 emails si besoin

## 9. Dépannage

### Erreur "BREVO_API_KEY manquant"
→ Vérifier que `.env` contient bien `BREVO_API_KEY=...`

### Erreur "EMAIL_FROM manquant"
→ Ajouter `EMAIL_FROM=...` dans `.env` avec un email vérifié dans Brevo

### Erreur API "Unauthorized"
→ Vérifier que la clé API est correcte et active dans Brevo

### Email non reçu
→ Vérifier :
1. L'email expéditeur est vérifié dans Brevo
2. Consulter les logs Brevo (Statistiques → Emails transactionnels)
3. Vérifier le dossier spam

## 10. Sécurité

⚠️ **Important** :
- Ne jamais committer le fichier `.env` dans Git
- Le `.env` contient des credentials sensibles
- `.gitignore` doit inclure `.env`

## Ressources

- [Documentation Brevo API](https://developers.brevo.com/docs)
- [Tarifs Brevo 2026](https://www.brevo.com/pricing/)
- [Support Brevo](https://help.brevo.com/)
