# Agent Documentation (`agent_docs/`)

Workspace for AI-agent task tracking and progress reports. Not published to the docs site.

## Convention

| Directory | Audience | Published |
|---|---|---|
| `docs/` | Human developers | Yes (MkDocs → GitHub Pages) |
| `agent_docs/` | AI agents (task workspace) | No |
| `.claude/agents/` | Specialist agent definitions | No |
| `.claude/skills/` | Project-local skills (procedural knowledge) | No |
| `CLAUDE.md` (root) | Top-level project conventions for Claude | No |

## Structure

```
agent_docs/
  README.md          # This file
  mcp-tools.md       # MCP tools reference for development sessions
  tasks/             # Numbered task specs (NNN_short_name.md)
    archive/         # Completed / superseded tasks
  progress/          # Dated session reports (YYYY-MM-DD_HH-MM-SS_*.md)
```

## Task workflow

1. Write a spec at `agent_docs/tasks/NNN_short_name.md` (next number is **211** — most recent is `210_live_strategy_execution.md`)
2. Spec sections: Overview, Context, Architecture, Implementation Plan, Testing Strategy, Success Criteria, Agent Assignment, References
3. After completion, write a progress report at `agent_docs/progress/YYYY-MM-DD_HH-MM-SS_short-description.md`

## For human developers

Start with:

1. [CLAUDE.md](../CLAUDE.md) — top-level project conventions
2. [README.md](../README.md) — project overview and quick start
3. [CONTRIBUTING.md](../CONTRIBUTING.md) — development workflow
4. [docs/](../docs/) — published human-facing documentation
5. [docs/planning/agent-platform-proposal.md](../docs/planning/agent-platform-proposal.md) — active forward plan
