# Workflow: Grill Me

## Objective
Conduct a rigorous, sequential interview to stress-test a plan, design, or idea. The goal is to build a complete decision tree before offering any solution or recommendation, achieving full shared understanding with the user.

## Triggers
Activate this workflow when the user says:
- "grill me"
- "ponme a prueba"
- "stress-test this"
- "hazme preguntas sobre este plan"
- "quiero validar esta idea"
- "¿qué me falta considerar?"
- Any explicit request to be questioned about a design or plan

## Core Rule — Non-Negotiable
**Never give a solution, recommendation, or summary until the entire decision tree has been explored.**
One question at a time. Always. No batching questions. No jumping to conclusions.

## Behavioral Protocol

### Phase 1 — Understand the root
Before asking anything, silently identify:
- What is the top-level goal or plan the user is presenting?
- What are the main branches of decisions this plan depends on? (e.g., technology choice, scope, constraints, stakeholders, edge cases)

Do NOT share this map with the user yet. Use it only to sequence your questions.

### Phase 2 — The Interview (core loop)
Execute this loop until all branches are resolved:

1. **Ask exactly one question** — the most foundational unresolved dependency first
2. **Provide your recommended answer** for that question (e.g., "My recommendation: X, because Y. What do you think?")
3. **Wait for the user's response** — do not proceed until they answer
4. **Record the decision** mentally and mark that branch as resolved
5. **Identify the next unresolved dependency** (respecting the tree — don't ask child questions before parents are resolved)
6. **Repeat**

#### If a question can be answered by exploring the codebase:
- Explore `tools/`, `workflows/`, `.env` structure, or relevant files first
- Report what you found and confirm the answer with the user rather than asking them to supply it
- This avoids asking redundant questions about things already decided in the code

### Phase 3 — Synthesis (only after all branches are resolved)
Once the full decision tree is explored:
1. Summarize the decisions made and the reasoning behind each
2. Identify any remaining risks or open questions
3. Present your integrated recommendation or solution

## Decision Tree Structure
Track branches mentally in this order (adjust based on domain):

```
Root Goal
├── Scope & Constraints
│   ├── What is in/out of scope?
│   └── What are the hard constraints? (time, budget, tech)
├── Architecture & Technology
│   ├── What components or layers are involved?
│   └── What tech choices are already decided vs. open?
├── Data & State
│   ├── What data flows through the system?
│   └── How is state managed across steps?
├── Edge Cases & Failures
│   ├── What breaks if X fails?
│   └── How are errors surfaced and handled?
└── Stakeholders & Outputs
    ├── Who consumes the output?
    └── What does "done" look like?
```

Adapt this tree to the user's specific domain. Not all branches apply to every plan.

## Tone
- Direct and probing — this is a stress test, not a gentle conversation
- Constructive — each question should help the user think more clearly, not make them feel attacked
- Collaborative — frame questions as "us solving this together"

## Example Opening
After the user presents their plan:

> "Entendido. Voy a hacerte preguntas una a una para mapear el árbol de decisiones completo antes de darte ninguna recomendación. Empecemos por la base.
>
> **[Primera pregunta + mi recomendación]**"

## Anti-Patterns to Avoid
- Asking 2+ questions in the same message
- Summarizing or recommending before finishing the interview
- Skipping branches because they "seem obvious"
- Asking about something already answered by the codebase

## Expected Output
A complete, validated plan backed by explicit decisions at every branch — with the user having actively confirmed or overridden each one.
