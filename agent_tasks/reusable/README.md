# Reusable Agent Tasks

This directory contains reusable task templates that can be referenced repeatedly for common operational workflows.

## Purpose

Unlike one-time tasks in `agent_tasks/`, these templates are designed to be:
- **Reusable**: Executed multiple times across the project lifecycle
- **Standardized**: Consistent approach to recurring workflows
- **Referenced**: Linked from orchestrator procedures and specific tasks

## Current Templates

### Complete Task Templates

#### [e2e_qa_validation.md](e2e_qa_validation.md)
**Agent**: qa
**Purpose**: Comprehensive end-to-end quality assurance testing

Execute all critical user workflows to validate application quality. Produces detailed test reports with pass/fail status, severity assessment, and follow-up action items.

**When to use**:
- Weekly quality checks
- After merging multiple PRs
- Before production releases
- After major refactoring
- Regression testing after critical fixes

**See**: [docs/testing/e2e-guide.md](../../docs/testing/e2e-guide.md#qa-orchestration-for-agents)

### Reusable Guidance Chunks

These small, focused documents can be referenced from agent instruction files to reduce duplication:

#### [quality-and-tooling.md](quality-and-tooling.md)
**For**: All coding agents
**Purpose**: Consolidated reference for quality checks, Docker, and pre-completion validation

**Covers**: Backend/frontend quality tasks, Docker commands, pre-completion checklist, common fixes.

**Referenced by**: `.github/copilot-instructions.md`, all agent files

---

#### [git-workflow.md](git-workflow.md)
**For**: All agents
**Purpose**: Standard Git and GitHub CLI workflow

Branch management, committing, PR creation, and GitHub CLI best practices (environment-specific for Copilot agents vs local VSCode).

**Referenced by**: `.github/copilot-instructions.md`, `AGENT_ORCHESTRATION.md`

---

#### [architecture-principles.md](architecture-principles.md)
**For**: All technical agents
**Purpose**: Clean Architecture and testing philosophy summary

Core principles, layer diagram, dependency rules, and testing philosophy.

**Referenced by**: `architect.md`, `backend-swe.md`, `frontend-swe.md`, `refactorer.md`

---

#### [agent-progress-docs.md](agent-progress-docs.md)
**For**: All PR-based coding agents
**Purpose**: Documentation requirements for PR-based work

When and how to create progress documentation for completed work.

**Referenced by**: All agent files

---

#### [before-starting-work.md](before-starting-work.md)
**For**: All agents
**Purpose**: Standard pre-work checklist

Check recent activity, open PRs, architecture docs, and project context before starting.

**Referenced by**: All agent files

## How to Use Reusable Tasks

### Option 1: Reference Directly
Create an agent task that references the template:

```bash
gh agent-task create --custom-agent qa -F agent_tasks/reusable/e2e_qa_validation.md
```

### Option 2: Reference in Orchestrator Procedures
Orchestrator procedures (in `docs/ai-agents/procedures/`) can reference these templates as part of larger workflows.

## Adding New Reusable Tasks

When creating a new reusable task template:

1. **Identify the Pattern**: Is this workflow repeated 3+ times?
2. **Generalize**: Remove project-specific details, make it adaptable
3. **Document Well**: Clear instructions, success criteria, expected outcomes
4. **Create Procedure**: Add orchestrator procedure if multi-step workflow
5. **Update This README**: Add entry describing the template

### Template Structure

```markdown
# [Task Name]

**Task Type**: Reusable [Category] Template
**Agent**: [agent-name]
**Priority**: [when executed]
**Estimated Effort**: [time]

## Objective
[Clear description of what this task accomplishes]

## Context
[When to use this task, what triggers it]

## Instructions
[Detailed step-by-step instructions]

## Deliverables
[What outputs are expected]

## Success Criteria
[How to know the task is complete]

## References
[Related docs, procedures, templates]
```

## Reusable vs One-Time Tasks

| Aspect | Reusable (this dir) | One-Time (agent_tasks/) |
|--------|---------------------|-------------------------|
| **Frequency** | Multiple uses | Single execution |
| **Specificity** | Generic, adaptable | Specific issue/feature |
| **Examples** | QA testing, deployments | Fix bug #123, implement feature X |
| **Versioned** | Updated over time | Completed and archived |
| **Referenced** | By procedures & tasks | By PRs & commits |

## Future Templates

Potential candidates for reusable templates:

- **Production Deployment**: Checklist for deploying to production
- **Database Migration**: Steps for applying schema changes
- **Performance Audit**: Systematic performance testing workflow
- **Security Scan**: Vulnerability assessment procedure
- **Dependency Updates**: Process for updating npm/pip packages
- **Documentation Review**: Ensuring docs stay current with code

## Maintenance

Review reusable templates quarterly:
- Are instructions still accurate?
- Have workflows evolved?
- Are success criteria appropriate?
- Should new templates be added?

## References

- [../README.md](../README.md) - Main agent tasks directory
- [../../docs/ai-agents/procedures/](../../docs/ai-agents/procedures/) - Orchestrator workflows
- [../../AGENT_ORCHESTRATION.md](../../AGENT_ORCHESTRATION.md) - Agent coordination guide
