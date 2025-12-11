"""
Script de vérification de l'installation Withings
Vérifie que tous les composants sont correctement configurés
"""

import os
import sys
import json

# Ajouter le repertoire parent au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def check_dependencies():
    """Vérifie que les dépendances Python sont installées"""
    print("\n" + "="*70)
    print("VÉRIFICATION DES DÉPENDANCES")
    print("="*70 + "\n")
    
    required = {
        'withings_api': 'withings-api',
        'requests': 'requests',
        'dotenv': 'python-dotenv'
    }
    
    all_ok = True
    
    for module, package in required.items():
        try:
            if module == 'dotenv':
                import dotenv
            else:
                __import__(module)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MANQUANT")
            all_ok = False
    
    if not all_ok:
        print("\n⚠️  Installez les dépendances manquantes:")
        print("   pip install withings-api requests python-dotenv")
        return False
    
    print("\n✅ Toutes les dépendances sont installées")
    return True


def check_files():
    """Vérifie que les fichiers nécessaires existent"""
    print("\n" + "="*70)
    print("VÉRIFICATION DES FICHIERS")
    print("="*70 + "\n")
    
    required_files = {
        'withings_integration.py': 'Module principal API',
        'withings_setup.py': 'Script de configuration initiale',
        'withings_sync.py': 'Script de synchronisation',
        'README_WITHINGS.md': 'Documentation'
    }
    
    optional_files = {
        'withings_credentials.json': 'Credentials OAuth (créé au setup)',
        '.env.withings': 'Configuration (créé au setup)',
        'withings_demo.py': 'Script de démonstration'
    }
    
    all_ok = True
    
    print("Fichiers obligatoires:")
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"  ✓ {filename:<30} ({description})")
        else:
            print(f"  ✗ {filename:<30} MANQUANT - {description}")
            all_ok = False
    
    print("\nFichiers optionnels:")
    for filename, description in optional_files.items():
        if os.path.exists(filename):
            print(f"  ✓ {filename:<30} ({description})")
        else:
            print(f"  ⚠ {filename:<30} Non créé - {description}")
    
    if not all_ok:
        print("\n✗ Fichiers manquants - Installation incomplète")
        return False
    
    print("\n✅ Tous les fichiers obligatoires sont présents")
    return True


def check_credentials():
    """Vérifie la configuration des credentials"""
    print("\n" + "="*70)
    print("VÉRIFICATION DES CREDENTIALS")
    print("="*70 + "\n")
    
    if not os.path.exists('withings_credentials.json'):
        print("⚠️  Fichier credentials non trouvé")
        print("   Exécutez: python withings_setup.py")
        return False
    
    try:
        with open('withings_credentials.json', 'r') as f:
            creds = json.load(f)
        
        required_keys = ['access_token', 'refresh_token', 'token_expiry', 'userid']
        
        all_keys_present = all(key in creds for key in required_keys)
        
        if all_keys_present:
            print("✓ Fichier credentials valide")
            print(f"  UserID: {creds.get('userid')}")
            print(f"  Token expiry: {creds.get('token_expiry')}")
            return True
        else:
            print("✗ Credentials incomplets")
            missing = [key for key in required_keys if key not in creds]
            print(f"  Clés manquantes: {', '.join(missing)}")
            return False
            
    except json.JSONDecodeError:
        print("✗ Fichier credentials corrompu")
        return False
    except Exception as e:
        print(f"✗ Erreur lecture credentials: {e}")
        return False


def check_gitignore():
    """Vérifie que le .gitignore est correctement configuré"""
    print("\n" + "="*70)
    print("VÉRIFICATION .GITIGNORE")
    print("="*70 + "\n")
    
    sensitive_files = [
        'withings_credentials.json',
        '.env.withings',
        '*.secret'
    ]
    
    if not os.path.exists('.gitignore'):
        print("⚠️  Fichier .gitignore non trouvé")
        print("\nCréation recommandée avec:")
        for pattern in sensitive_files:
            print(f"  {pattern}")
        
        create = input("\nCréer .gitignore maintenant ? (o/n): ").strip().lower()
        if create == 'o':
            with open('.gitignore', 'w') as f:
                f.write("# Withings sensitive files\n")
                for pattern in sensitive_files:
                    f.write(f"{pattern}\n")
            print("✓ .gitignore créé")
            return True
        return False
    
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
    
    all_ok = True
    for pattern in sensitive_files:
        if pattern in gitignore_content:
            print(f"✓ {pattern}")
        else:
            print(f"⚠️  {pattern} - NON PROTÉGÉ")
            all_ok = False
    
    if not all_ok:
        print("\n⚠️  Ajoutez les patterns manquants au .gitignore")
        add = input("Ajouter automatiquement ? (o/n): ").strip().lower()
        if add == 'o':
            with open('.gitignore', 'a') as f:
                f.write("\n# Withings sensitive files\n")
                for pattern in sensitive_files:
                    if pattern not in gitignore_content:
                        f.write(f"{pattern}\n")
            print("✓ Patterns ajoutés au .gitignore")
            return True
    else:
        print("\n✅ .gitignore correctement configuré")
    
    return all_ok


