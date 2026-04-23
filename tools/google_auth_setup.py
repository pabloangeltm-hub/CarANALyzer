"""
Run once to authorize Google APIs and generate token.json.
Opens a browser window for the OAuth consent screen.

Usage:
    python tools/google_auth_setup.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
        print(f"[OK] Token saved to {TOKEN_PATH}")

    return creds


if __name__ == "__main__":
    if not os.path.exists(CREDS_PATH):
        print(f"[ERROR] {CREDS_PATH} not found. Download it from Google Cloud Console.")
        exit(1)
    creds = get_credentials()
    print("[OK] Google authentication successful. Scopes authorized:")
    for s in SCOPES:
        print(f"  - {s}")
