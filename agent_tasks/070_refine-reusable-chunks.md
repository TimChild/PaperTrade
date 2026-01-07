# Task 070: Refine Reusable Agent Guidance Chunks

**Agent**: refactorer
**Priority**: Medium
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-07

## Objective

Review and refine the reusable guidance chunks in `agent_tasks/reusable/` to ensure they are:
1. Short and to the point (≤100 lines each)
2. Focused on a single topic
3. Actionable with clear commands/examples
4. Not verbose or redundant

## Context

PR #85 created 7 guidance chunks. Most are good size (55-100 lines), but they need review for:
- Unnecessary verbosity
- Redundant explanations
- Content that could be shortened

## Writing Guidelines for Chunks

**DO:**
- Keep chunks ≤100 lines (hard limit unless exceptional reason)
- Use examples when they're the clearest way to explain
- Use tables for reference data (commands, options)
- Get straight to the point
- Use code blocks for commands

**DON'T:**
- Write lengthy explanations when an example suffices
- Include "motivation" or "background" sections
- Repeat information available elsewhere
- Add counter-examples unless CRITICAL for avoiding common mistakes

## Chunks to Review

Review each file and trim where possible:

| File | Lines | Action |
|------|-------|--------|
| `git-workflow.md` | 90 | Review - at limit |
| `docker-commands.md` | 100 | Review - at limit |
| `agent-progress-docs.md` | 80 | Review for verbosity |
| `before-starting-work.md` | 76 | Review for verbosity |
| `architecture-principles.md` | 63 | Good size, light review |
| `backend-quality-checks.md` | 57 | Good size, light review |
| `frontend-quality-checks.md` | 55 | Good size, light review |
| `pre-completion-checklist.md` | 63 | Good size, light review |

## Specific Review Items

### 1. `git-workflow.md` (90 lines)
- Check if any sections are redundant with `pre-completion-checklist.md`
- Ensure examples are minimal but complete

### 2. `docker-commands.md` (100 lines)
- Consider if this can be split or trimmed
- Focus on most common operations only

### 3. `before-starting-work.md` (76 lines)
- Check overlap with other chunks
- May overlap conceptually with pre-completion - clarify distinction

### 4. `agent-progress-docs.md` (80 lines)
- Ensure the template section is minimal
- Remove verbose explanations

## Meta Files (Do Not Modify Content)

These files are documentation about the chunks, not chunks themselves:
- `README.md` - Index file (can update if chunks change)
- `integration-plan.md` - Implementation plan (reference only)
- `VISUAL_SUMMARY.md` - Diagram/overview (reference only)
- `e2e_qa_validation.md` - Full task template, not a guidance chunk

## Success Criteria

- ✅ All guidance chunks are ≤100 lines
- ✅ No verbose/redundant content
- ✅ Each chunk focused on single topic
- ✅ Examples used instead of lengthy explanations where appropriate
- ✅ README.md updated if any chunks renamed/removed

## Pre-Completion

Follow: [pre-completion-checklist.md](reusable/pre-completion-checklist.md)
