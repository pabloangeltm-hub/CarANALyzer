# Workflow: Scrape Website

## Objective
Extract clean text content from a single URL and save it to `.tmp/` for further processing.

## Required Inputs
- `url` — the target URL

## Optional Inputs
- `output_file` — path to save result (default: `.tmp/scraped.txt`)

## Tool
`tools/scrape_website.py`

## Steps
1. Run the scraper with the target URL
2. Verify the output file exists and has content
3. If the task requires analysis, pipe the output to `tools/ask_claude.py`

## Commands
```bash
python tools/scrape_website.py --url <URL> --output .tmp/scraped.txt
python tools/ask_claude.py --prompt "Summarize this page" --file .tmp/scraped.txt
```

## Edge Cases
- **403 / bot detection**: Add delay or use a different User-Agent header in the script
- **JS-rendered content**: The scraper uses `requests` + `BeautifulSoup` — it does NOT execute JavaScript. If the page requires JS, content will be missing. Workaround: use the page's API or RSS feed instead.
- **Encoding errors**: The script uses UTF-8 encoding. Non-UTF-8 pages may need `--encoding` handling.
- **Large pages**: Output is truncated in CLI preview; full content is always saved to file.

## Expected Output
A `.txt` file in `.tmp/` containing the page title and body text, ready for analysis or storage.
