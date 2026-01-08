# Before Starting Work - Standard Checklist

**All agents should perform these checks before beginning implementation work.**

## 1. Check Recent Agent Activity

```bash
ls -lt agent_progress_docs/ | head -10
find agent_progress_docs/ -name "*keyword*"
```

## 2. Check Open PRs

```bash
GH_PAGER="" gh pr list
```

Look for PRs touching same files/features or related work.

## 3. Review Architecture Documentation

```bash
ls -la architecture_plans/
ls -la docs/architecture/
```

If architecture docs exist for this feature:
- **REQUIRED**: Implement according to the spec
- Don't deviate without explicit approval

## 4. Understand Current Code State

E.g.
```bash
find . -name "*portfolio*" -type f
grep -r "class Portfolio" --include="*.py"
```

Understand existing patterns, tests, and code organization.

## 5. Review Project Context

Familiarize yourself with:
- `docs/planning/project_plan.md` - Development roadmap
- `docs/planning/project_strategy.md` - Technical strategy
- `PROGRESS.md` - Current status
- `.github/copilot-instructions.md` - General guidelines

## Quick Start Command

```bash
GH_PAGER="" gh pr list && \
ls -lt agent_progress_docs/ | head -5 && \
ls -la architecture_plans/ && \
echo "✓ Pre-work checks complete"
```
