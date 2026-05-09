---
name: docs-tidy
description: Periodic cleanup of BACKLOG.md, PROGRESS.md, and README.md after a milestone or every ~5 PRs. Prune completed items, add milestone entries, sync feature lists, fix stale cross-references.
---

# Docs Tidy

Lightweight 15–30 minute procedure to keep BACKLOG / PROGRESS / README accurate.

## When

- After completing a major milestone or phase
- When BACKLOG has grown with completed items
- Monthly maintenance (or every ~5 PRs merged)
- Before opening a session-handoff context

## Scope

| File | Purpose | Rule |
|---|---|---|
| `BACKLOG.md` | Incomplete work only | Remove anything done |
| `PROGRESS.md` | Completed milestones | Add new entries chronologically |
| `README.md` | Project overview | Update feature list to match reality |

## Procedure

### 1. Audit BACKLOG.md

- Read the full file
- For each item, check if it's complete (search code, check merged PRs)
- **Remove** completed items entirely — they belong in PROGRESS
- **Update** items with partial progress to reflect current state
- Verify "Last Updated" date is current
- Keep focused: only actionable, incomplete work

### 2. Update PROGRESS.md

- Add a new section for the latest milestone if one was completed
- List key PRs with brief descriptions
- Include metrics (test counts, coverage)
- Keep entries concise — one line per PR or accomplishment
- Reconcile any test-count claims with the actual run

### 3. Sync README.md

- Verify feature list matches what's implemented
- Update version references
- Ensure setup instructions still work
- **Don't overhaul** — just fix inaccuracies

### 4. Check for stale cross-references

```bash
grep -rn "TODO\|FIXME\|HACK" --include="*.md" .
grep -rn "<old-filename>" --include="*.md" .   # if you renamed/removed
```

### 5. Quality checklist

- [ ] BACKLOG.md contains only incomplete items
- [ ] PROGRESS.md has entries for all completed milestones
- [ ] README.md feature list is accurate
- [ ] No stale cross-references
- [ ] All "Last Updated" dates current
- [ ] Markdown is well-formed (no broken links, headings consistent)

## Example commit

```
docs: milestone cleanup after Phase N completion

- BACKLOG.md: remove completed items, update priorities
- PROGRESS.md: add Phase N milestone with PR links
- README.md: update feature list and test counts
```

## Don't

- Don't restructure documents — just prune and update
- Don't archive items just because they're old; archive only if they have ongoing reference value (ADRs, retrospectives). For everything else, delete (the git history is the archive)
- Don't delay this if it's overdue — the longer BACKLOG drifts from reality, the harder it is to read
