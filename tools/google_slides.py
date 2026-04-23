"""
Read and update Google Slides presentations.

Usage:
    from tools.google_slides import get_presentation, replace_text, add_slide

    pres = get_presentation(slides_id)
    replace_text(slides_id, replacements={"{{title}}": "My Report"})
"""
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/presentations"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"


def _get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("slides", "v1", credentials=creds)


def get_presentation(slides_id: str) -> dict:
    service = _get_service()
    return service.presentations().get(presentationId=slides_id).execute()


def replace_text(slides_id: str, replacements: dict[str, str]) -> dict:
    """Replace placeholder text across all slides. Keys are search strings, values are replacements."""
    service = _get_service()
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": search, "matchCase": False},
                "replaceText": replace,
            }
        }
        for search, replace in replacements.items()
    ]
    body = {"requests": requests}
    result = (
        service.presentations()
        .batchUpdate(presentationId=slides_id, body=body)
        .execute()
    )
    print(f"[OK] Text replacements applied to presentation")
    return result


def list_slides(slides_id: str) -> list[dict]:
    pres = get_presentation(slides_id)
    slides = pres.get("slides", [])
    print(f"[OK] Presentation has {len(slides)} slides")
    return slides


if __name__ == "__main__":
    slides_id = os.getenv("GOOGLE_SLIDES_ID")
    if not slides_id:
        print("[ERROR] GOOGLE_SLIDES_ID not set in .env")
        exit(1)
    slides = list_slides(slides_id)
    for i, slide in enumerate(slides):
        print(f"  Slide {i+1}: {slide.get('objectId')}")
