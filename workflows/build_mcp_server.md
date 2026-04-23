# Workflow: Build an MCP Server

## Objective
Design and implement a Model Context Protocol (MCP) server that connects Claude (or another LLM) to an external API or service, following agent-centric design principles that prioritize high-signal responses and natural task workflows.

## Triggers
Activate when the user says things like:
- "Build an MCP server for..."
- "Create an MCP tool that connects to..."
- "I want Claude to be able to [action] via MCP"
- "Add MCP support for [service/API]"

## Required Inputs
- Target API or service name
- API documentation URL or credentials
- Preferred implementation language (default: Python via FastMCP)
- Scope: which operations/endpoints to expose as tools

## Optional Inputs
- Existing API key or credentials (store in `.env`)
- Examples of how the agent should use the tools
- Performance or rate-limit constraints

---

## Phase 1 — Research and Planning

### 1.1 Study the MCP protocol
Fetch core reference documentation before writing any code:
- MCP protocol spec: `https://modelcontextprotocol.io/llms-full.txt`
- Python SDK: `https://github.com/modelcontextprotocol/python-sdk`
- TypeScript SDK (if Node): `https://github.com/modelcontextprotocol/typescript-sdk`

### 1.2 Analyze the target API
- Read the full API documentation
- Identify natural task groupings (not 1:1 endpoint mapping — think in agent workflows)
- Note authentication method, rate limits, pagination patterns, and error codes
- Flag any read-only vs. write operations (keep evaluations read-only)

### 1.3 Design the tool surface
Design tools around **agent workflows**, not API endpoints:
- Name tools as verbs: `search_contacts`, `create_draft`, `get_order_status`
- Return **high-signal summaries**, not raw API JSON — agents have limited context windows
- Error messages must guide the agent toward correct usage (not just report HTTP codes)
- Aim for 5–15 focused tools; avoid exposing every endpoint

Draft a tool list before writing code. Confirm with user if scope is ambiguous.

---

## Phase 2 — Implementation (Python / FastMCP)

### 2.1 Project structure

Generate the skeleton with the scaffold tool before writing any logic:

```bash
python tools/scaffold_mcp.py --service <service-name>
# Creates ./mcp-<service-name>/ with server.py, api.py, formatters.py, requirements.txt, README.md
```

```
mcp-<service>/
├── server.py          # Main FastMCP server and tool definitions
├── api.py             # API client helpers, auth, retry logic
├── formatters.py      # Response formatters — raw API → agent-readable text
├── requirements.txt   # fastmcp, httpx, python-dotenv, etc.
└── README.md          # Setup instructions and tool reference
```

After scaffolding: open `api.py`, replace `BASE_URL` with the real endpoint, and implement each method.

### 2.2 Server scaffold (FastMCP)
```python
from fastmcp import FastMCP
import os
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("<service-name>")

@mcp.tool()
def search_items(query: str, limit: int = 10) -> str:
    """Search items by keyword. Returns top results as a formatted list."""
    # ... implementation
```

### 2.3 Implementation checklist
- [ ] All tools have docstrings — the LLM uses these to decide when to call the tool
- [ ] Input parameters have type hints and sensible defaults
- [ ] Return type is always `str` — format for readability, not for machines
- [ ] Shared API client instantiated once, not per-call
- [ ] All errors caught and returned as descriptive strings (never raise to the agent)
- [ ] Credentials loaded from `.env` — never hardcoded
- [ ] Rate limits handled with exponential backoff in `api.py`

### 2.4 Response formatting principles
- Lead with the most important information
- Use structured text (markdown lists, key: value pairs) over raw JSON
- Include counts when returning collections: `"Found 3 results:"`
- Truncate large payloads and indicate truncation: `"... (showing 10 of 47)"`

---

## Phase 3 — Review and Refine

### 3.1 Code quality audit
- [ ] DRY: no repeated API call patterns — extract to `api.py`
- [ ] Type safety: all function signatures annotated
- [ ] Docstrings: every tool has a clear, agent-facing description
- [ ] No hardcoded secrets
- [ ] Error handling: every external call wrapped in try/except

### 3.2 Testing (IMPORTANT: never run the server directly — it hangs)
Test using the MCP Inspector or a tmux split:
```bash
# Terminal 1: start the server
fastmcp run server.py

# Terminal 2: test individual tools
fastmcp call search_items '{"query": "test"}'
```

Or use the evaluation harness (see Phase 4).

### 3.3 Edge cases to verify
- Empty results (return a clear "No results found" message, not an empty list)
- API auth failures (return actionable error: "Check API_KEY in .env")
- Rate limit hits (return: "Rate limit reached — retry in N seconds")
- Large payloads (truncate and indicate: "Showing first 10 of 47 results")

---

## Phase 4 — Create Evaluations

Design 10 independent, read-only evaluation questions that verify the server works correctly. Each question must:
- Be answerable with a single tool call or short chain
- Use real data (not mocked)
- Have a personally verified correct answer

### Evaluation output format
```xml
<evaluations>
  <eval id="1">
    <question>How many items are in the default collection?</question>
    <tool>list_items</tool>
    <expected>A count greater than 0</expected>
  </eval>
  ...
</evaluations>
```

Record evaluation results in `.tmp/mcp-<service>-eval.xml`.

---

## Registration

After the server is built and tested, register it in Claude's MCP config:

```json
{
  "mcpServers": {
    "<service-name>": {
      "command": "fastmcp",
      "args": ["run", "path/to/server.py"],
      "env": {
        "API_KEY": "${<SERVICE>_API_KEY}"
      }
    }
  }
}
```

Store credentials in `.env` using the pattern `<SERVICE>_API_KEY=...`.

## Expected Output
- A working MCP server in a `mcp-<service>/` directory
- 10 passing evaluations in `.tmp/mcp-<service>-eval.xml`
- Registration entry in the MCP config
- Credentials added to `.env`

## Edge Cases
- **API uses OAuth:** implement the OAuth flow in `api.py` and store tokens in `.env`
- **API is paginated:** build pagination into the helper, expose `limit` and `offset` as tool params
- **API is rate-limited:** implement exponential backoff in `api.py` — document the limits in the README
- **Scope is too large:** default to read operations only; confirm with user before implementing writes
