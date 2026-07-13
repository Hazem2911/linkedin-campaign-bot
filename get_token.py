#!/usr/bin/env python3
"""
One-time helper: get a LinkedIn access token + your person URN.

Before running:
1. Create an app at https://www.linkedin.com/developers/apps  (takes ~3 minutes)
2. In the app -> Products: request "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect"
3. In the app -> Auth: add redirect URL  http://localhost:8914/callback
4. Copy your Client ID and Client Secret below (or set env vars)

Run:
  python get_token.py

It opens your browser, you approve once, and it prints the two values
you need to put in GitHub Secrets:
  LINKEDIN_ACCESS_TOKEN   (valid ~60 days)
  LINKEDIN_PERSON_URN
"""

import http.server
import os
import secrets
import threading
import urllib.parse
import webbrowser

import requests

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "PUT_YOUR_CLIENT_ID_HERE")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "PUT_YOUR_CLIENT_SECRET_HERE")
REDIRECT_URI = "http://localhost:8914/callback"
SCOPES = "openid profile w_member_social"

_code_holder: dict = {}


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _code_holder["code"] = params["code"][0]
            body = b"<h2>Done! You can close this tab and go back to the terminal.</h2>"
        else:
            body = b"<h2>No code received. Try again.</h2>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence server logs
        pass


def main() -> None:
    state = secrets.token_urlsafe(16)
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?response_type=code"
        f"&client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state={state}&scope={urllib.parse.quote(SCOPES)}"
    )

    server = http.server.HTTPServer(("localhost", 8914), CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("Opening browser for LinkedIn approval…")
    webbrowser.open(auth_url)
    print("(If the browser did not open, paste this URL manually:)\n" + auth_url + "\n")

    while "code" not in _code_holder:
        pass  # wait for the callback
    server.shutdown()

    print("Exchanging code for an access token…")
    r = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": _code_holder["code"],
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    r.raise_for_status()
    token = r.json()["access_token"]

    me = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    me.raise_for_status()
    person_urn = f"urn:li:person:{me.json()['sub']}"

    print("\n" + "=" * 60)
    print("Add these two values as GitHub Actions secrets:\n")
    print(f"LINKEDIN_ACCESS_TOKEN = {token}")
    print(f"LINKEDIN_PERSON_URN   = {person_urn}")
    print("=" * 60)
    print("\nToken lifetime is ~60 days — enough for the whole campaign.")


if __name__ == "__main__":
    main()
