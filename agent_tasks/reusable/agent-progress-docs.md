# Agent Progress Documentation

**For PR-based coding agents only** (not for orchestration sessions).

## When Required

✅ Coding agents creating PRs (backend-swe, frontend-swe, etc.)
✅ Architectural decisions
✅ Complex bug fixes

❌ Orchestration sessions (direct conversations)
❌ Simple questions or explorations
❌ Documentation-only changes

## File Format

```
agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_short-description.md
```

Get timestamp: `date "+%Y-%m-%d_%H-%M-%S"`

## Content Template

```markdown
# [Task Name/Description]

**Date**: YYYY-MM-DD
**Agent**: [backend-swe|frontend-swe|architect|quality-infra|refactorer]
**Related Task**: agent_tasks/NNN_task-name.md

## Task Summary
Brief description of what was accomplished.

## Decisions Made
Key technical decisions and rationale:
- Decision 1: Why it was chosen
- Decision 2: Alternatives considered

## Files Changed
- `path/to/file1.py` - Description
- `path/to/file2.ts` - Description

## Testing Notes
How the changes were tested:
- Unit tests added/modified
- Integration tests
- Manual testing performed

## Known Issues/Next Steps
Any limitations or follow-up work needed.

## (Optional) Next Step Suggestions
Only if applicable, suggest next tasks or improvements.
```
