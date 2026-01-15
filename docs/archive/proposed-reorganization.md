# Documentation Reorganization Proposal

**Date**: January 7, 2026
**Task**: #068
**Status**: PARTIALLY IMPLEMENTED

---

## Implementation Status

### ✅ Completed (Quick Wins)

| Item | Action | Date |
|------|--------|------|
| `project_plan.md` | Moved to `docs/planning/` | 2026-01-07 |
| `project_strategy.md` | Moved to `docs/planning/` | 2026-01-07 |
| `.github/copilot-setup.sh` | Deleted (superseded by workflow) | 2026-01-07 |
| `clerk-implementation-info.md` | Moved to `docs/architecture/` | 2026-01-07 |
| `starting_files/` | Moved to `docs/archive/seed-files/` | 2026-01-07 |
| `.tmp_start_agent.sh` | Deleted + `.tmp*` added to gitignore | 2026-01-07 |

### 📋 Deferred (Lower Priority)

- Archiving completed tasks in `agent_tasks/` by phase
- Archiving `agent_progress_docs/` by month
- Moving `orchestrator_procedures/` to `docs/ai-agents/procedures/`
- Creating AI agents documentation hub at `docs/ai-agents/`

---

## Executive Summary

This proposal addresses the organic growth of Zebu's documentation by reorganizing 100+ documents into a clear, maintainable structure. The key goals are:

1. **Reduce confusion** - Clear separation between human docs and AI agent instructions
2. **Improve discoverability** - Logical directory structure with clear navigation
3. **Preserve history** - Archive completed work without deleting valuable context
4. **Enable maintenance** - Distinguish "living" docs from static references

### Recommended Actions

- **Move**: 14 files to new locations
- **Archive**: 78 historical task/progress files
- **Delete**: 1 truly redundant file
- **Update**: 6 files need content updates (separate task)

---

## File Audit

### Root Level Files (8 markdown files)

| File | Size | Purpose | Audience | Status | Recommendation |
|------|------|---------|----------|--------|----------------|
| `README.md` | Main | Project overview, quick start | Human devs | Living | **KEEP** - Essential entry point |
| `PROGRESS.md` | Main | Current status, recent work | Human orchestrator | Living | **KEEP** - Core tracking doc |
| `BACKLOG.md` | Main | Minor improvements, tech debt | Human orchestrator | Living | **KEEP** - Active planning |
| `CONTRIBUTING.md` | Main | Contribution guidelines | Human contributors | Static | **KEEP** - Standard OSS file |
| `project_plan.md` | 200+ lines | Development phases, roadmap | Human + AI | Static | **MOVE** → `docs/planning/project-plan.md` |
| `project_strategy.md` | 200+ lines | Architecture, tech decisions | Human + AI | Static | **MOVE** → `docs/planning/project-strategy.md` |
| `AGENT_ORCHESTRATION.md` | 150+ lines | Orchestrator workflow guide | Human orchestrator | Living | **MOVE** → `docs/ai-agents/orchestration-guide.md` |
| `clerk-implementation-info.md` | 150+ lines | Clerk auth implementation details | Human + AI | Static | **MOVE** → `docs/architecture/clerk-implementation.md` |

**Reasoning**:
- Keep root minimal: README, PROGRESS, BACKLOG, CONTRIBUTING (standard files)
- Move detailed planning/architecture docs to `docs/`
- `AGENT_ORCHESTRATION.md` is AI-focused, belongs in `docs/ai-agents/`
- Clerk doc is technical architecture, not root-level content

### .github/ Directory

| File | Lines | Purpose | Audience | Status | Recommendation |
|------|-------|---------|----------|--------|----------------|
| `copilot-instructions.md` | 238 | Core agent guidelines | AI coding agents | Living | **KEEP** - GitHub Copilot convention |
| `copilot-code-review-instructions.md` | ~100 | Code review guidelines | AI agents | Static | **KEEP** - Specialized instructions |
| `copilot-setup.sh` | 159 | Shell-based environment setup | Human + AI | Redundant | **DELETE** - Replaced by `copilot-setup-steps.yml` |
| `PULL_REQUEST_TEMPLATE.md` | Small | PR template | Human devs | Static | **KEEP** - GitHub convention |
| `agents/*.md` (7 files) | 1535 total | Role-specific agent instructions | AI agents | Living | **KEEP** - Active agent definitions |
| `workflows/README.md` | Small | Workflow documentation | Human + AI | Static | **KEEP** - Standard location |

