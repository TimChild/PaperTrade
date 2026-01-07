# Task 068: Documentation Organization Proposal

**Agent**: architect
**Priority**: Medium
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-07

## Objective

Analyze the current documentation structure and propose a reorganization that:
1. Identifies redundant/obsolete files
2. Organizes docs under `docs/` with clear subdirectories
3. Makes it clear which docs are for humans vs AI agents
4. Distinguishes "living" docs from historical/archive docs

**This is a PROPOSAL task only** - do not implement changes. Create a proposal document.

## Context

The repo has grown organically and documentation is scattered:
- Root level: `README.md`, `PROGRESS.md`, `BACKLOG.md`, `project_plan.md`, `project_strategy.md`, `AGENT_ORCHESTRATION.md`, `CONTRIBUTING.md`, `clerk-implementation-info.md`
- `.github/`: `copilot-instructions.md`, `copilot-setup.sh`, `copilot-code-review-instructions.md`, `agents/*.md`
- `docs/`: Mixed user guides, technical docs, and archives
- `agent_tasks/`: Historical task files (67+), plus `reusable/` and `archived/`
- `architecture_plans/`: Phase-specific design docs
- `orchestrator_procedures/`: Testing and handoff procedures
- `starting_files/`: Original project notes (historical)

### Known Issues
1. `.github/copilot-setup.sh` - Likely redundant now that `copilot-setup-steps.yml` handles agent setup
2. `starting_files/` - Historical only, was the seed for the project
3. `clerk-implementation-info.md` in root - Should be in docs or archived
4. `agent_tasks/*.md` - 67 files, most are historical (completed tasks)
5. Duplication between `AGENT_ORCHESTRATION.md`, `.github/copilot-instructions.md`, and individual agent files

## Requirements

### 1. File Audit

Review each of these locations and categorize files:
- **Keep as-is**: Essential files in correct location
- **Move**: Files that belong elsewhere
- **Archive**: Historical files to preserve but move out of active paths
- **Delete**: Truly redundant files (be conservative!)

Files to specifically investigate:
```
.github/copilot-setup.sh          # Is this still used? Compare to copilot-setup-steps.yml
clerk-implementation-info.md      # Should this be in docs/archive?
starting_files/                   # Archive or keep for reference?
orchestrator_procedures/          # Still used? Should merge with docs/?
```

### 2. Proposed Directory Structure

Design a `docs/` structure like:
```
docs/
├── README.md              # Index/navigation
├── getting-started/       # Onboarding for humans
├── reference/             # Technical reference docs
├── ai-agents/             # All agent-related docs
│   ├── instructions/      # Reusable guidance chunks
│   └── procedures/        # How to do specific tasks
├── architecture/          # Design documents
└── archive/               # Historical docs (read-only)
```

### 3. Human vs AI Classification

For each major doc, identify:
- **Primary audience**: Human developers, AI orchestrators, AI coding agents
- **Update frequency**: Living (frequent updates) vs Static (rarely changes)
- **Purpose**: Reference, guide, historical record

### 4. Deliverable

Create a proposal document at: `docs/proposed-reorganization.md`

Include:
1. Summary of findings from file audit
2. Recommended directory structure with rationale
3. Migration plan (what moves where)
4. List of files to delete (with justification)
5. List of files that need content updates (just identify, don't fix)

## Success Criteria

- ✅ All root-level markdown files reviewed
- ✅ All `.github/` files reviewed
- ✅ Clear proposal for `docs/` structure
- ✅ Explicit recommendations for redundant files
- ✅ Classification of docs by audience and update frequency
- ✅ Proposal document created (not implementation)

## References

- Current docs index: `docs/README.md`
- Orchestration guide: `AGENT_ORCHESTRATION.md`
- Agent instructions: `.github/copilot-instructions.md`

## Notes

- Be conservative with deletions - prefer archiving
- Consider that `agent_tasks/` files serve as examples for new tasks
- The goal is better organization, not just fewer files
