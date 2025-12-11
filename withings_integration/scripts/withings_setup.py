"""
Script de configuration initiale Withings OAuth
À exécuter UNE SEULE FOIS pour obtenir les credentials
"""

import os
import json
from withings_integration import WithingsIntegration
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading

# Configuration depuis .env.withings
from dotenv import load_dotenv
load_dotenv('.env.withings')

CLIENT_ID = os.getenv('WITHINGS_CLIENT_ID')
CLIENT_SECRET = os.getenv('WITHINGS_CLIENT_SECRET')
CALLBACK_URI = os.getenv('WITHINGS_CALLBACK_URI', 'http://localhost:8080/auth/withings/callback')

if not CLIENT_ID or not CLIENT_SECRET:
    print("Erreur: Variables d'environnement manquantes dans .env.withings")
    exit(1)

# Variable globale pour stocker le code
authorization_code = None
server_running = True

class CallbackHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour recevoir le callback OAuth"""
    
    def do_GET(self):
        global authorization_code, server_running
        
        # Parser l'URL pour extraire le code
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/auth/withings/callback':
            # Extraire le code d'autorisation
            params = parse_qs(parsed_path.query)
            
            if 'code' in params:
                authorization_code = params['code'][0]
                
                # Réponse succès
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Withings Authorization Successful</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            max-width: 600px;
                            margin: 100px auto;
                            text-align: center;
                        }
                        .success {
                            color: #28a745;
                            font-size: 24px;
                            margin-bottom: 20px;
                        }
                        .code {
                            background: #f4f4f4;
                            padding: 10px;
                            border-radius: 5px;
                            font-family: monospace;
                            word-break: break-all;
                        }
                    </style>
                </head>
                <body>
                    <div class="success">✓ Autorisation réussie !</div>
                    <p>Vous pouvez fermer cette fenêtre.</p>
                    <p>Le script continue automatiquement...</p>
                    <div class="code">
                        <small>Code: {}</small>
                    </div>
                </body>
                </html>
                """.format(authorization_code)
                
                self.wfile.write(success_html.encode())
                
                # Arrêter le serveur après réception du code
                threading.Thread(target=self.server.shutdown).start()
                
            else:
                # Erreur - pas de code
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = """
                <!DOCTYPE html>
                <html>
                <head><title>Error</title></head>
                <body>
                    <h1>Erreur d'autorisation</h1>
                    <p>Aucun code d'autorisation reçu.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Supprimer les logs HTTP verbeux"""
        pass


def start_callback_server():
    """Démarre un serveur HTTP pour recevoir le callback"""
    # Extraire le port de l'URL de callback
    parsed_callback = urlparse(CALLBACK_URI)
    port = parsed_callback.port or 80
    
    print(f"\n{'='*60}")
    print(f"Démarrage serveur callback sur port {port}...")
    print(f"{'='*60}\n")
    
    server = HTTPServer(('', port), CallbackHandler)
    server.serve_forever()


def main():
    """Processus complet d'authentification"""
    print("\n" + "="*60)
    print("CONFIGURATION WITHINGS - AUTHENTIFICATION INITIALE")
    print("="*60 + "\n")
    
    # Initialiser l'intégration
    withings = WithingsIntegration(CLIENT_ID, CLIENT_SECRET, CALLBACK_URI)
    
    # Obtenir l'URL d'autorisation
    auth_url = withings.get_authorization_url()
    
    print("\nÉtapes:")
    print("1. Le navigateur va s'ouvrir automatiquement")
    print("2. Connectez-vous à votre compte Withings")
    print("3. Autorisez l'application")
    print("4. Vous serez redirigé automatiquement")
    print("5. Le script récupérera le code automatiquement\n")
    
    input("Appuyez sur Entrée pour continuer...")
    
    # Démarrer le serveur callback dans un thread
    server_thread = threading.Thread(target=start_callback_server, daemon=True)
    server_thread.start()
    
    # Ouvrir le navigateur
    print("\nOuverture du navigateur...")
    webbrowser.open(auth_url)
    
    # Attendre la réception du code
    print("En attente de l'autorisation...\n")
    
    # Attendre que le serveur se termine (callback reçu)
    server_thread.join()
    
    if authorization_code:
        print("\n" + "="*60)
        print("✓ Code d'autorisation reçu !")
        print("="*60 + "\n")
        
        # Échanger le code contre des credentials
        print("Échange du code contre les tokens d'accès...")
        credentials = withings.authenticate_with_code(authorization_code)
        
        # Sauvegarder les credentials
        credentials_file = 'withings_credentials.json'
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"\n✓ Credentials sauvegardés dans '{credentials_file}'")
        
        # Test rapide
        print("\n" + "="*60)
        print("TEST DE CONNEXION")
        print("="*60 + "\n")
        
        withings.load_credentials(credentials)
        
        # Tester poids
        try:
            weight = withings.get_latest_weight()
            if weight:
                print(f"✓ Poids récupéré: {weight['weight_kg']}kg ({weight['date']})")
            else:
                print("ℹ Aucune donnée de poids récente")
        except Exception as e:
            print(f"⚠ Erreur poids: {e}")
        
        # Tester sommeil
        try:
            sleep = withings.get_last_night_sleep()
            if sleep:
                print(f"✓ Sommeil récupéré: {sleep['total_sleep_hours']}h ({sleep['date']})")
                print(f"  Score: {sleep['sleep_score']}/100")
            else:
                print("ℹ Aucune donnée de sommeil récente")
        except Exception as e:
            print(f"⚠ Erreur sommeil: {e}")
        
        print("\n" + "="*60)
        print("CONFIGURATION TERMINÉE !")
        print("="*60)
        print("\nVous pouvez maintenant utiliser withings_integration.py")
        print("Les credentials sont sauvegardés et se rafraîchiront automatiquement.\n")
        
        # Créer également un fichier .env
        env_content = f"""# Configuration Withings
WITHINGS_CLIENT_ID={CLIENT_ID}
WITHINGS_CLIENT_SECRET={CLIENT_SECRET}
WITHINGS_CALLBACK_URI={CALLBACK_URI}

# Configuration Intervals.icu (existante)
INTERVALS_ATHLETE_ID=i151223
INTERVALS_API_KEY=REDACTED_INTERVALS_KEY
"""
        
        with open('.env.withings', 'w') as f:
            f.write(env_content)
        
        print(f"✓ Fichier .env.withings créé avec la configuration")
        
    else:
        print("\n✗ Échec de l'autorisation - aucun code reçu")
        print("Vérifiez que:")
        print("- L'URL de callback dans le Developer Dashboard correspond")
        print("- Votre serveur ngrok/tunnel est actif")
        print("- Les ports correspondent")


if __name__ == "__main__":
    main()
