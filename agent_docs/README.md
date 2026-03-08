# Agent Documentation (`agent_docs/`)

This directory contains **agent-facing documentation** — files intended for AI coding agents,
not for human readers browsing the project.

## Convention

| Directory | Audience | Published |
|-----------|----------|-----------|
| `docs/` | Human developers | Yes (MkDocs → GitHub Pages) |
| `agent_docs/` | AI agents | No |

**Rule**: If a document is primarily consumed by an AI agent (task definitions, reusable workflow
chunks, progress reports, orchestration procedures), it belongs here. If it's for human developers,
it belongs in `docs/`.

## Structure

```
agent_docs/
  README.md               # This file — explains the convention
  orchestration-guide.md  # How to orchestrate AI coding agents
  mcp-tools.md            # MCP tools reference for agents
  tasks/                  # Task definitions (current + archive)
    archive/              # Completed tasks
  progress/               # Agent progress reports from PRs
  reusable/               # Reusable workflow chunks (included by agent instructions)
  procedures/             # Orchestration procedures (session handoff, QA validation)
```

## Agent Instructions (not here)

Agent role definitions live in `.github/agents/` — GitHub requires that location.
Global agent instructions live in `.github/copilot-instructions.md`.

## For Human Developers

If you're a human developer, start with:
1. [README.md](../README.md) — Project overview and quick start
2. [CONTRIBUTING.md](../CONTRIBUTING.md) — Development workflow and guidelines
3. [docs/](../docs/) — All human-facing documentation
