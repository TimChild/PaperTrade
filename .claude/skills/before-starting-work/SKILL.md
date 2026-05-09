---
name: before-starting-work
description: Pre-work checklist for any non-trivial task in this repo. Surfaces recent agent activity, open PRs, architecture docs, and project context before you start coding.
---

# Before Starting Work

Run these checks before beginning implementation work in Zebu.

## 1. Recent agent activity

```bash
ls -lt agent_docs/progress/ | head -10
find agent_docs/progress/ -name "*<keyword>*"
```

If recent progress mentions the same area, read those reports — there may be context, decisions, or follow-up items.

## 2. Open PRs

```bash
GH_PAGER="" gh pr list
```

Look for PRs touching the same files / features. Coordinate to avoid merge conflicts.

## 3. Architecture docs

```bash
ls -la docs/architecture/
ls -lt agent_docs/tasks/ | head -10
```

If a task spec exists for the feature you're working on at `agent_docs/tasks/NNN_*.md`, **implement it as written** — don't deviate without explicit approval.

## 4. Current code state

For a feature you're about to extend or modify:

```bash
find . -name "*<concept>*" -type f
grep -r "class <ConceptName>" --include="*.py"
```

Understand existing patterns and tests before writing new code.

## 5. Project context

Skim:

- `CLAUDE.md` — top-level conventions
- `PROGRESS.md` — current phase, recent work
- `docs/planning/agent-platform-proposal.md` — active forward plan
- `agent_docs/tasks/` — open numbered task specs (the next is **211**)

## Quick-start one-liner

```bash
GH_PAGER="" gh pr list && \
  ls -lt agent_docs/progress/ | head -5 && \
  ls -la docs/architecture/ && \
  echo "✓ Pre-work checks complete"
```

## When to skip

- Pure formatting / typo fixes
- Adding a single test for existing behavior
- One-line bug fixes with obvious root cause

For everything else, run the checks. Two minutes here saves an hour of misaligned work.
