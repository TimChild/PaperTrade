# Task 194: Documentation Reorganization

**Agent**: quality-infra
**Priority**: Medium
**Estimated Effort**: 3-4 hours

## Objective

Reorganize documentation into a clear two-tier structure: human-facing docs (`docs/`) and agent-facing docs (`agent_docs/`). Add MkDocs configuration for the human-facing docs.

## Problem

Documentation is spread across multiple locations with unclear boundaries:
- `docs/` — Mix of human-readable docs and agent-specific content (e.g., `docs/ai-agents/`)
- `agent_tasks/` — Task files, progress docs, reusable workflow chunks
- Root-level: `PROGRESS.md`, `BACKLOG.md`, `resume-from-here.md`, `CONTRIBUTING.md`

## Decisions (Already Made)

- **Use `agent_docs/`** as the new agent-facing directory name
- **Keep `BACKLOG.md` and `PROGRESS.md` at root** — shared between humans and agents
- **Remove `resume-from-here.md`** — it duplicates PROGRESS.md; just keep PROGRESS.md updated
- **Use `mkdocs-material` theme** for the docs site
- **Deploy to GitHub Pages** (free, zero maintenance vs running on Proxmox)

## Target Structure

### `docs/` — Human-Facing Documentation (published via MkDocs)

```
docs/
  index.md                    # Project overview (adapted from README.md)
  user-guide.md               # How to use the app
  architecture/               # System architecture, design decisions
  deployment/                 # Production deployment guides
  planning/                   # Roadmap, features, strategy
  reference/                  # External resources, API docs
  design-system/              # UI/UX design guidelines
  monitoring/                 # Observability setup
  testing/                    # Testing strategy (human-readable)
  archive/                    # Old docs kept for reference
```

### `agent_docs/` — Agent-Facing Documentation (NEW, not published)

```
agent_docs/
  README.md                   # Explains this directory to agents
  tasks/                      # Task definitions (from agent_tasks/)
    archive/                  # Completed tasks
  progress/                   # Agent progress reports (from agent_tasks/progress/)
  reusable/                   # Reusable workflow chunks (from agent_tasks/reusable/)
  procedures/                 # Orchestration procedures (from docs/ai-agents/procedures/)
  orchestration-guide.md      # From docs/ai-agents/orchestration-guide.md
  mcp-tools.md                # From docs/ai-agents/mcp-tools.md
```

### Root Level (unchanged)

```
.github/agents/               # Agent role definitions (GitHub requires this location)
.github/copilot-instructions.md  # Global agent instructions (GitHub requires this)
BACKLOG.md                    # Shared human + agent
PROGRESS.md                   # Shared human + agent
CONTRIBUTING.md               # Human-facing
README.md                     # Human-facing
```

## Implementation Steps

### 1. Create `agent_docs/` structure and move files
- Create `agent_docs/` with subdirectories
- Move `agent_tasks/*.md` → `agent_docs/tasks/`
- Move `agent_tasks/archive/` → `agent_docs/tasks/archive/`
- Move `agent_tasks/progress/` → `agent_docs/progress/`
- Move `agent_tasks/reusable/` → `agent_docs/reusable/`
- Move `docs/ai-agents/procedures/` → `agent_docs/procedures/`
- Move `docs/ai-agents/orchestration-guide.md` → `agent_docs/orchestration-guide.md`
- Move `docs/ai-agents/mcp-tools.md` → `agent_docs/mcp-tools.md`
- Delete `resume-from-here.md` (content should be in PROGRESS.md)
- Write `agent_docs/README.md` explaining the convention

### 2. Update all references
- `.github/copilot-instructions.md` — update all paths referencing `agent_tasks/` or `docs/ai-agents/`
- `.github/agents/*.md` — update any path references
- `agent_docs/reusable/*.md` — update internal cross-references
- `CONTRIBUTING.md` — update if it references docs locations

### 3. Clean up `docs/` for human readers
- Remove `docs/ai-agents/` (content moved to `agent_docs/`)
- Ensure remaining content in `docs/` is human-oriented
- Move any remaining agent-specific content out

### 4. Add MkDocs configuration
- Create `mkdocs.yml` at repo root with mkdocs-material theme
- Configure navigation based on `docs/` structure
- Add `.github/workflows/docs.yml` to deploy to GitHub Pages on push to main
- Ensure `agent_docs/` is excluded from the docs site

### 5. Add convention rule to copilot-instructions.md
Add this to the global instructions:
```
## Documentation Convention
- Human-facing docs go in `docs/` (published via MkDocs)
- Agent workflow docs go in `agent_docs/` (tasks, progress, reusable chunks)
- Do not mix them. If in doubt, it's agent-facing.
```

## Validation
- All existing tests still pass (no code changes)
- All agent file references resolve correctly (grep for old paths)
- MkDocs builds without errors: `mkdocs build`
- No broken links in docs
- `agent_docs/README.md` clearly explains the convention

## Important Notes
- `.github/agents/*.md` MUST stay where they are — GitHub requires this location
- `.github/copilot-instructions.md` MUST stay where it is — GitHub requires this
- Do NOT add MkDocs dependencies to the backend or frontend — use a standalone install or GitHub Action
- The MkDocs GitHub Pages workflow should use `pip install mkdocs-material` in CI