**Key Finding**: `copilot-setup.sh` is **redundant**
- `copilot-setup-steps.yml` (171 lines) is the **active** file used by GitHub Copilot agents
- The shell script was the original approach, now superseded
- **Action**: DELETE `copilot-setup.sh`, add note in CONTRIBUTING.md about using `task setup` instead

### docs/ Directory (14 files)

| File | Purpose | Audience | Update Freq | Recommendation |
|------|---------|----------|-------------|----------------|
| `README.md` | Index/navigation | All | Living | **UPDATE** - Needs reorganization to match new structure |
| `USER_GUIDE.md` | End-user documentation | Humans | Living | **KEEP** in `docs/` |
| `TESTING_CONVENTIONS.md` | Testing standards | Human + AI | Static | **MOVE** → `docs/development/testing-conventions.md` |
| `EXECUTIVE_SUMMARY.md` | High-level project overview | Stakeholders | Static | **MOVE** → `docs/planning/executive-summary.md` |
| `FEATURE_STATUS.md` | Feature completion tracking | Human orchestrator | Living | **MOVE** → `docs/planning/feature-status.md` |
| `PRODUCT_ROADMAP.md` | Future feature plans | Stakeholders | Static | **MOVE** → `docs/planning/product-roadmap.md` |
| `TECHNICAL_BOUNDARIES.md` | Technical constraints | Developers | Static | **MOVE** → `docs/architecture/technical-boundaries.md` |
| `testing.md` | Testing quick reference | Developers | Static | **MERGE** with `TESTING_CONVENTIONS.md` |
| `external-resources.md` | API docs, framework links | Developers | Static | **MOVE** → `docs/reference/external-resources.md` |
| `mcp-tools.md` | MCP tools reference | AI orchestrator | Static | **MOVE** → `docs/ai-agents/mcp-tools-reference.md` |
| `future-ideas.md` | Feature brainstorming | All | Living | **MOVE** → `docs/planning/future-ideas.md` |
| `progress-archive.md` | Historical PR details | Archive | Archive | **MOVE** → `docs/archive/progress-archive.md` |
| `foundation-evaluation-2026-01-03.md` | Project evaluation snapshot | Archive | Archive | **MOVE** → `docs/archive/foundation-evaluation-2026-01-03.md` |
| `e2e-testing-alpha-vantage-investigation.md` | E2E testing notes | Archive | Archive | **MOVE** → `docs/archive/e2e-testing-alpha-vantage-investigation.md` |

**Duplication Found**: `testing.md` and `TESTING_CONVENTIONS.md` - Merge into one comprehensive guide

### agent_tasks/ Directory (76 files + 2 subdirs)

**Structure**:
- 76 task files: `001_*.md` through `076_*.md`
- `archived/` subdirectory: 2 old task files
- `reusable/` subdirectory: 3 reusable templates

**Analysis**:
- Most tasks (001-067) are **completed** - historical reference only
- Current/future tasks: 068-076
- Tasks serve as **examples** for creating new tasks
- **Value**: Historical context, patterns, task definition examples

**Recommendation**: **Archive completed tasks, keep active + recent + templates**

```
agent_tasks/
├── README.md                    # NEW - Explains structure, how to create tasks
├── active/                      # NEW - Current/future tasks (068-076)
│   ├── 068_docs-organization-proposal.md
│   └── ...
├── templates/                   # RENAME from reusable/
│   ├── README.md
│   ├── e2e_qa_validation.md
│   └── pre-completion-checklist.md
└── archive/                     # EXPAND - Move completed tasks
    ├── phase1/                  # NEW - Organize by phase
    │   ├── 001_setup-backend-project-scaffolding.md
    │   └── ...
    ├── phase2/
    │   └── ...
    └── phase3/
        └── ...
```

