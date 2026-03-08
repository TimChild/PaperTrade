# Docs Tidy Procedure

**Agent**: docs-refactorer (or any agent with write access)
**Purpose**: Periodic cleanup of project tracking documents to keep them accurate and concise.

## When to Use

- After completing a major milestone or phase
- When BACKLOG.md has grown with completed items
- When PROGRESS.md needs a new milestone entry
- Before creating resume-from-here.md for a handoff
- Monthly maintenance (or every ~5 PRs merged)

## Scope

This procedure covers three core tracking files:

| File | Purpose | Rule |
|------|---------|------|
| `BACKLOG.md` | Incomplete work only | Remove anything that's done |
| `PROGRESS.md` | Completed milestones | Add new entries, keep chronological |
| `README.md` | Project overview | Update feature list to match reality |

## Procedure

### 1. Audit BACKLOG.md

- Read the entire file
- For each item, check if it's been completed (search codebase, check merged PRs)
- **Remove** completed items entirely — they belong in PROGRESS.md
- **Update** items that have partial progress with current status
- Verify "Last Updated" date is current
- Keep the file focused: only actionable, incomplete work

### 2. Update PROGRESS.md

- Add a new section for the latest milestone/phase if one was completed
- List key PRs merged with brief descriptions
- Include metrics where available (test counts, coverage, etc.)
- Keep entries concise — one line per PR or accomplishment

### 3. Sync README.md

- Verify the feature list matches what's actually implemented
- Update any version references
- Ensure setup instructions are still accurate
- Don't overhaul — just fix inaccuracies

### 4. Check for Stale References

Search for references to removed items:
```bash
# Look for references to items you removed from BACKLOG
grep -r "TODO\|FIXME\|HACK" --include="*.md" .
```

### 5. Update resume-from-here.md

If this is part of a session handoff, update `resume-from-here.md` with:
- What was just completed
- What's next in the backlog
- Any blocking issues or decisions needed

## Quality Checklist

- [ ] BACKLOG.md contains only incomplete items
- [ ] PROGRESS.md has entries for all completed milestones
- [ ] README.md feature list is accurate
- [ ] No stale cross-references between docs
- [ ] All "Last Updated" dates are current
- [ ] Files are well-formatted markdown (no broken links, proper headings)

## Example Commit

```
docs: milestone cleanup after Phase N completion (Task #NNN)

- BACKLOG.md: Remove completed items, update priorities
- PROGRESS.md: Add Phase N milestone with PR links
- README.md: Update feature list
```

## Notes

- This is a lightweight procedure — should take 15-30 minutes
- Don't restructure documents, just prune and update
- When in doubt about whether something is "done", check the deployed app
- Can be combined with other docs work in a single PR
