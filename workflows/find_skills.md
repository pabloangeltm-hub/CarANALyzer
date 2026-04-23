# Workflow: Find & Install Skills

## Objective
Discover and install agent skills from the open ecosystem when the user asks to extend capabilities.

## Triggers
Activate this workflow when the user says things like:
- "¿hay una skill para...?"
- "busca una skill que..."
- "¿cómo hago X?" (when a skill may exist for X)
- "find a skill for..."
- "install a skill that..."
- "¿existe algo que automatice...?"

## Required Inputs
- User's intent or domain (e.g., "web scraping", "test generation", "diagram creation")

## Tool Sequence

### Step 1 — Identify the domain and task
- Extract the core domain (e.g., DevOps, Testing, Documentation) and the specific task
- Assess likelihood that an existing skill covers it before searching

### Step 2 — Check the skills.sh leaderboard
- Browse https://skills.sh/ for well-known solutions in the relevant category
- Check popular sources: `vercel-labs/agent-skills`, `ComposioHQ/awesome-claude-skills`

### Step 3 — Search via CLI (if needed)
```bash
npx skills find [query]
```
Use specific keywords first; try alternative terminology if no results.

### Step 4 — Verify quality before recommending
Criteria (in order of priority):
1. Install count: prefer 1,000+ installs
2. Source reputation: known orgs (vercel-labs, mattpocock, etc.)
3. GitHub stars and recent activity (updated in last 6 months)
4. Clear documentation and defined scope

### Step 5 — Present options to user
For each candidate, show:
- Name and one-line description
- Install count
- Installation command
- Why it fits the user's request

### Step 6 — Install upon confirmation
```bash
npx skills add <package> -g -y
```

## Step 7 — Register in memory (REQUIRED after every successful install)

**This goes to Layer 2 — Operational Memory (claude-mem), NOT the structural `.claude/` memory.**
See `memory/memory_architecture.md` for the separation of responsibilities.

After every successful installation, use claude-mem to store an observation in this format:

> Skill installed: **<skill-name>** | Package: `<package>` | Purpose: <one-line description> | Date: <date>

If claude-mem is not yet available, temporarily append to the structural memory file
`C:\Users\Guzman\.claude\projects\c--Users-Guzman-Desktop-Agartha\memory\installed_skills.md`
and migrate the entries to claude-mem once it is installed.

## No Results Scenario
1. Acknowledge that no matching skill was found
2. Offer to solve the task directly with existing tools
3. Suggest creating a custom skill: `npx skills init`

## Expected Output
- Skill installed and confirmed working
- Memory entry recorded in `installed_skills.md`

## Search Categories Reference
| Category | Keywords to try |
|---|---|
| Web Development | scraping, http, fetch, html, browser |
| Testing | test, spec, coverage, e2e, unit |
| DevOps | deploy, docker, ci, pipeline, infra |
| Documentation | docs, readme, openapi, swagger |
| Code Quality | lint, format, refactor, review |
| Productivity | schedule, notify, summarize, search |

## Notes
- Never install a skill without presenting it to the user first (Step 5 confirmation)
- If a skill requires credentials, check `.env` before installing
- Skills installed with `-g` are global; document this in the memory entry
