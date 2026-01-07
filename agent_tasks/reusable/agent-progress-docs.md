# Agent Progress Documentation

**For PR-based coding agents only** (not for orchestration sessions).

## Purpose

When a coding agent creates a PR, it should document decisions and changes in `agent_progress_docs/`. This helps the orchestrator review work and provides context for future development.

## When Required

- ✅ Coding agents creating PRs (backend-swe, frontend-swe, etc.)
- ✅ Architectural decisions
- ✅ Complex bug fixes

## When NOT Required

- ❌ Orchestration sessions (direct conversations in VS Code)
- ❌ Simple questions or explorations
- ❌ Documentation-only changes

## File Format

```
agent_progress_docs/YYYY-MM-DD_HH-MM-SS_short-description.md
```

Get timestamp:
```bash
date "+%Y-%m-%d_%H-%M-%S"
```

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

List of modified/created files with brief description:
- `path/to/file1.py` - Description
- `path/to/file2.ts` - Description

## Testing Notes

How the changes were tested:
- Unit tests added/modified
- Integration tests
- Manual testing performed

## Known Issues/Next Steps

Any limitations or follow-up work needed:
- Issue 1
- Issue 2

## (Optional) Next Step Suggestions

Only if applicable, suggest next tasks or improvements.
```

## Best Practices

- Keep it concise but informative
- Focus on **why** decisions were made, not just **what**
- Include relevant context for future developers
- Link to architecture docs when applicable
