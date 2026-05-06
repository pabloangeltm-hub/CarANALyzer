# Shared Agent Instructions

This file is the shared operating contract for every coding agent working in this repository, including Codex and Claude Code.

## Startup Checklist

Before changing files:
- Read `CLAUDE.md` for project-specific architecture and workflow rules.
- Read `.agents/coordination.md` for active tasks, ownership, locks, and handoffs.
- Run `git status --short` and treat existing changes as user or peer-agent work.
- Do not revert, overwrite, reformat, or relocate files touched by another agent unless the coordination file explicitly assigns that work to you.

## Coordination Protocol

Use `.agents/coordination.md` as the shared work log.

When starting a task:
- Add or update an entry under `Active Tasks`.
- Claim clear ownership of files, directories, or responsibility areas.
- Add temporary locks for files you expect to edit.

While working:
- Keep changes inside your claimed scope.
- If you discover that another agent owns a needed file, stop and leave a handoff note instead of editing through it.
- Prefer narrow, reviewable changes over broad refactors.

Before finishing:
- Update the task status and summarize changed files.
- Remove locks you no longer need.
- Record commands/tests run and any failures.
- Add a handoff note when another agent should continue from your work.

## Suggested Role Split

Default Codex role:
- Implementation, repo navigation, precise patches, test execution, debugging, and final integration.

Default Claude Code role:
- Architecture review, workflow design, product reasoning, broad refactor planning, documentation, and independent code review.

Either agent may do any task when explicitly assigned, but concurrent work should use disjoint file ownership.

## Conflict Rules

- One file should have one active editing owner at a time.
- If a file is locked, do not edit it unless the lock owner has handed it off.
- If a task needs overlapping files, coordinate through `.agents/coordination.md` first.
- Never use destructive git commands to resolve coordination problems.
- Prefer worktrees or separate branches for large parallel tasks.

## Project Rules

- Tools live in `tools/` and workflows live in `workflows/`.
- Check existing tools before creating new scripts.
- Secrets must stay in `.env` only.
- `.tmp/` is disposable and should not be treated as source of truth.
- Final deliverables usually go to cloud services, not local scratch files.
