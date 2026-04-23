# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agartha is a **WAT framework** (Workflows, Agents, Tools) — an AI automation architecture that separates probabilistic reasoning (AI agents) from deterministic execution (Python scripts). This separation is what makes the system reliable: each step in a chain stays at near-100% accuracy because AI handles only orchestration, not implementation.

## Running Tools

Tools are standalone Python scripts. Run them directly:

```bash
python tools/<script_name>.py
```

Credentials are loaded from `.env`. Google OAuth uses `credentials.json` and `token.json` (both gitignored).

## Architecture

```
workflows/      # Markdown SOPs — the entry point for every task
tools/          # Python scripts — deterministic execution layer
.tmp/           # Regenerable intermediates (scraped data, exports)
.env            # All secrets live here exclusively
```

**Execution flow:** Read the relevant `workflows/` file → identify required inputs and tools → execute the corresponding `tools/` script(s) → deliver outputs to cloud services (Google Sheets, Slides, etc.).

**Layer responsibilities:**
- **Workflows** define objective, required inputs, tool sequence, expected outputs, and edge case handling
- **Agent (you)** reads workflows, sequences tool calls, handles failures, and asks clarifying questions when needed
- **Tools** perform the actual work (API calls, data transformations, file operations)

## Operating Rules

**Before building anything new**, check `tools/` for an existing script that covers the task. Only create new scripts when nothing fits.

**On errors:** Read the full trace, fix and retest (check before re-running anything that uses paid API credits), then update the workflow with what you learned (rate limits, batch endpoints, timing quirks).

**On workflows:** Update them as you learn better methods or encounter constraints. Do not create or overwrite workflows without asking unless explicitly told to — they are the persistent instructions for this system.

**On deliverables:** Final outputs go to cloud services. `.tmp/` is disposable. Never store secrets outside `.env`.

## Self-Improvement Loop

When something breaks: identify the failure → fix the tool → verify the fix → update the workflow with the new approach. This is how the framework improves over time.
