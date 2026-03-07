# Task 071: Integrate Reusable Chunks into Agent Files

**Agent**: refactorer
**Priority**: Medium
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-07
**Depends On**: Task 070 (chunk refinement)

## Objective

Update `.github/agents/*.md` and `.github/copilot-instructions.md` to reference the reusable chunks in `agent_tasks/reusable/` instead of duplicating content.

## Context

We have reusable guidance chunks that multiple agent files should reference. Currently, the same information is duplicated across agent files. This task integrates the chunks to:
1. Reduce duplication
2. Create single source of truth
3. Make maintenance easier

## Reference Syntax

Use this format to reference chunks from agent files:

```markdown
## Git Workflow

> 📖 **See**: [git-workflow.md](../../../agent_tasks/reusable/git-workflow.md)

**Role-specific additions:**
- [Any backend/frontend specific notes here]
```

## Integration Map

Based on `integration-plan.md`, update these files:

### `.github/copilot-instructions.md`
Replace duplicated sections with references to:
- `git-workflow.md` - Git & GitHub CLI section
- `architecture-principles.md` - Core principles section

### `.github/agents/backend-swe.md`
Reference:
- `backend-quality-checks.md`
- `pre-completion-checklist.md`
- `architecture-principles.md`

### `.github/agents/frontend-swe.md`
Reference:
- `frontend-quality-checks.md`
- `pre-completion-checklist.md`
- `architecture-principles.md`

### `.github/agents/quality-infra.md`
Reference:
- `backend-quality-checks.md`
- `frontend-quality-checks.md`
- `docker-commands.md`
- `pre-completion-checklist.md`

### `.github/agents/architect.md`
Reference:
- `architecture-principles.md`
- `before-starting-work.md`

### `.github/agents/refactorer.md`
Reference:
- `backend-quality-checks.md`
- `frontend-quality-checks.md`
- `pre-completion-checklist.md`

### All Agent Files
All should reference:
- `pre-completion-checklist.md` (before completing work)
- `agent-progress-docs.md` (for PR documentation)

## Guidelines

1. **Don't over-reference**: Only reference chunks that are actually relevant
2. **Keep role-specific content**: Don't remove content unique to that agent
3. **Add context**: When referencing, add any role-specific notes inline
4. **Test readability**: Ensure files still read coherently with references

## What NOT to Change

- Don't modify the actual reusable chunks (that's Task 070)
- Don't change agent role descriptions
- Don't remove role-specific workflows or examples

## Success Criteria

- ✅ All agent files reference appropriate chunks
- ✅ Duplicated content removed (replaced with references)
- ✅ Files still readable and coherent
- ✅ Role-specific content preserved
- ✅ All referenced paths are correct and work

## Pre-Completion

Follow: [pre-completion-checklist.md](reusable/pre-completion-checklist.md)
