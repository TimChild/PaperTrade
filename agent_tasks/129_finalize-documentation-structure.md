# Task 129: Finalize Documentation Structure

**Agent**: quality-infra or refactorer
**Priority**: Medium
**Estimated Complexity**: Low
**Dependencies**: Completes Task 127 (PR #129 merged)

## Objective

Complete the documentation reorganization by moving remaining top-level docs/ files into appropriate subdirectories and consolidating overlapping testing documentation.

## Background

PR #129 successfully cleaned up the root directory and created new categorization (`ai-agents/`, `reference/`, `archive/`). However, several documentation files remain at the `docs/` top level that should be categorized into subdirectories for better organization.

## Scope

### Files to Relocate

**Move to `docs/planning/`**:
- `docs/EXECUTIVE_SUMMARY.md` → `docs/planning/executive-summary.md`
- `docs/PRODUCT_ROADMAP.md` → `docs/planning/product-roadmap.md`
- `docs/FEATURE_STATUS.md` → `docs/planning/feature-status.md`

**Move to `docs/architecture/`**:
- `docs/TECHNICAL_BOUNDARIES.md` → `docs/architecture/technical-boundaries.md`

**Move to `docs/reference/`**:
- `docs/E2E_TESTING_STANDARDS.md` → `docs/reference/e2e-testing-standards.md`
- `docs/TESTING_CONVENTIONS.md` → `docs/reference/testing-conventions.md`
- `docs/QA_ACCESSIBILITY_GUIDE.md` → `docs/reference/qa-accessibility-guide.md`

**Keep at docs/ root**:
- `docs/README.md` - navigation index
- `docs/USER_GUIDE.md` - high-visibility end-user documentation

### Testing Documentation Consolidation

Review and consolidate if there's overlap between:
- `docs/reference/e2e-testing-standards.md` (after move)
- `docs/reference/testing-conventions.md` (after move)
- `docs/reference/testing.md` (existing)

**Options**:
1. Keep all three if they serve distinct purposes (standards, conventions, quick reference)
2. Merge into comprehensive `docs/reference/testing-guide.md` if there's significant overlap
3. Create cross-references if content is complementary

### Update References

After moves, update all internal links in:
- `docs/README.md` - update navigation table
- `.github/copilot-instructions.md` - if it references these files
- `CONTRIBUTING.md` - if it references these files
- Any other files that link to the moved documentation

## Tasks

1. **Use `git mv` for all file moves** to preserve git history
2. **Rename files to lowercase-with-hyphens** convention (e.g., `EXECUTIVE_SUMMARY.md` → `executive-summary.md`)
3. **Review testing docs** for overlap and consolidate if appropriate
4. **Update all cross-references** to point to new locations
5. **Update `docs/README.md`** navigation table
6. **Verify no broken links** exist after moves

## Acceptance Criteria

- [ ] Only `README.md` and `USER_GUIDE.md` remain at `docs/` root level
- [ ] All planning docs consolidated in `docs/planning/`
- [ ] All architecture docs in `docs/architecture/`
- [ ] All reference/testing docs in `docs/reference/`
- [ ] No duplicate/overlapping testing documentation
- [ ] All internal links updated and working
- [ ] `docs/README.md` navigation table reflects new structure
- [ ] File naming follows lowercase-with-hyphens convention

## Implementation Notes

- Preserve git history with `git mv`
- Check each file for last-modified date and relevance before moving
- Consider adding sections to subdirectory README.md files to explain contents
- The goal is a docs/ structure like:
  ```
  docs/
  ├── README.md (index)
  ├── USER_GUIDE.md (high visibility)
  ├── planning/ (4-7 strategy docs)
  ├── architecture/ (2-3 design docs)
  ├── reference/ (3-5 technical guides)
  ├── deployment/ (7 deployment docs - already good)
  ├── design-system/ (2 UI docs - already good)
  ├── ai-agents/ (3 AI docs - already good)
  └── archive/ (historical docs - already good)
  ```

## Testing

- [ ] All links in `docs/README.md` resolve correctly
- [ ] Search for old file paths: `rg "E2E_TESTING_STANDARDS|EXECUTIVE_SUMMARY|PRODUCT_ROADMAP|TECHNICAL_BOUNDARIES|FEATURE_STATUS|TESTING_CONVENTIONS|QA_ACCESSIBILITY"` returns only new paths
- [ ] No 404s when following documentation links

## Related

- Builds on PR #129 (documentation reorganization)
- Completes the docs cleanup initiative
- Prepares documentation structure for Zebu rename (Task 130+)
