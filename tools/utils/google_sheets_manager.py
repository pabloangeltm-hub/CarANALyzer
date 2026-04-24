"""
CRM connector for Google Sheets.

Usage:
    from tools.utils.google_sheets_manager import GoogleSheetsManager

    mgr = GoogleSheetsManager()
    mgr.connect(spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")

    # Register a new car opportunity
    mgr.append_row(["Toyota Supra", "15000", "Madrid", "https://...", "Nuevo"])

    # Mark an opportunity as contacted
    mgr.find_and_update(
        search_col="URL",
        search_value="https://...",
        update_col="Estado",
        new_value="Contactado",
    )

    records = mgr.get_all_records()

Credentials:
    Place credentials.json (OAuth Desktop App or Service Account) at the project root.
    The script auto-detects the credential type from the 'type' field in that file.
    For OAuth flows, the resulting token is cached in token.json (gitignored).
"""

import json
import os
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# Drive.readonly is required only when opening a spreadsheet by display name.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

ROOT = Path(__file__).resolve().parents[2]
CREDS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"


class GoogleSheetsManager:
    """Deterministic CRM connector for a single Google Spreadsheet.

    Wraps gspread to provide a stable, intent-driven interface for the car
    arbitrage pipeline: append new opportunities and update their status fields.
    """

    def __init__(self):
        self._client: gspread.Client = self._authenticate()
        self._spreadsheet: gspread.Spreadsheet = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> gspread.Client:
        if not CREDS_PATH.exists():
            raise FileNotFoundError(
                f"credentials.json not found at {CREDS_PATH}. "
                "Download it from Google Cloud Console → APIs & Services → Credentials."
            )

        with open(CREDS_PATH) as f:
            cred_type = json.load(f).get("type", "")

        if cred_type == "service_account":
            # Service accounts need no browser interaction.
            return gspread.service_account(filename=str(CREDS_PATH))

        # OAuth Desktop App — opens a browser on first run, then caches token.json.
        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        return gspread.Client(auth=creds)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(
        self,
        spreadsheet_id: str = None,
        spreadsheet_name: str = None,
    ) -> "GoogleSheetsManager":
        """Open a spreadsheet by ID (preferred, stable) or display name.

        Prefer spreadsheet_id — display names are not unique and require the
        Drive.readonly scope.
        """
        if spreadsheet_id:
            self._spreadsheet = self._client.open_by_key(spreadsheet_id)
        elif spreadsheet_name:
            self._spreadsheet = self._client.open(spreadsheet_name)
        else:
            raise ValueError("Provide spreadsheet_id or spreadsheet_name.")

        print(f"[OK] Connected to '{self._spreadsheet.title}'")
        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _worksheet(self, name: str) -> gspread.Worksheet:
        if self._spreadsheet is None:
            raise RuntimeError("Call connect() before operating on worksheets.")
        return self._spreadsheet.worksheet(name)

    def _resolve_col_index(
        self, col: Union[str, int], headers: list
    ) -> int:
        """Return 1-based column index from a header name or a 1-based int."""
        if isinstance(col, int):
            return col
        try:
            return headers.index(col) + 1
        except ValueError:
            raise KeyError(
                f"Column '{col}' not found. Available headers: {headers}"
            )

    # ------------------------------------------------------------------
    # CRM operations
    # ------------------------------------------------------------------

    def append_row(
        self,
        values: list,
        worksheet_name: str = "Sheet1",
    ) -> dict:
        """Append a single row at the first empty position in the sheet.

        Args:
            values: Ordered list of cell values matching the sheet's column layout.
            worksheet_name: Tab name inside the spreadsheet (default 'Sheet1').

        Returns:
            Raw API response dict from gspread.
        """
        ws = self._worksheet(worksheet_name)
        result = ws.append_row(values, value_input_option="USER_ENTERED")
        print(f"[OK] Row appended to '{worksheet_name}'")
        return result

    def find_and_update(
        self,
        search_col: Union[str, int],
        search_value: str,
        update_col: Union[str, int],
        new_value: str,
        worksheet_name: str = "Sheet1",
    ) -> bool:
        """Find the first row where search_col == search_value and set update_col.

        Args:
            search_col: Header name (str) or 1-based column index (int) to search in.
            search_value: The cell value to locate.
            update_col: Header name (str) or 1-based column index (int) to overwrite.
            new_value: Value to write into the matched cell.
            worksheet_name: Tab name inside the spreadsheet (default 'Sheet1').

        Returns:
            True if a row was found and updated, False if no match exists.
        """
        ws = self._worksheet(worksheet_name)
        headers = ws.row_values(1)

        search_idx = self._resolve_col_index(search_col, headers)
        update_idx = self._resolve_col_index(update_col, headers)

        col_values = ws.col_values(search_idx)
        try:
            # col_values[0] is the header — row numbers are 1-based in Sheets.
            row_number = col_values.index(search_value) + 1
        except ValueError:
            print(f"[MISS] '{search_value}' not found in column '{search_col}'")
            return False

        ws.update_cell(row_number, update_idx, new_value)
        print(f"[OK] Row {row_number}: '{update_col}' → '{new_value}'")
        return True

    def get_all_records(
        self,
        worksheet_name: str = "Sheet1",
    ) -> list:
        """Return every data row as a dict keyed by the header row.

        Returns:
            List of dicts, one per data row, with header names as keys.
        """
        ws = self._worksheet(worksheet_name)
        return ws.get_all_records()
