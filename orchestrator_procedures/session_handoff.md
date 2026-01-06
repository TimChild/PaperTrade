# Session Handoff Procedure

Guide for creating a `resume-from-here.md` document to enable seamless handoff between orchestrator sessions.

## Purpose

When ending an orchestration session, create a `resume-from-here.md` file that provides all context needed for a new orchestrator agent to continue work **without access to the previous conversation history**.

## When to Create

- End of a work session
- Before a planned break
- When significant progress has been made
- After completing a major milestone

## Template Structure

```markdown
# Resume From Here - [Date]

## Current Status Summary
One paragraph describing where the project currently stands.

## Session Accomplishments
- What PRs were merged/closed this session
- What tasks were completed
- What decisions were made

## Active Work
- Any in-progress PRs (with numbers)
- Any running agent tasks
- Any blocked items and why

## Key Decisions Made This Session
Brief explanation of any strategic decisions with rationale.
This is critical context that would be lost without conversation history.

## Next Steps (Prioritized)
1. **Immediate**: What should be done first
2. **Short-term**: What follows after immediate tasks
3. **Deferred**: Items to revisit later

## Environment State
- Any uncommitted changes to be aware of
- Any local configuration changes
- Any services running that need attention

## Commands to Get Started
\`\`\`bash
# Pull latest
git checkout main && git pull origin main

# Check current state
GH_PAGER="" gh pr list
GH_PAGER="" gh agent-task list

# [Any other relevant commands]
\`\`\`

## Key Context (if applicable)
Any critical background information the next orchestrator needs:
- Architecture decisions
- Known issues or gotchas
- Important constraints
```

## Best Practices

### DO Include:
- **PR numbers** and their status (merged, open, closed)
- **Task numbers** that are relevant
- **Specific decisions** and the reasoning behind them
- **Blockers** or issues that need attention
- **Commands** that the next agent will need

### DON'T Include:
- Full conversation recaps
- Extensive code snippets (reference files instead)
- Information already in PROGRESS.md
- Outdated context from earlier in the session

### Keep It Concise
The document should be ~50-150 lines. If it's longer, consider:
- Moving detailed information to PROGRESS.md
- Referencing existing docs instead of duplicating
- Summarizing rather than listing everything

## Location

Always create at repository root:
```
/resume-from-here.md
```

## Cleanup

The `resume-from-here.md` file should be:
1. **Deleted** once the new session is established and context is absorbed
2. **Not committed** to version control (add to `.gitignore` if needed)
3. **Replaced** with a new one at the end of the next session

## Example Workflow

### Ending a Session:
```bash
# 1. Ensure all work is committed/pushed
git status

# 2. Create resume document
# (Use AI assistant or manually write)

# 3. Note any running processes
GH_PAGER="" gh agent-task list
```

### Starting a New Session:
```bash
# 1. Read the resume document
cat resume-from-here.md

# 2. Read current progress
cat PROGRESS.md

# 3. Check active work
GH_PAGER="" gh pr list

# 4. Continue from where previous session left off

# 5. Delete outdated resume doc when no longer needed
rm resume-from-here.md
```

## Integration with Other Docs

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| `resume-from-here.md` | Session-specific handoff | Per session (temporary) |
| `PROGRESS.md` | Overall project progress | After milestones |
| `AGENT_ORCHESTRATION.md` | How to orchestrate agents | Rarely |
| `agent_tasks/*.md` | Individual task specs | Per task |

The resume doc is **ephemeral** - it captures session state that isn't appropriate for permanent documentation.
