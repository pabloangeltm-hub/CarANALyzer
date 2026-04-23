# Workflow: Ask Claude

## Objective
Send a prompt (optionally with file context) to Claude and get a response. Use this as a processing step inside larger workflows.

## Required Inputs
- `ANTHROPIC_API_KEY` in `.env`
- A prompt string

## Optional Inputs
- A context file (scraped page, spreadsheet export, etc.)
- A system prompt to set behavior
- An output file path

## Tool
`tools/ask_claude.py`

## Commands
```bash
# Simple question
python tools/ask_claude.py --prompt "What are the key metrics in this data?" --file .tmp/data.txt

# Save response
python tools/ask_claude.py --prompt "Write a summary" --file .tmp/scraped.txt --output .tmp/summary.txt

# With system prompt
python tools/ask_claude.py --prompt "Extract all company names" --file .tmp/page.txt --system "Return only a JSON array of strings."
```

## As a Module
```python
from tools.ask_claude import ask
summary = ask("Summarize this", context=open(".tmp/data.txt").read())
```

## Edge Cases
- **Large context**: Claude supports up to 200K tokens. For very large files, chunk them first.
- **Structured output**: Use `--system "Return only valid JSON"` to enforce format.
- **Rate limits**: claude-sonnet-4-6 handles high throughput; no throttling needed for single calls.

## Expected Output
A text response from Claude, either printed to stdout or saved to the specified output file.
