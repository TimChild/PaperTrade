# Integration Plan: Reusable Agent Guidance

This document outlines how to integrate the new reusable chunks into existing agent instruction files.

## Summary of Reusable Chunks Created

| Chunk File | Lines | Primary Purpose | Replaces Content In |
|------------|-------|----------------|---------------------|
| `git-workflow.md` | 97 | Git/GitHub CLI workflow | copilot-instructions.md, AGENT_ORCHESTRATION.md |
| `architecture-principles.md` | 73 | Clean Architecture summary | copilot-instructions.md, architect.md, backend-swe.md |
| `backend-quality-checks.md` | 59 | Backend validation commands | backend-swe.md, quality-infra.md |
| `frontend-quality-checks.md` | 58 | Frontend validation commands | frontend-swe.md, quality-infra.md |
| `docker-commands.md` | 83 | Docker/Compose operations | quality-infra.md, AGENT_ORCHESTRATION.md |
| `agent-progress-docs.md` | 71 | Progress documentation guide | copilot-instructions.md (referenced by all) |
| `before-starting-work.md` | 67 | Pre-work checklist | ALL agent files |
| `pre-completion-checklist.md` | 64 | Final validation steps | Already exists, well-used |

**Total new reusable content**: ~508 lines (excluding pre-completion-checklist.md which already exists)

## Integration Mapping

### `.github/copilot-instructions.md` (238 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Git & GitHub CLI Workflow" | ~95 | Reference to `git-workflow.md` | ~90 |
| "Core Principles" | ~25 | Reference to `architecture-principles.md` | ~20 |
| "Agent Progress Documentation" | ~30 | Reference to `agent-progress-docs.md` | ~25 |

**Estimated reduction**: ~135 lines → ~103 lines (43% reduction)

---

### `.github/agents/backend-swe.md` (235 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting Work" | ~15 | Reference to `before-starting-work.md` | ~10 |
| "CRITICAL: Pre-Completion Validation" | ~15 | Reference to `pre-completion-checklist.md` + `backend-quality-checks.md` | ~10 |
| Progress docs mention | ~5 | Reference to `agent-progress-docs.md` | ~3 |

**Estimated reduction**: ~235 lines → ~212 lines (10% reduction)

---

### `.github/agents/frontend-swe.md` (301 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting Work" | ~15 | Reference to `before-starting-work.md` | ~10 |
| "CRITICAL: Pre-Completion Validation" | ~15 | Reference to `pre-completion-checklist.md` + `frontend-quality-checks.md` | ~10 |
| Progress docs mention | ~5 | Reference to `agent-progress-docs.md` | ~3 |

**Estimated reduction**: ~301 lines → ~278 lines (8% reduction)

---

### `.github/agents/quality-infra.md` (277 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting Work" | ~12 | Reference to `before-starting-work.md` | ~8 |
| Docker Compose examples | ~40 | Reference to `docker-commands.md` | ~35 |
| Testing Philosophy | ~30 | Reference to `architecture-principles.md` | ~25 |
| Progress docs mention | ~5 | Reference to `agent-progress-docs.md` | ~3 |

**Estimated reduction**: ~277 lines → ~206 lines (26% reduction)

---

### `.github/agents/architect.md` (246 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting Work" | ~12 | Reference to `before-starting-work.md` | ~8 |
| "Architecture Layers Reference" | ~25 | Reference to `architecture-principles.md` | ~20 |
| "Guiding Principles" | ~15 | Reference to `architecture-principles.md` | ~12 |
| Progress docs mention | ~5 | Reference to `agent-progress-docs.md` | ~3 |

**Estimated reduction**: ~246 lines → ~203 lines (17% reduction)

---

### `.github/agents/refactorer.md` (226 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting Work" | ~12 | Reference to `before-starting-work.md` | ~8 |
| Modern Software Engineering principles | ~10 | Reference to `architecture-principles.md` | ~8 |
| Progress docs mention | ~5 | Reference to `agent-progress-docs.md` | ~3 |

**Estimated reduction**: ~226 lines → ~207 lines (8% reduction)

---