**Migration Plan**:
1. Move tasks 001-067 to `archive/phaseN/` based on phase
2. Keep 068-076 in `active/`
3. Rename `reusable/` → `templates/`
4. Create `README.md` explaining structure

### agent_progress_docs/ Directory (72 files)

**Analysis**:
- All files are **historical** - document completed PRs
- Naming: `YYYY-MM-DD_HH-MM-SS_description.md`
- **Value**: PR context, decision rationale, troubleshooting history
- **Problem**: Growing unbounded (72 files, will be 100+)

**Recommendation**: **Archive by month, keep structure**

```
agent_progress_docs/
├── README.md                    # NEW - Explains purpose, when to create
├── 2026-01/                     # Current month - keep accessible
│   ├── 2026-01-06_00-36-04_task056-phase3c-analytics-domain.md
│   └── ...
└── archive/                     # Historical months
    ├── 2025-12/
    │   ├── 2025-12-26_13-30-45_initial-github-agent-setup.md
    │   └── ...
    └── 2026-01/                # Month-end: move here
        └── ...
```

**Migration Plan**:
1. Create `archive/YYYY-MM/` directories
2. Move older months (2025-12) to archive
3. Keep current month (2026-01) at top level or in dated folder
4. Create `README.md` explaining structure

### architecture_plans/ Directory (4 subdirs)

**Structure**:
```
architecture_plans/
├── 20251227_phase1-backend-mvp/
├── 20251228_phase2-market-data/
├── phase3-refined/
└── phase4-refined/
```

**Analysis**:
- Well-organized, phase-based structure
- Mix of date-prefixed (phase 1-2) and name-only (phase 3-4)
- All are **reference** docs, not frequently updated

**Recommendation**: **Keep as-is** - Already well-organized
- Consider: Add `README.md` with index

### orchestrator_procedures/ Directory (7 files)

**Structure**:
```
orchestrator_procedures/
├── README.md
├── e2e_validation.py
├── manual_e2e_testing.md
├── playwright_e2e_testing.md
├── quick_e2e_test.sh
├── run_qa_validation.md
└── session_handoff.md
```

**Analysis**:
- **Active** procedures for orchestrator
- Well-documented in README.md
- Clear purpose: testing, validation, handoffs

**Recommendation**: **MOVE** to `docs/ai-agents/procedures/`
- These are AI agent procedures, not general docs
- Keeps AI-related content together
- More discoverable in unified structure

### starting_files/ Directory (6 files)

**Analysis**:
- `initial-notes.md` - Original project brainstorming
- Agent instruction files (architect, backend-swe, etc.) - Early versions
- `project-plan.md`, `project-strategy.md` - Seed documents
- **Status**: Historical only - project origin story
- **Value**: Context for "why this approach?"

**Recommendation**: **MOVE** to `docs/archive/seed-files/`
- Preserve for historical context
- Remove from active navigation
- Rename directory to clarify purpose

---

## Proposed Directory Structure

