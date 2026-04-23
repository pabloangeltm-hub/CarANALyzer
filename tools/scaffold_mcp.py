"""
Scaffold a new MCP server project with the standard WAT framework structure.
Generates all boilerplate files so Phase 2 of build_mcp_server.md starts from a clean base.

Usage:
    python tools/scaffold_mcp.py --service notion
    python tools/scaffold_mcp.py --service stripe --output-dir ./mcp-servers/mcp-stripe
"""
import argparse
import os
import sys

TEMPLATES = {
    "server.py": '''\
"""
MCP server for {service_title} via FastMCP.
Tools are named as agent-facing verbs. Return values are always str.
"""
from fastmcp import FastMCP
import os
from dotenv import load_dotenv
from api import {service_var}_client
from formatters import format_result

load_dotenv()

mcp = FastMCP("{service_name}")


@mcp.tool()
def search_{service_var}(query: str, limit: int = 10) -> str:
    """Search {service_title} by keyword. Returns top results as a formatted list."""
    try:
        client = {service_var}_client()
        results = client.search(query, limit=limit)
        return format_result(results)
    except Exception as e:
        return f"Error searching {service_title}: {{e}}"


if __name__ == "__main__":
    mcp.run()
''',

    "api.py": '''\
"""
{service_title} API client — auth, retry logic, and shared helpers.
All external calls live here. server.py never calls requests/httpx directly.
"""
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.example.com/v1"  # TODO: replace with real base URL
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def {service_var}_client() -> "_{service_class}Client":
    api_key = os.getenv("{service_env}_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing {service_env}_API_KEY in .env")
    return _{service_class}Client(api_key)


class _{service_class}Client:
    def __init__(self, api_key: str):
        self._headers = {{"Authorization": f"Bearer {{api_key}}", "Content-Type": "application/json"}}

    def get(self, path: str, params: dict = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict = None) -> dict:
        return self._request("POST", path, json=body)

    def search(self, query: str, limit: int = 10) -> dict:
        # TODO: implement real search endpoint
        return self.get("/search", params={{"q": query, "limit": limit}})

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = BASE_URL + path
        for attempt in range(MAX_RETRIES):
            try:
                response = httpx.request(method, url, headers=self._headers, timeout=15, **kwargs)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", BACKOFF_BASE ** attempt))
                    return {{"error": f"Rate limit reached — retry in {{retry_after}} seconds"}}
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    return {{"error": "Authentication failed — check {service_env}_API_KEY in .env"}}
                if attempt == MAX_RETRIES - 1:
                    return {{"error": f"HTTP {{e.response.status_code}}: {{e.response.text[:200]}}"}}
                time.sleep(BACKOFF_BASE ** attempt)
            except httpx.RequestError as e:
                if attempt == MAX_RETRIES - 1:
                    return {{"error": f"Network error: {{e}}"}}
                time.sleep(BACKOFF_BASE ** attempt)
        return {{"error": "Max retries exceeded"}}
''',

    "formatters.py": '''\
"""
Response formatters — raw {service_title} API JSON → agent-readable text.
Rules: lead with the most important info, use markdown lists, include counts,
truncate large payloads and indicate truncation.
"""

MAX_ITEMS = 10


def format_result(data: dict | list, max_items: int = MAX_ITEMS) -> str:
    """Generic formatter. Replace with domain-specific formatters as needed."""
    if isinstance(data, dict) and "error" in data:
        return f"Error: {{data['error']}}"

    if isinstance(data, list):
        total = len(data)
        items = data[:max_items]
        lines = [f"Found {{total}} result(s):" if total > 0 else "No results found."]
        for item in items:
            lines.append(f"- {{_summarise(item)}}")
        if total > max_items:
            lines.append(f"... (showing {{max_items}} of {{total}})")
        return "\\n".join(lines)

    return str(data)


def _summarise(item: dict | str) -> str:
    if isinstance(item, str):
        return item
    # Try common identifier fields first
    for key in ("name", "title", "id", "label", "subject"):
        if key in item:
            return str(item[key])
    return str(item)[:120]
''',

    "requirements.txt": '''\
fastmcp
httpx
python-dotenv
''',

    "README.md": '''\
# mcp-{service_name}

MCP server for **{service_title}** built with FastMCP.

## Setup

1. Add your API key to `.env` at the project root:
   ```
   {service_env}_API_KEY=your_key_here
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running

```bash
fastmcp run server.py
```

Never run `python server.py` directly — it will hang waiting for MCP stdio input.

## Testing individual tools

```bash
fastmcp call search_{service_var} \'{{"query": "test"}}\'
```

## Tools

| Tool | Description |
|------|-------------|
| `search_{service_var}` | Search {service_title} by keyword |

## Registration in Claude

Add to your MCP config (`claude_desktop_config.json` or `.claude/settings.json`):

```json
{{
  "mcpServers": {{
    "{service_name}": {{
      "command": "fastmcp",
      "args": ["run", "path/to/mcp-{service_name}/server.py"],
      "env": {{
        "{service_env}_API_KEY": "${{{service_env}_API_KEY}}"
      }}
    }}
  }}
}}
```
''',
}


def scaffold(service: str, output_dir: str) -> None:
    service_name = service.lower().replace(" ", "-")
    service_var = service_name.replace("-", "_")
    service_title = service.title().replace("-", " ")
    service_class = service_title.replace(" ", "")
    service_env = service.upper().replace("-", "_")

    os.makedirs(output_dir, exist_ok=True)

    ctx = {
        "service_name": service_name,
        "service_var": service_var,
        "service_title": service_title,
        "service_class": service_class,
        "service_env": service_env,
    }

    created = []
    for filename, template in TEMPLATES.items():
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            print(f"[SKIP] {path} already exists — not overwriting")
            continue
        content = template.format(**ctx)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(filename)
        print(f"[OK]   {path}")

    if created:
        print(f"\nScaffolded {len(created)} file(s) in {output_dir}/")
        print(f"Next: open {output_dir}/api.py and replace BASE_URL + implement search()")
    else:
        print("Nothing created — all files already exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new MCP server project")
    parser.add_argument("--service", required=True, help="Service name (e.g. notion, stripe, github)")
    parser.add_argument("--output-dir", help="Where to create the project (default: ./mcp-<service>)")
    args = parser.parse_args()

    out = args.output_dir or f"./mcp-{args.service.lower().replace(' ', '-')}"
    scaffold(service=args.service, output_dir=out)
