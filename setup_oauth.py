"""
One-time Google OAuth2 setup for the Social Engine.

Run this once per client on the machine that will run the engine.
It opens a browser window, you log in with the Google account that has
access to the RPG Shared Drive, and it saves a token file locally.

Usage:
    python setup_oauth.py --client ryan
    python setup_oauth.py --client client_b

The token is saved to:
    tokens/ryan_token.json
    tokens/client_b_token.json

These files are in .gitignore and will never be committed to the repo.
The engine auto-refreshes the token when it expires.
"""
import argparse
import json
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.parse

# Google OAuth2 endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8765/callback"

# Scopes needed for Drive read access
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

# These are the same client credentials used by rclone/gws for Drive access.
# They are the standard Google Drive desktop client credentials - not secret.
# See: https://rclone.org/drive/#making-your-own-client-id
CLIENT_ID = "202264815644.apps.googleusercontent.com"
CLIENT_SECRET = "X4Z3ca8xfWDb1Voo-F9a7ZxJ"

# Where to save tokens
TOKENS_DIR = os.path.join(os.path.dirname(__file__), "tokens")

_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server to catch the OAuth callback."""

    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style='font-family:sans-serif;padding:40px'>
                <h2>Authorization successful!</h2>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            """)
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def authorize(client_slug: str):
    global _auth_code
    _auth_code = None

    os.makedirs(TOKENS_DIR, exist_ok=True)
    token_path = os.path.join(TOKENS_DIR, f"{client_slug}_token.json")

    # Build the authorization URL
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print(f"\nSetting up Google Drive access for client: {client_slug}")
    print("=" * 60)
    print("\nOpening your browser for Google authorization...")
    print("Log in with the Google account that has access to the RPG Shared Drive.")
    print(f"\nIf the browser does not open automatically, visit:\n{auth_url}\n")

    webbrowser.open(auth_url)

    # Start local server to catch the callback
    server = HTTPServer(("localhost", 8765), _CallbackHandler)
    print("Waiting for authorization (listening on localhost:8765)...")
    server.handle_request()

    if not _auth_code:
        print("\nAuthorization failed. No code received.")
        return

    # Exchange code for tokens
    token_data = {
        "code": _auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(token_data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())

    if "error" in tokens:
        print(f"\nToken exchange failed: {tokens}")
        return

    # Save token
    saved = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "token_uri": TOKEN_URL,
    }
    with open(token_path, "w") as f:
        json.dump(saved, f, indent=2)

    print(f"\nSuccess! Token saved to: {token_path}")
    print(f"\nYou are now authorized. The engine will use this token automatically.")
    print(f"The token auto-refreshes - you will not need to run this again unless")
    print(f"you revoke access in your Google account settings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One-time Google OAuth2 setup")
    parser.add_argument("--client", required=True, help="Client slug (ryan or client_b)")
    args = parser.parse_args()
    authorize(args.client)