### `.github/agents/qa.md` (103 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| "Before Starting" | ~8 | Reference to `before-starting-work.md` | ~5 |
| Docker commands | ~10 | Reference to `docker-commands.md` | ~8 |

**Estimated reduction**: ~103 lines → ~90 lines (13% reduction)

---

### `AGENT_ORCHESTRATION.md` (213 lines)

**Sections to replace with references:**

| Section | Lines | Replace With | Estimated Lines Saved |
|---------|-------|--------------|----------------------|
| Local Development docker commands | ~15 | Reference to `docker-commands.md` | ~12 |
| Git workflow mentions | ~10 | Reference to `git-workflow.md` | ~8 |
| GH CLI best practices | ~15 | Reference to `git-workflow.md` | ~12 |

**Estimated reduction**: ~213 lines → ~181 lines (15% reduction)

---

## Total Impact Estimate

| File | Current Lines | After Integration | Lines Saved | % Reduction |
|------|---------------|-------------------|-------------|-------------|
| copilot-instructions.md | 238 | 103 | 135 | 43% |
| backend-swe.md | 235 | 212 | 23 | 10% |
| frontend-swe.md | 301 | 278 | 23 | 8% |
| quality-infra.md | 277 | 206 | 71 | 26% |
| architect.md | 246 | 203 | 43 | 17% |
| refactorer.md | 226 | 207 | 19 | 8% |
| qa.md | 103 | 90 | 13 | 13% |
| AGENT_ORCHESTRATION.md | 213 | 181 | 32 | 15% |
| **Total** | **1,839** | **1,480** | **359** | **20%** |

**Overall reduction**: ~359 lines (20% of duplicated content)

## Reference Syntax

When referencing reusable chunks in agent files, use this format:

```markdown
## [Section Title]

> 📖 **See**: [agent_tasks/reusable/chunk-name.md](../../../agent_tasks/reusable/chunk-name.md)

[Optional: Any file-specific additions or clarifications]
```

Example:
```markdown
## Before Starting Work

> 📖 **See**: [agent_tasks/reusable/before-starting-work.md](../../../agent_tasks/reusable/before-starting-work.md)

**Backend-specific additions**:
- Check `backend/pyproject.toml` for recent dependency changes
- Review `backend/tests/conftest.py` for test fixtures
```

## Content That Should NOT Be Deduplicated

Some content is intentionally file-specific and should remain:

### Agent-Specific Content
- **Role descriptions**: Each agent has a unique purpose
- **Technology stack tables**: Agent-specific tools and versions
- **Coding standards**: Language-specific examples and patterns
- **Custom responsibilities**: Agent-specific workflows

### Context-Specific Content
- **Examples**: Code examples tailored to the agent's domain
- **File structures**: Domain-specific directory layouts
- **Decision rationales**: Explanations unique to the agent's work

### Strategic Content
- **When to Engage This Agent**: Agent-specific scenarios
- **Output Expectations**: Agent-specific deliverables

## Implementation Steps (Follow-up Task)

This is a **proposal only**. A separate follow-up task will:

1. Update `.github/copilot-instructions.md` with references
2. Update each agent file in `.github/agents/`
3. Update `AGENT_ORCHESTRATION.md` with references
4. Test that links work correctly
5. Verify agent behavior hasn't changed
6. Document the changes in a progress doc

## Benefits

### Maintenance
- **Single source of truth**: Update workflow in one place
- **Consistency**: All agents follow the same processes
- **Easier updates**: Change once, applies everywhere

### Clarity
- **Focused agent files**: Each agent file stays focused on role-specific content
- **Clearer separation**: Common vs. agent-specific guidance
- **Easier onboarding**: New agents can reference standard chunks

### Quality
- **Less duplication**: Reduced chance of conflicting instructions
- **Version control**: Easier to track changes to common workflows
- **Testability**: Can validate that all agents reference current versions

## Next Steps

1. ✅ Create reusable chunks (this task)
2. ✅ Document integration plan (this document)
3. ⏭️ Create follow-up task to integrate chunks into agent files
4. ⏭️ Test agent behavior with new structure
5. ⏭️ Monitor for any issues or missing content
