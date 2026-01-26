# Task 185: Documentation Consolidation Round 2

**Status**: In Progress
**Branch**: `chore/docs-cleanup-round-2`

## Objective
Continue the systematic consolidation of documentation, focusing on Monitoring and Architecture sectors to reduce fragmentation and improve discoverability.

## Sub-Tasks

### 1. Monitoring Consolidation
- **Scope**: `docs/monitoring/` (dashboards, alert config, runbooks).
- **Current State**: Fragmented across `dashboards/` folders and loose markdown files.
- **Goal**: Unified `docs/monitoring/README.md` that links to or contains all relevant operational info. Archive or delete low-value JSON descriptors if not actively used by humans (or move to `infra/`).
- **Agent Task**: `agent_tasks/185a_docs_monitoring.md`

### 2. Architecture Consolidation
- **Scope**: `docs/architecture/` and `docs/architecture/phase4-refined/` and `technical-boundaries.md`.
- **Current State**: Confusing mix of "current" status in `phase4-refined` and root files.
- **Goal**: Move the "current" architecture to `docs/architecture/README.md` or `docs/architecture/overview.md`. Ensure top-level discoverability.
- **Agent Task**: `agent_tasks/185b_docs_architecture.md`

## Success Criteria
- [ ] `docs/monitoring` is navigable from a single entry point.
- [ ] `docs/architecture` clearly states the *current* architecture without needing to dig into subfolders.
- [ ] Redundant files deleted.
