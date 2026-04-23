# Workflow: Update Google Sheet

## Objective
Read from or write data to a Google Sheet.

## Required Inputs
- `GOOGLE_SHEET_ID` in `.env`
- `token.json` at project root (run `python tools/google_auth_setup.py` once to generate it)
- Data to write (as a list of rows)
- Target range (e.g. `Sheet1!A1`)

## Tool
`tools/google_sheets.py`

## First-Time Setup
Run once to authorize Google access:
```bash
python tools/google_auth_setup.py
```
This opens a browser. Approve access. `token.json` is saved automatically and reused on future runs.

## Operations

### Read
```python
from tools.google_sheets import read_sheet
import os; from dotenv import load_dotenv; load_dotenv()
rows = read_sheet(os.getenv("GOOGLE_SHEET_ID"), "Sheet1!A1:Z100")
```

### Write (overwrite range)
```python
from tools.google_sheets import write_sheet
write_sheet(sheet_id, "Sheet1!A1", [["Header1", "Header2"], ["val1", "val2"]])
```

### Append rows
```python
from tools.google_sheets import append_rows
append_rows(sheet_id, "Sheet1", [["new_val1", "new_val2"]])
```

## Edge Cases
- **Token expired**: Delete `token.json` and re-run `google_auth_setup.py`
- **Wrong sheet ID**: The ID is the long string in the Google Sheets URL between `/d/` and `/edit`
- **Range mismatch**: If writing more columns than the range allows, extend the range or use `append_rows`
- **Quota limits**: Google Sheets API allows 300 write requests/minute per project

## Expected Output
Data read as a list of lists, or confirmation of rows written/updated.
