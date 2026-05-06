"""
Setup utility — writes the header row to the CarANALyzer Google Sheet.

Run once after creating the spreadsheet (or after adding new columns).
Safe to re-run: checks for an existing header before writing.

Usage:
    python tools/setup_sheet.py
"""

import os
from dotenv import load_dotenv
from tools.utils.google_sheets_manager import GoogleSheetsManager

load_dotenv()

SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "").strip()
SHEETS_TAB: str = "Oportunidades"

HEADER = [
    "Portal",
    "Marca",
    "Modelo",
    "Año",
    "KM",
    "Precio Lista €",
    "Precio Mercado €",
    "ROI Bruto %",
    "ROI Neto %",
    "Muestra",
    "Daños",
    "Coste Rep. €",
    "Resumen Forense",
    "URL",
    "Fecha",
]


def main() -> None:
    if not SPREADSHEET_ID:
        print("[ERROR] SPREADSHEET_ID not set in .env — aborting.")
        return

    sheets = GoogleSheetsManager()
    sheets.connect(spreadsheet_id=SPREADSHEET_ID)

    # Read row 1 to check if header already exists
    ws = sheets._worksheet(SHEETS_TAB)
    first_row = ws.row_values(1)

    if first_row == HEADER:
        print(f"[OK] Header already correct in '{SHEETS_TAB}' — nothing to do.")
        return

    if first_row:
        print(f"[WARN] Row 1 exists but doesn't match expected header.")
        print(f"  Found:    {first_row}")
        print(f"  Expected: {HEADER}")
        answer = input("Overwrite row 1? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    ws.update("A1", [HEADER])
    print(f"[OK] Header written to '{SHEETS_TAB}':")
    for i, col in enumerate(HEADER, 1):
        print(f"  {i:>2}. {col}")


if __name__ == "__main__":
    main()
