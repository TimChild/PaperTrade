# Task: Documentation Reorganization

**Status**: DRAFT / TODO — Not ready for execution yet
**Agent**: docs-refactorer (or orchestrator)
**Priority**: Medium (backlog)
**Estimated Effort**: 4-6 hours

## Objective

Reorganize documentation into a clear two-tier structure: human-facing docs and agent-facing docs. Establish a documentation strategy that every agent will immediately understand and follow.

## Problem

Documentation is currently spread across multiple locations with unclear boundaries:
- `docs/` — Mix of human-readable docs and agent-specific content (e.g., `docs/ai-agents/`)
- `agent_tasks/` — Task files, progress docs, reusable workflow chunks
- `agent_tasks/reusable/` — Agent instructions that are referenced by `.github/agents/*.md`
- `.github/agents/` — Agent role definitions (these are fine where they are)
- `.github/copilot-instructions.md` — Global agent instructions
- Root-level: `PROGRESS.md`, `BACKLOG.md`, `resume-from-here.md`, `CONTRIBUTING.md`

Agents frequently create/modify docs in inconsistent locations. We need a clear, enforceable convention.

## Proposed Structure

### `docs/` — Human-Facing Documentation
Published via MkDocs. Everything here should be useful to a human reader.

```
docs/
  index.md                    # was README.md
  user-guide.md               # how to use the app
  architecture/               # system architecture, design decisions
  deployment/                 # production deployment guides
  planning/                   # roadmap, features, strategy
  reference/                  # external resources, API docs
  design-system/              # UI/UX design guidelines
  monitoring/                 # observability setup
  testing/                    # testing strategy (human-readable)
  archive/                    # old docs kept for reference
```

### `agent_docs/` — Agent-Facing Documentation (NEW)
Everything agents need to plan, execute, and track work. NOT published to MkDocs.

```
agent_docs/
  README.md                   # Explains this directory to agents
  tasks/                      # Task definitions (currently agent_tasks/)
    192_backend_quality_fixes.md
    193_frontend_ux_improvements.md
    archive/                  # Completed tasks
  progress/                   # Agent progress reports (currently agent_tasks/progress/)
  reusable/                   # Reusable workflow chunks (currently agent_tasks/reusable/)
    architecture-principles.md
    before-starting-work.md
    git-workflow.md
    quality-and-tooling.md
    e2e_qa_validation.md
    agent-progress-docs.md
  procedures/                 # Orchestration procedures (currently docs/ai-agents/procedures/)
  orchestration-guide.md      # How agents coordinate (currently docs/ai-agents/orchestration-guide.md)
  mcp-tools.md                # MCP tool reference (currently docs/ai-agents/mcp-tools.md)
```

### Root Level
```
.github/
  agents/                     # Agent role definitions (unchanged)
  copilot-instructions.md     # Global agent instructions (unchanged, but update refs)
BACKLOG.md                    # Keep — human + agent shared
PROGRESS.md                   # Keep — human + agent shared
CONTRIBUTING.md               # Keep — human-facing
README.md                     # Keep — human-facing
resume-from-here.md           # Move to agent_docs/ (agent-facing)
```

## Key Decisions to Make

- [ ] Confirm `agent_docs/` as the name (alternatives: `agent_tasks/`, `.agent/`, `ai/`)
- [ ] Should `BACKLOG.md` and `PROGRESS.md` stay at root or move to `docs/planning/`?
- [ ] Should `resume-from-here.md` be kept? It duplicates info from PROGRESS.md
- [ ] MkDocs: do we want to use `mkdocs-material` theme?
- [ ] MkDocs deployment: static site on proxmox VM or GitHub Pages?

## Migration Checklist (for execution)

- [ ] Create `agent_docs/` directory structure
- [ ] Move `agent_tasks/` contents → `agent_docs/tasks/`
- [ ] Move `agent_tasks/reusable/` → `agent_docs/reusable/`
- [ ] Move `agent_tasks/progress/` → `agent_docs/progress/`
- [ ] Move `docs/ai-agents/` → `agent_docs/`
- [ ] Update all references in `.github/agents/*.md` files
- [ ] Update `.github/copilot-instructions.md` references
- [ ] Add clear README.md to `agent_docs/` explaining the convention
- [ ] Add `mkdocs.yml` configuration
- [ ] Deploy MkDocs site to proxmox
- [ ] Update BACKLOG.md to reflect completion

## Notes

- `.github/agents/*.md` files MUST stay where they are — GitHub requires this location
- `.github/copilot-instructions.md` MUST stay where it is — GitHub requires this
- The key principle: if it's for human consumption → `docs/`. If it's for agent workflow → `agent_docs/`
- MkDocs should ignore `agent_docs/` completely
- Consider adding a simple rule to copilot-instructions.md: "Human docs go in `docs/`. Agent workflow docs go in `agent_docs/`. Do not mix them."

## References
- Current docs overview: `docs/README.md`
- Agent task README: `agent_tasks/reusable/README.md`
- MkDocs Material: https://squidfoss.github.io/mkdocs-material/