```
docs/
├── README.md                          # Updated index with clear navigation
│
├── getting-started/                   # NEW - Onboarding for humans
│   ├── README.md                      # Quick start guide
│   ├── setup.md                       # Detailed setup (from current README)
│   └── local-development.md           # Running locally, common tasks
│
├── planning/                          # NEW - Project planning docs
│   ├── README.md
│   ├── executive-summary.md           # FROM docs/
│   ├── project-plan.md                # FROM root
│   ├── project-strategy.md            # FROM root
│   ├── product-roadmap.md             # FROM docs/
│   ├── feature-status.md              # FROM docs/
│   └── future-ideas.md                # FROM docs/
│
├── architecture/                      # NEW - Technical design docs
│   ├── README.md
│   ├── technical-boundaries.md        # FROM docs/
│   ├── clerk-implementation.md        # FROM root (clerk-implementation-info.md)
│   └── decisions/                     # Future: ADRs
│       └── README.md
│
├── development/                       # NEW - Developer reference
│   ├── README.md
│   ├── testing-conventions.md         # FROM docs/ (merged with testing.md)
│   └── code-quality-standards.md      # Future: From .github/copilot-instructions.md
│
├── reference/                         # NEW - Quick reference docs
│   ├── README.md
│   ├── external-resources.md          # FROM docs/
│   └── user-guide.md                  # FROM docs/USER_GUIDE.md
│
├── ai-agents/                         # NEW - All AI agent docs
│   ├── README.md
│   ├── orchestration-guide.md         # FROM root (AGENT_ORCHESTRATION.md)
│   ├── mcp-tools-reference.md         # FROM docs/mcp-tools.md
│   ├── instructions/                  # Future: Reusable guidance chunks
│   │   └── README.md
│   └── procedures/                    # FROM orchestrator_procedures/
│       ├── README.md
│       ├── e2e_validation.py
│       ├── manual_e2e_testing.md
│       ├── playwright_e2e_testing.md
│       ├── quick_e2e_test.sh
│       ├── run_qa_validation.md
│       └── session_handoff.md
│
└── archive/                           # Historical/read-only docs
    ├── README.md                      # Explains archive purpose
    ├── progress-archive.md            # FROM docs/
    ├── foundation-evaluation-2026-01-03.md  # FROM docs/
    ├── e2e-testing-alpha-vantage-investigation.md  # FROM docs/
    └── seed-files/                    # FROM starting_files/
        ├── README.md                  # Explains origin story
        ├── initial-notes.md
        ├── architect-agent.md
        ├── backend-swe-agent.md
        ├── frontend-swe-agent.md
        ├── project-plan.md
        ├── project-strategy.md
        └── quality-and-infra-agent.md
```

**Top-level directories** (outside `docs/`):
```
.github/                               # GitHub-specific (UNCHANGED)
├── agents/                            # KEEP - Active agent definitions
├── workflows/                         # KEEP - CI/CD
├── copilot-instructions.md            # KEEP - Core agent guidelines
├── copilot-code-review-instructions.md  # KEEP
├── copilot-setup.sh                   # DELETE - Redundant
└── PULL_REQUEST_TEMPLATE.md           # KEEP

agent_tasks/                           # REORGANIZE (see above)
├── README.md                          # NEW
├── active/                            # NEW - Tasks 068+
├── templates/                         # RENAME from reusable/
└── archive/                           # EXPAND - Tasks 001-067 by phase

agent_progress_docs/                   # REORGANIZE (see above)
├── README.md                          # NEW
├── 2026-01/                           # Current month
└── archive/                           # Historical months

architecture_plans/                    # KEEP AS-IS (consider adding README)

docs/                                  # REORGANIZE (see above)

orchestrator_procedures/               # DELETE - Moved to docs/ai-agents/procedures/

starting_files/                        # DELETE - Moved to docs/archive/seed-files/

README.md                              # KEEP - Main entry point
PROGRESS.md                            # KEEP - Active tracking
BACKLOG.md                             # KEEP - Active planning
CONTRIBUTING.md                        # KEEP - Standard OSS
```

---

## Classification by Audience & Update Frequency

### Human Developers (Primary Audience)

**Living Docs** (Updated frequently):
- `README.md` - Project entry point
- `CONTRIBUTING.md` - Contribution guidelines
- `PROGRESS.md` - Current status
- `BACKLOG.md` - Active issues
- `docs/getting-started/` - Onboarding content
- `docs/reference/user-guide.md` - User documentation

**Static/Reference** (Rarely updated):
- `docs/planning/` - Project strategy, roadmap
- `docs/architecture/` - Design decisions
- `docs/development/` - Standards, conventions
- `docs/reference/external-resources.md` - API links

### AI Orchestrator (Human + AI)

**Living Docs**:
- `PROGRESS.md` - Session planning
- `docs/ai-agents/orchestration-guide.md` - Workflow
- `docs/planning/feature-status.md` - Phase tracking
- `agent_tasks/active/` - Current tasks