def check_api_connection():
    """Teste la connexion à l'API Withings"""
    print("\n" + "="*70)
    print("TEST DE CONNEXION API")
    print("="*70 + "\n")
    
    if not os.path.exists('withings_credentials.json'):
        print("⚠️  Credentials non trouvés - Skip test API")
        return False
    
    try:
        from withings_integration import WithingsIntegration
        
        # Charger config
        CLIENT_ID = "c5e8820a701242a8708c54ee9fcc83915f02270f2ae0930b9a5917bbb3d21278"
        CLIENT_SECRET = os.getenv('WITHINGS_SECRET', 'dummy')
        CALLBACK_URI = "https://4f3c-2a01-cb14-8513-df00-2031-d098-d697-75c1.ngrok-free.app/auth/withings/callback"
        
        # Charger credentials
        with open('withings_credentials.json', 'r') as f:
            creds = json.load(f)
        
        # Initialiser
        withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)
        withings.load_credentials(creds)
        
        # Test récupération poids
        print("Test récupération poids...")
        weight = withings.get_latest_weight()
        
        if weight:
            print(f"✓ Poids récupéré: {weight['weight_kg']}kg ({weight['date']})")
        else:
            print("⚠️  Aucune donnée de poids (normal si pas de mesure récente)")
        
        # Test récupération sommeil
        print("\nTest récupération sommeil...")
        sleep = withings.get_last_night_sleep()
        
        if sleep:
            print(f"✓ Sommeil récupéré: {sleep['total_sleep_hours']}h ({sleep['date']})")
        else:
            print("⚠️  Aucune donnée de sommeil (normal si pas de mesure récente)")
        
        print("\n✅ Connexion API fonctionnelle")
        return True
        
    except ImportError:
        print("✗ Impossible d'importer withings_integration")
        return False
    except Exception as e:
        print(f"✗ Erreur test API: {e}")
        return False


def main():
    """Exécute toutes les vérifications"""
    print("\n" + "="*70)
    print(" VÉRIFICATION INSTALLATION WITHINGS ".center(70, "="))
    print("="*70)
    
    results = {
        'dependencies': check_dependencies(),
        'files': check_files(),
        'credentials': check_credentials(),
        'gitignore': check_gitignore(),
        'api': check_api_connection()
    }
    
    print("\n" + "="*70)
    print("RÉSUMÉ")
    print("="*70 + "\n")
    
    status_symbols = {True: "✅", False: "✗"}
    
    for check, status in results.items():
        symbol = status_symbols[status]
        print(f"{symbol} {check.capitalize()}")
    
    all_ok = all(results.values())
    
    print("\n" + "="*70)
    
    if all_ok:
        print("✅ INSTALLATION COMPLÈTE ET FONCTIONNELLE")
        print("="*70)
        print("\nProcédure de démarrage:")
        print("1. python withings_sync.py sync      # Synchronisation quotidienne")
        print("2. python withings_sync.py readiness # Vérifier disponibilité")
        print("3. python withings_sync.py summary   # Résumé hebdomadaire")
        print("4. python withings_demo.py           # Démos interactives")
    else:
        print("⚠️  INSTALLATION INCOMPLÈTE")
        print("="*70)
        
        if not results['dependencies']:
            print("\n1. Installer les dépendances:")
            print("   pip install withings-api requests python-dotenv")
        
        if not results['credentials']:
            print("\n2. Configurer l'authentification:")
            print("   python withings_setup.py")
        
        if not results['gitignore']:
            print("\n3. Protéger les fichiers sensibles:")
            print("   Configurer .gitignore correctement")
    
    print()


if __name__ == "__main__":
    main()
