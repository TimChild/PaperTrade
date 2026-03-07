# Task 127: Documentation Reorganization

**Agent**: quality-infra (or refactorer)
**Priority**: Medium
**Estimated Complexity**: Medium
**Dependencies**: None

## Objective

Clean up and reorganize the documentation structure, especially at the root level. Eliminate duplicates, properly categorize files, and ensure a clear, navigable documentation hierarchy.

## Background

The repository currently has ~323 markdown files across various directories. Several documentation files exist both at the root level and in the `docs/` directory, creating confusion about which is authoritative. Some files may be outdated or poorly categorized.

## Scope

### Files to Address

**Root-level duplicates** (compare with docs/ versions and pick authoritative):
- `AGENT_ORCHESTRATION.md` (also in `docs/project-management/`)
- `EXECUTIVE_SUMMARY.md` (also in `docs/project-management/`)
- `PRODUCT_ROADMAP.md` (also in `docs/planning/`)
- `TECHNICAL_BOUNDARIES.md` (also in `docs/architecture/`)

**Files needing evaluation/categorization**:
- `docs/proposed-reorganization.md`
- `docs/foundation-evaluation.md`
- `docs/progress-archive.md`
- `docs/testing.md`
- `docs/future-ideas.md`
- `PROGRESS.md` (root level)
- `BACKLOG.md` (root level)
- `resume-from-here.md` (root level)

### Tasks

1. **Compare duplicates**: For each file that exists both at root and in docs/, compare content and determine which is more current/authoritative
2. **Consolidate**: Keep the authoritative version in the appropriate docs/ subdirectory, remove duplicates
3. **Categorize miscellaneous files**: Review files like `proposed-reorganization.md`, `foundation-evaluation.md`, etc. and either:
   - Archive if outdated/completed
   - Move to appropriate category
   - Delete if no longer relevant
4. **Check cross-references**: Scan for any internal links to moved/deleted files and update them
5. **Update documentation index**: Ensure `docs/README.md` (or similar) accurately reflects the new structure

## Acceptance Criteria

- [ ] No duplicate documentation files between root and docs/ directory
- [ ] All documentation files properly categorized in docs/ subdirectories
- [ ] Dated/completed documentation archived or removed
- [ ] No broken internal links
- [ ] Clear documentation hierarchy reflected in docs/README.md or similar

## Implementation Notes

- Preserve git history where possible (use `git mv` for moves)
- When comparing duplicates, check:
  - Last modified date
  - Content completeness
  - References from other files
- Consider creating a `docs/archive/` directory for historical but non-current docs
- Root level should only contain: README.md, CONTRIBUTING.md, and possibly LICENSE

## Testing

- [ ] All internal documentation links work
- [ ] Documentation structure is clear and logical
- [ ] No orphaned files

## Related

- This addresses the documentation cleanup request from the CTO/senior SWE
- Should make it easier for new developers to navigate the project
