# Task 182: Documentation Consolidation Master Plan

**Status**: In Progress
**Branch**: `chore/docs-cleanup`

## Objective
Systematically analyze, consolidate, and prune the project documentation to improve discoverability and maintainability.

## Strategy
Delegate specific clusters of documentation to the `docs-refactorer` agent.

## Sub-Tasks

### 1. Testing & QA Consolidation
- **Scope**: `docs/ai-agents/procedures/` (re: testing), `docs/reference/testing.md`, `docs/reference/e2e-testing-standards.md`, `scripts/quick_e2e_test.sh`
- **Output goal**: A single comprehensive "Testing Strategy" document and simple script references.
- **Agent Task**: `agent_tasks/182a_docs_testing.md`

### 2. Deployment Documentation
- **Scope**: `docs/deployment/*` (Proxmox, domain, etc.)
- **Output goal**: A clear "Deployment Guide" distinguishing between "Production" (Proxmox) and "Local". Archive historical "learnings" if they aren't actionable guides.
- **Agent Task**: `agent_tasks/182b_docs_deployment.md`

### 3. Planning & Roadmap
- **Scope**: `docs/planning/*`
- **Output goal**: Confirm `product-roadmap.md` is the single source of truth. Archive duplicated feature matrices.
- **Agent Task**: `agent_tasks/182c_docs_planning.md`

## Success Criteria
- [ ] No duplicated instructions for running tests.
- [ ] "Single Source of Truth" established for Architecture, Testing, Deployment, and Planning.
- [ ] Broken links fixed.
- [ ] Agent context (token count) reduced by removing redundant text.