**Static/Reference**:
- `docs/planning/project-plan.md` - Development phases
- `docs/ai-agents/mcp-tools-reference.md` - Tool reference
- `docs/ai-agents/procedures/` - Testing procedures

### AI Coding Agents

**Living Docs**:
- `.github/copilot-instructions.md` - Core guidelines
- `.github/agents/*.md` - Role-specific instructions
- `architecture_plans/` - Design specs

**Static/Reference**:
- `.github/copilot-code-review-instructions.md` - Review standards
- `docs/development/testing-conventions.md` - Test patterns
- `docs/architecture/` - Technical decisions

### Historical/Archive (All Audiences)

**Read-Only**:
- `docs/archive/` - Historical snapshots
- `agent_tasks/archive/` - Completed tasks
- `agent_progress_docs/archive/` - Old PR docs

---

## Migration Plan

### Phase 1: Preparation (No file moves)

**Tasks**:
1. Create new directory structure under `docs/`
2. Create all `README.md` files for new directories
3. Create `agent_tasks/README.md` and `agent_progress_docs/README.md`
4. Review and approve proposal

**Deliverables**:
- Empty directory structure
- Documentation explaining new organization
- Migration script (optional)

### Phase 2: Archive Historical Content

**Tasks**:
1. Move `agent_tasks/001-067` to `archive/phaseN/`
2. Move `agent_progress_docs/2025-12/` to `archive/2025-12/`
3. Move `starting_files/` to `docs/archive/seed-files/`
4. Move completed docs investigations to `docs/archive/`

**Impact**: Low - Only historical files moved

### Phase 3: Reorganize docs/

**Tasks**:
1. Create subdirectories: `planning/`, `architecture/`, `development/`, `reference/`, `ai-agents/`
2. Move files from `docs/` to new subdirectories
3. Move `orchestrator_procedures/` to `docs/ai-agents/procedures/`
4. Update `docs/README.md` with new structure

**Impact**: Medium - Changes doc paths, needs link updates

### Phase 4: Move Root-Level Files

**Tasks**:
1. Move `project_plan.md` to `docs/planning/`
2. Move `project_strategy.md` to `docs/planning/`
3. Move `AGENT_ORCHESTRATION.md` to `docs/ai-agents/orchestration-guide.md`
4. Move `clerk-implementation-info.md` to `docs/architecture/`
5. Delete `.github/copilot-setup.sh`
6. Update `CONTRIBUTING.md` to reference `task setup` instead of shell script

**Impact**: High - Root-level changes, requires link updates throughout repo

### Phase 5: Update Links & References

**Tasks**:
1. Update all internal links in markdown files
2. Update `.github/copilot-instructions.md` references
3. Update `AGENT_ORCHESTRATION.md` → `orchestration-guide.md` links
4. Update task template references
5. Run link checker to verify

**Impact**: Critical - Ensures no broken links

### Phase 6: Cleanup & Validation

**Tasks**:
1. Remove empty `orchestrator_procedures/` directory
2. Remove empty `starting_files/` directory
3. Verify all links work
4. Update CI/CD if any paths referenced
5. Test agent task creation workflow

**Impact**: Low - Final cleanup

---

## Files Requiring Content Updates

These files need updates **after** reorganization (separate task):

1. **`README.md`** (root)
   - Update "Documentation" section to point to new `docs/` structure
   - Remove reference to `copilot-setup.sh`

2. **`docs/README.md`**
   - Complete rewrite to reflect new directory structure
   - Add navigation guide for different audiences

3. **`CONTRIBUTING.md`**
   - Update setup instructions (remove `copilot-setup.sh` reference)
   - Update documentation section to reflect new structure

4. **`.github/copilot-instructions.md`**
   - Update file path references
   - Update "Related Documentation" section

5. **`docs/ai-agents/orchestration-guide.md`** (formerly `AGENT_ORCHESTRATION.md`)
   - Update all file path references
   - Update "Key Files" section

6. **`agent_tasks/templates/*.md`**
   - Update references section with new paths
   - Update agent task creation examples

---

## Files to Delete

### Confirmed Redundant

