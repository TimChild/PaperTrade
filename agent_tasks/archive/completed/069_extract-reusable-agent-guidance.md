# Task 069: Extract Reusable Agent Guidance

**Agent**: architect
**Priority**: Medium
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-07

## Objective

Analyze the current agent instruction files and extract common guidance into small, reusable chunks that can be composed together. This reduces duplication and makes maintenance easier.

**This is a RESEARCH + PROPOSAL task** - identify what should be extracted, create the chunks, but do not modify the existing agent files (that's a follow-up task).

## Context

Currently we have multiple agent instruction files with overlapping content:
- `.github/copilot-instructions.md` (238 lines) - Main instructions for all agents
- `.github/agents/backend-swe.md` - Backend-specific
- `.github/agents/frontend-swe.md` - Frontend-specific
- `.github/agents/architect.md` - Architecture focus
- `.github/agents/quality-infra.md` - CI/CD, testing
- `.github/agents/refactorer.md` - Code cleanup
- `.github/agents/qa.md` - QA validation

Additionally:
- `AGENT_ORCHESTRATION.md` (213 lines) - Guide for orchestrating agents
- `agent_tasks/reusable/pre-completion-checklist.md` - Example of a good reusable chunk

### The Problem
1. Same information repeated across multiple agent files
2. When we update a process, we have to update multiple files
3. Hard to ensure consistency across agents
4. Files are getting long with mixed concerns

### The Goal
Create small, focused reusable docs like `pre-completion-checklist.md` that:
- Cover ONE specific topic
- Can be referenced from multiple agent files
- Are easy to keep up-to-date
- Use clear, concise language

## Requirements

### 1. Analyze Existing Agent Files

Read each file in `.github/agents/` and `.github/copilot-instructions.md`.

Identify content that appears in multiple places:
- Git/GitHub CLI workflows
- Testing commands
- Code quality commands (ruff, pyright, eslint, etc.)
- Architecture principles
- Common patterns

### 2. Propose Reusable Chunks

For each identified topic, propose a reusable chunk file.

Suggested candidates (verify and expand):
```
agent_tasks/reusable/
├── README.md                     # Index of reusable chunks
├── pre-completion-checklist.md   # Already exists ✓
├── git-workflow.md               # Branch, commit, PR creation
├── backend-quality-checks.md     # ruff, pyright, pytest commands
├── frontend-quality-checks.md    # eslint, tsc, vitest commands
├── docker-commands.md            # Common docker/compose operations
├── architecture-principles.md    # Clean architecture summary
├── mcp-tools-quick-ref.md        # Essential MCP tools for agents
└── common-fixes.md               # Frequent issues and solutions
```

### 3. Create Proposed Chunks

For each proposed chunk:
1. Create the file in `agent_tasks/reusable/`
2. Keep it concise (target 30-60 lines)
3. Focus on actionable information
4. Use consistent formatting

### 4. Create Integration Plan

Document in `agent_tasks/reusable/README.md`:
1. Purpose of each chunk
2. Which agent files should reference which chunks
3. How to reference chunks (example syntax)

Example reference in agent file:
```markdown
## Pre-Completion Checklist
See: [agent_tasks/reusable/pre-completion-checklist.md](../../../agent_tasks/reusable/pre-completion-checklist.md)
```

### 5. Deliverable Summary

Create or update: `agent_tasks/reusable/integration-plan.md`

Include:
1. List of all chunks created
2. Mapping: which agent files need updates to reference which chunks
3. Estimated lines removed from each agent file after consolidation
4. Any content that should NOT be deduplicated (file-specific)

## Success Criteria

- ✅ All agent instruction files analyzed
- ✅ Common patterns identified and documented
- ✅ 3-6 new reusable chunk files created
- ✅ Integration plan documented
- ✅ Chunks are concise (30-60 lines each)
- ✅ No modifications to existing agent files (just proposals)

## References

- Example reusable chunk: `agent_tasks/reusable/pre-completion-checklist.md`
- Main agent instructions: `.github/copilot-instructions.md`
- Agent files: `.github/agents/*.md`
- Orchestration guide: `AGENT_ORCHESTRATION.md`

## Notes

- Quality over quantity - fewer, better chunks is preferable
- Each chunk should have a clear single purpose
- Test that the chunks make sense standalone
- Consider how an agent would use these during a task
