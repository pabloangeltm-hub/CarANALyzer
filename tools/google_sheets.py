"""
Read and write Google Sheets.

Usage:
    from tools.google_sheets import read_sheet, write_sheet, append_rows

    data = read_sheet(sheet_id, range_="Sheet1!A1:Z")
    write_sheet(sheet_id, range_="Sheet1!A1", values=[[...]])
    append_rows(sheet_id, range_="Sheet1", values=[[...]])
"""
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
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
    return build("sheets", "v4", credentials=creds)


def read_sheet(sheet_id: str, range_: str) -> list[list]:
    service = _get_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


def write_sheet(sheet_id: str, range_: str, values: list[list]) -> dict:
    service = _get_service()
    body = {"values": values}
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=sheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    print(f"[OK] {result.get('updatedCells')} cells updated")
    return result


def append_rows(sheet_id: str, range_: str, values: list[list]) -> dict:
    service = _get_service()
    body = {"values": values}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    print(f"[OK] {result.get('updates', {}).get('updatedRows', '?')} rows appended")
    return result


def clear_range(sheet_id: str, range_: str) -> dict:
    service = _get_service()
    result = (
        service.spreadsheets()
        .values()
        .clear(spreadsheetId=sheet_id, range=range_)
        .execute()
    )
    print(f"[OK] Range {range_} cleared")
    return result


if __name__ == "__main__":
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("[ERROR] GOOGLE_SHEET_ID not set in .env")
        exit(1)
    data = read_sheet(sheet_id, "Sheet1!A1:Z10")
    print(f"[OK] Read {len(data)} rows from Sheet1")
    for row in data:
        print(row)
