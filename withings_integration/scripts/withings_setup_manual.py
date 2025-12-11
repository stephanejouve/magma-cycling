# -*- coding: utf-8 -*-
"""
Script de configuration Withings OAuth - METHODE MANUELLE
Plus simple : pas besoin de serveur local ni ngrok
"""

import os
import sys
import json
import webbrowser

# Ajouter le repertoire parent au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from withings_integration import WithingsIntegration

# Charger configuration
load_dotenv('.env.withings')

CLIENT_ID = os.getenv('WITHINGS_CLIENT_ID')
CLIENT_SECRET = os.getenv('WITHINGS_CLIENT_SECRET')
CALLBACK_URI = os.getenv('WITHINGS_CALLBACK_URI')

if not CLIENT_ID or not CLIENT_SECRET:
    print("\nErreur: Variables d'environnement manquantes dans .env.withings")
    exit(1)

def main():
    """Processus d'authentification manuelle"""
    print("\n" + "="*70)
    print(" CONFIGURATION WITHINGS - AUTHENTIFICATION MANUELLE ".center(70, "="))
    print("="*70 + "\n")

    print("Cette methode est plus simple car elle ne necessite pas de serveur local.\n")

    # Initialiser l'integration
    withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)

    # Obtenir l'URL d'autorisation
    print("Etape 1: Generation de l'URL d'autorisation...")
    auth_url = withings.get_authorization_url()

    print("\n" + "="*70)
    print("Etape 2: Autorisation Withings")
    print("="*70 + "\n")

    print("1. Le navigateur va s'ouvrir automatiquement")
    print("2. Connectez-vous a votre compte Withings")
    print("3. Autorisez l'application")
    print("4. Vous serez redirige vers une page d'erreur (NORMAL)")
    print("5. Copiez le CODE dans l'URL de la page d'erreur\n")

    print("Exemple d'URL apres redirection:")
    print("https://...ngrok.../callback?code=VOTRE_CODE&state=...\n")
    print("Copiez seulement la partie: VOTRE_CODE\n")

    input("Appuyez sur Entree pour ouvrir le navigateur...")

    # Ouvrir le navigateur
    print("\nOuverture du navigateur...")
    webbrowser.open(auth_url)

    print("\n" + "="*70)
    print("Etape 3: Recuperation du code")
    print("="*70 + "\n")

    # Demander le code manuellement
    authorization_code = input("Collez le code d'autorisation ici: ").strip()

    if not authorization_code:
        print("\nErreur: Aucun code fourni")
        exit(1)

    print("\n" + "="*70)
    print("Code recu ! Echange contre les tokens d'acces...")
    print("="*70 + "\n")

    try:
        # Echanger le code contre des credentials
        credentials = withings.authenticate_with_code(authorization_code)

        # Sauvegarder les credentials
        credentials_file = 'withings_credentials.json'
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)

        print(f"✓ Credentials sauvegardes dans '{credentials_file}'")

        # Test rapide
        print("\n" + "="*70)
        print("TEST DE CONNEXION")
        print("="*70 + "\n")

        withings.load_credentials(credentials)

        # Tester poids
        try:
            weight = withings.get_latest_weight()
            if weight:
                print(f"✓ Poids recupere: {weight['weight_kg']}kg ({weight['date']})")
            else:
                print("i Aucune donnee de poids recente")
        except Exception as e:
            print(f"⚠ Erreur poids: {e}")

        # Tester sommeil
        try:
            sleep = withings.get_last_night_sleep()
            if sleep:
                print(f"✓ Sommeil recupere: {sleep['total_sleep_hours']}h ({sleep['date']})")
                print(f"  Score: {sleep['sleep_score']}/100")
            else:
                print("i Aucune donnee de sommeil recente")
        except Exception as e:
            print(f"⚠ Erreur sommeil: {e}")

        print("\n" + "="*70)
        print("CONFIGURATION TERMINEE !")
        print("="*70)
        print("\nVous pouvez maintenant utiliser:")
        print("  python withings_integration/scripts/withings_sync.py sync")
        print("\nLes credentials se rafraichissent automatiquement.\n")

    except Exception as e:
        print(f"\nErreur lors de l'authentification: {e}")
        print("\nVerifiez que:")
        print("- Le code est correct et complet")
        print("- Le code n'a pas expire (valide quelques minutes)")
        print("- Le callback URL dans le Developer Dashboard correspond")
        exit(1)


if __name__ == "__main__":
    main()