1. **`.github/copilot-setup.sh`** (159 lines)
   - **Reason**: Fully superseded by `.github/workflows/copilot-setup-steps.yml`
   - **Evidence**:
     - `copilot-setup-steps.yml` is the active file for GitHub Copilot agents
     - Both do the same thing (setup environment)
     - The YAML workflow is more maintainable and used by CI
   - **Action**: DELETE
   - **Migration**: Update `CONTRIBUTING.md` to reference `task setup` instead

### Potential Merges (Not Deletions)

1. **`docs/testing.md`** + **`docs/TESTING_CONVENTIONS.md`**
   - **Reason**: Overlapping content (both about testing)
   - **Action**: MERGE into single `docs/development/testing-conventions.md`
   - **Review**: Check for unique content in each before merging

---

## Potential Issues & Mitigations

### Issue 1: Broken Links

**Risk**: Moving files breaks internal links throughout repo

**Mitigation**:
1. Use find/replace for common paths
2. Run link checker before/after
3. Test key workflows (agent task creation, setup)
4. Consider: Create symbolic links during transition period

### Issue 2: Agent Confusion

**Risk**: AI agents reference old paths in their instructions

**Mitigation**:
1. Update `.github/copilot-instructions.md` first
2. Update all `.github/agents/*.md` files
3. Add "Files Moved" section to `PROGRESS.md`
4. Test agent task creation with new paths

### Issue 3: CI/CD References

**Risk**: GitHub Actions may reference moved files

**Mitigation**:
1. Search `.github/workflows/` for hardcoded paths
2. Update workflow files if needed
3. Test workflows after migration

### Issue 4: External Documentation

**Risk**: External docs (blog posts, wikis) may link to old paths

**Mitigation**:
1. This is a private repo - lower risk
2. Consider: Add redirects in `README.md` for common paths
3. Document old → new path mappings in migration doc

---

## Benefits of Reorganization

### For Human Developers

**Before**:
- 8 root-level markdown files (which to read first?)
- `docs/` has 14 files in flat structure
- Planning docs scattered (root + docs)

**After**:
- Clean root: README, PROGRESS, BACKLOG, CONTRIBUTING
- `docs/getting-started/` - Clear onboarding path
- `docs/planning/` - All planning in one place
- `docs/development/` - Standards and conventions together

### For AI Orchestrator

