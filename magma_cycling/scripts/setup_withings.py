"""Interactive Withings OAuth setup script.

This script guides the user through the Withings OAuth 2.0 authentication flow
by starting a local HTTP server to capture the OAuth callback. Run once to
generate credentials, which are then saved for use with the MCP server and
other Withings integration tools.

Usage:
    python -m magma_cycling.scripts.setup_withings

Requirements:
    - WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET must be set in .env
    - Available port 8080 for local callback server
    - Web browser for OAuth authorization

The script will:
1. Generate an authorization URL
2. Open your browser to the Withings authorization page
3. Start a local server to receive the OAuth callback
4. Exchange the authorization code for access/refresh tokens
5. Save credentials to ~/training-logs/.withings_credentials.json

Example:
    $ python -m magma_cycling.scripts.setup_withings

    === Withings OAuth Setup ===

    Opening authorization URL in your browser...
    Waiting for authorization callback...

    ✓ Authorization successful!
    ✓ Credentials saved to ~/training-logs/.withings_credentials.json

    You can now use Withings tools in the MCP server!
"""

import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from magma_cycling.config import create_withings_client, get_withings_config

# Global variable to store authorization code
authorization_code = None
server_should_stop = False


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback.

    Captures the authorization code from Withings OAuth redirect and
    displays a success message to the user.
    """

    def log_message(self, format, *args):
        """Suppress HTTP server log messages."""
        pass

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        global authorization_code, server_should_stop

        # Parse query parameters
        query_components = parse_qs(urlparse(self.path).query)

        # Check if authorization code is present
        if "code" in query_components:
            authorization_code = query_components["code"][0]

            # Send success response to browser
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Withings Authorization Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 500px;
                    }
                    h1 {
                        color: #2ecc71;
                        margin-bottom: 20px;
                    }
                    p {
                        color: #555;
                        line-height: 1.6;
                        margin: 10px 0;
                    }
                    .checkmark {
                        font-size: 64px;
                        color: #2ecc71;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="checkmark">✓</div>
                    <h1>Authorization Successful!</h1>
                    <p>Withings has authorized your application.</p>
                    <p>You can close this window and return to the terminal.</p>
                    <p style="margin-top: 30px; color: #888; font-size: 14px;">
                        Credentials will be saved automatically.
                    </p>
                </div>
            </body>
            </html>
            """

            self.wfile.write(html.encode())
            server_should_stop = True

        elif "error" in query_components:
            # Handle authorization error
            error = query_components["error"][0]
            error_desc = query_components.get("error_description", ["Unknown error"])[0]

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Withings Authorization Failed</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 500px;
                    }}
                    h1 {{
                        color: #e74c3c;
                        margin-bottom: 20px;
                    }}
                    p {{
                        color: #555;
                        line-height: 1.6;
                        margin: 10px 0;
                    }}
                    .error {{
                        background: #fee;
                        border: 1px solid #fcc;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-family: monospace;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✗ Authorization Failed</h1>
                    <p>Withings authorization was not successful.</p>
                    <div class="error">
                        <strong>Error:</strong> {error}<br>
                        <strong>Description:</strong> {error_desc}
                    </div>
                    <p>Please close this window and try again from the terminal.</p>
                </div>
            </body>
            </html>
            """

            self.wfile.write(html.encode())
            server_should_stop = True

        else:
            # Unknown request
            self.send_response(400)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Invalid callback request")


def start_callback_server(port: int = 8080) -> str | None:
    """Start local HTTP server and wait for OAuth callback.

    Args:
        port: Port to listen on (default: 8080)

    Returns:
        Authorization code from callback, or None if failed/timeout
    """
    global server_should_stop

    server_address = ("", port)
    httpd = HTTPServer(server_address, CallbackHandler)

    print(f"Starting callback server on http://localhost:{port}")
    print("Waiting for authorization callback...\n")

    # Handle requests until we get the authorization code
    while not server_should_stop:
        httpd.handle_request()

    httpd.server_close()

    return authorization_code


def main():
    """Main setup flow for Withings OAuth authentication."""
    print("\n" + "=" * 50)
    print("    Withings OAuth Setup")
    print("=" * 50 + "\n")

    # Check configuration
    print("1. Checking configuration...")
    config = get_withings_config()

    if not config.is_configured():
        print("\n❌ Error: Withings API not configured\n")
        print("Please set the following environment variables in your .env file:")
        print("  - WITHINGS_CLIENT_ID")
        print("  - WITHINGS_CLIENT_SECRET")
        print("\nGet your credentials from: https://developer.withings.com/dashboard")
        sys.exit(1)

    print(f"   ✓ Client ID: {config.client_id[:20]}...")
    print(f"   ✓ Client Secret: {'*' * 20}")
    print(f"   ✓ Redirect URI: {config.redirect_uri}")

    # Check if already authenticated
    if config.has_valid_credentials():
        print("\n⚠️  Valid credentials already exist at:")
        print(f"   {config.credentials_path}")
        print("\nDo you want to re-authenticate? (y/N): ", end="")
        response = input().strip().lower()

        if response != "y":
            print("\n✓ Using existing credentials")
            print("\nSetup complete!")
            return

    # Create client
    print("\n2. Creating Withings client...")
    try:
        client = create_withings_client()
        print("   ✓ Client created")
    except Exception as e:
        print(f"\n❌ Error creating client: {e}")
        sys.exit(1)

    # Generate authorization URL
    print("\n3. Generating authorization URL...")
    try:
        auth_url = client.get_authorization_url(state="setup_script")
        print("   ✓ Authorization URL generated")
    except Exception as e:
        print(f"\n❌ Error generating URL: {e}")
        sys.exit(1)

    # Open browser
    print("\n4. Opening browser for authorization...")
    print(f"   URL: {auth_url}")

    try:
        webbrowser.open(auth_url)
        print("   ✓ Browser opened")
    except Exception as e:
        print(f"\n⚠️  Could not open browser automatically: {e}")
        print(f"\nPlease manually visit:\n{auth_url}\n")

    # Start callback server
    print("\n5. Waiting for authorization...")
    print("   (Authorize the application in your browser)")

    try:
        code = start_callback_server(port=8080)

        if not code:
            print("\n❌ Authorization failed or timed out")
            sys.exit(1)

        print("   ✓ Authorization code received")

    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error starting callback server: {e}")
        print("\nMake sure port 8080 is available.")
        sys.exit(1)

    # Exchange code for tokens
    print("\n6. Exchanging authorization code for tokens...")
    try:
        tokens = client.exchange_code(code)
        print("   ✓ Access token obtained")
        print("   ✓ Refresh token obtained")
        print(f"   ✓ User ID: {tokens['user_id']}")
    except Exception as e:
        print(f"\n❌ Error exchanging code: {e}")
        sys.exit(1)

    # Verify credentials saved
    print("\n7. Verifying credentials...")
    if config.credentials_path.exists():
        print("   ✓ Credentials saved to:")
        print(f"     {config.credentials_path}")

        # Set file permissions
        config.credentials_path.chmod(0o600)
        print("   ✓ File permissions set to 600 (owner read/write only)")
    else:
        print("\n❌ Warning: Credentials file not found at:")
        print(f"   {config.credentials_path}")

    # Test authentication
    print("\n8. Testing authentication...")
    try:
        if client.is_authenticated():
            print("   ✓ Authentication valid")

            # Try to fetch data
            latest_weight = client.get_latest_weight()
            if latest_weight:
                print(f"   ✓ API working - Latest weight: {latest_weight['weight_kg']} kg")
            else:
                print("   ⚠️  API working but no weight data found")

        else:
            print("   ❌ Authentication failed")

    except Exception as e:
        print(f"   ⚠️  Could not test API: {e}")

    # Success
    print("\n" + "=" * 50)
    print("✓ Setup complete!")
    print("=" * 50)
    print("\nYou can now use Withings tools:")
    print("  - MCP server: withings-get-sleep, withings-get-weight, etc.")
    print("  - Python API: create_withings_client()")
    print(f"\nCredentials stored in: {config.credentials_path}")
    print("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
