# Workflow: Generate Optimized Prompt

## Objective
Produce a production-ready, copy-paste prompt for any AI tool using the prompt-master precision framework. Eliminates iterative re-prompting by engineering the prompt correctly on the first attempt.

## Triggers
Activate when the user says things like:
- "Crea un prompt para..."
- "Necesito un prompt que..."
- "Write me a prompt for [tool]"
- "How should I prompt [tool] to..."
- "Dame el mejor prompt para..."

## Required Inputs
- `ANTHROPIC_API_KEY` in `.env`
- `--task`: What the AI tool should accomplish (be specific)
- `--tool`: The target AI platform (Claude, ChatGPT, Cursor, Midjourney, etc.)

## Optional Inputs
- `--context`: Constraints, tech stack, audience, or setup details that affect prompt design
- `--output`: File path to save the generated prompt (default: stdout)

## Tool
`tools/generate_prompt.py`

## Commands

```bash
# Basic: generate a Claude prompt
python tools/generate_prompt.py --task "Extract action items from meeting transcripts" --tool "Claude"

# With context
python tools/generate_prompt.py \
  --task "Generate a React component from a Figma screenshot" \
  --tool "Cursor" \
  --context "TypeScript, Tailwind CSS, shadcn/ui components"

# Image generation
python tools/generate_prompt.py --task "Product shot of a luxury watch on marble" --tool "Midjourney"

# Save to file
python tools/generate_prompt.py \
  --task "Write cold outreach emails for SaaS founders" \
  --tool "ChatGPT" \
  --output .tmp/cold_email_prompt.txt
```

## As a Module
```python
from tools.generate_prompt import generate_prompt
prompt = generate_prompt(task="Summarize legal documents", tool="Claude", context="Focus on liability clauses")
```

## Tool-Specific Notes

| Target Tool | Key Design Rule |
|---|---|
| Claude | XML tags, explicit output format, explain WHY |
| ChatGPT / GPT-4 | Role at top, few-shot examples for format |
| Cursor / Cline | Start state + target state + stop conditions |
| Midjourney | Subject, style, lighting, negative prompts, `::` weights |
| Reasoning models (o3, o4-mini) | Short instructions only — no CoT scaffolding |
| Gemini | Direct task first, grounding anchors |
| Workflow tools (Make, Zapier) | Trigger → condition → action + error branch |

## Edge Cases
- **Missing critical context:** The tool will ask up to 3 clarifying questions before generating. Answer them and re-run.
- **Wrong tool specified:** If unsure of the target tool, specify the task and add `--context "I'm not sure which tool to use"` — the output will include a recommendation.
- **Very long tasks:** Break into sub-tasks and generate a prompt for each step separately.

## Expected Output
A ready-to-paste prompt block labeled with the target tool, plus:
- Template used (RTF, CO-STAR, ReAct, etc.)
- One-sentence optimization rationale
- Setup instructions if credentials or plugins are needed