**Before**:
- `AGENT_ORCHESTRATION.md` at root (not obvious it's AI-focused)
- Procedures in separate `orchestrator_procedures/` directory
- Task files mixed with completed + active

**After**:
- `docs/ai-agents/` - All AI content together
- Procedures integrated with other AI docs
- `agent_tasks/active/` vs `archive/` - Clear separation

### For AI Coding Agents

**Before**:
- Architecture plans separate from tech boundaries
- Test conventions in `docs/`, standards in `.github/`
- Examples buried in 76 task files

**After**:
- `docs/architecture/` - All design docs together
- `docs/development/` - All standards together
- `agent_tasks/templates/` - Easy to find patterns

### For Project Maintenance

**Before**:
- 100+ files in main navigation
- Historical content mixed with active
- Unclear what's authoritative vs deprecated

**After**:
- ~50 active files in main navigation
- Historical content in `archive/`
- Clear "living" vs "static" designation

---

## Metrics

### Current State
- **Root-level markdown**: 8 files
- **docs/**: 14 files (flat structure)
- **agent_tasks/**: 76 files + 2 subdirs
- **agent_progress_docs/**: 72 files (flat)
- **Total documentation files**: ~170+

### After Reorganization
- **Root-level markdown**: 4 files (README, PROGRESS, BACKLOG, CONTRIBUTING)
- **docs/**: ~50 active files in 6 subdirectories
- **agent_tasks/**: ~10 active files + templates + 66 archived
- **agent_progress_docs/**: Current month + archived by month
- **Total documentation files**: ~170+ (same, but organized)

### Navigation Improvement
- **Before**: Flat structure, unclear purpose
- **After**:
  - 3 levels deep max
  - Clear README at each level
  - Logical grouping by purpose
  - Archived content hidden from main navigation

---

## Open Questions

1. **Architecture Plans**: Should `architecture_plans/` move to `docs/architecture/plans/`?
   - **Pro**: All architecture docs together
   - **Con**: Plans are large, might clutter `docs/architecture/`
   - **Recommendation**: Keep separate at root for now, monitor

2. **Agent Instructions**: Should `.github/agents/` content be duplicated/linked in `docs/ai-agents/`?
   - **Pro**: Single source of truth for AI docs
   - **Con**: GitHub convention is to keep agent definitions in `.github/`
   - **Recommendation**: Keep in `.github/`, reference from `docs/ai-agents/README.md`

3. **Versioning**: Should we version architecture_plans or keep date-based naming?
   - **Current**: Mix of dates (`20251227_`) and names (`phase3-refined`)
   - **Recommendation**: Standardize on `phaseN-topic` naming for clarity

4. **Progress Docs Lifecycle**: When to archive agent_progress_docs?
   - **Options**: Monthly, quarterly, by phase
   - **Recommendation**: Monthly archive (matches current date format)

---

## Next Steps

1. **Review & Approve**: Get feedback on this proposal
2. **Create Migration Task**: Break into implementable chunks
3. **Execute Phase 1**: Create directory structure
4. **Execute Phases 2-6**: Migrate files incrementally
5. **Update Documentation**: Fix all links and references
6. **Validate**: Test agent workflows, check for broken links

---

## Appendix: Quick Reference Tables

### Files Being Moved

| From | To | Reason |
|------|-----|--------|
| `project_plan.md` | `docs/planning/project-plan.md` | Planning content |
| `project_strategy.md` | `docs/planning/project-strategy.md` | Planning content |
| `AGENT_ORCHESTRATION.md` | `docs/ai-agents/orchestration-guide.md` | AI-specific |
| `clerk-implementation-info.md` | `docs/architecture/clerk-implementation.md` | Architecture |
| `docs/EXECUTIVE_SUMMARY.md` | `docs/planning/executive-summary.md` | Planning |
| `docs/FEATURE_STATUS.md` | `docs/planning/feature-status.md` | Planning |
| `docs/PRODUCT_ROADMAP.md` | `docs/planning/product-roadmap.md` | Planning |
| `docs/TECHNICAL_BOUNDARIES.md` | `docs/architecture/technical-boundaries.md` | Architecture |
| `docs/TESTING_CONVENTIONS.md` | `docs/development/testing-conventions.md` | Development |
| `docs/external-resources.md` | `docs/reference/external-resources.md` | Reference |
| `docs/mcp-tools.md` | `docs/ai-agents/mcp-tools-reference.md` | AI-specific |
| `docs/future-ideas.md` | `docs/planning/future-ideas.md` | Planning |
| `docs/USER_GUIDE.md` | `docs/reference/user-guide.md` | Reference |
| `orchestrator_procedures/*` | `docs/ai-agents/procedures/*` | AI-specific |

### Files Being Archived

| From | To | Reason |
|------|-----|--------|
| `starting_files/*` | `docs/archive/seed-files/*` | Historical |
| `docs/progress-archive.md` | `docs/archive/progress-archive.md` | Historical |
| `docs/foundation-evaluation-2026-01-03.md` | `docs/archive/foundation-evaluation-2026-01-03.md` | Historical |
| `docs/e2e-testing-alpha-vantage-investigation.md` | `docs/archive/e2e-testing-alpha-vantage-investigation.md` | Historical |
| `agent_tasks/001-067` | `agent_tasks/archive/phaseN/` | Completed |
| `agent_progress_docs/2025-12/*` | `agent_progress_docs/archive/2025-12/*` | Historical |

### Files Being Deleted

| File | Reason | Replaced By |
|------|--------|-------------|
| `.github/copilot-setup.sh` | Redundant | `.github/workflows/copilot-setup-steps.yml` |
| `docs/testing.md` | Duplicate | Merged into `TESTING_CONVENTIONS.md` |

---

**End of Proposal**
