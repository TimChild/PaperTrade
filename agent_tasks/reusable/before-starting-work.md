# Before Starting Work - Standard Checklist

**All agents should perform these checks before beginning implementation work.**

## 1. Check Recent Agent Activity

Review what other agents have done recently:
```bash
# View recent progress docs
ls -lt agent_progress_docs/ | head -10

# Check for relevant documentation
find agent_progress_docs/ -name "*keyword*"
```

## 2. Check Open PRs

Avoid conflicts with ongoing work:
```bash
GH_PAGER="" gh pr list
```

Look for:
- PRs touching the same files/features
- Related work by other agents
- Pending reviews that might affect your work

## 3. Review Architecture Documentation

Check if architecture plans exist for your feature:
```bash
# List architecture plans
ls -la architecture_plans/

# Check architecture docs
ls -la docs/architecture/
```

If architecture docs exist for this feature:
- **REQUIRED**: Implement according to the spec
- Don't deviate without explicit approval
- Ask questions if spec is unclear

## 4. Understand Current Code State

Read relevant existing code:
```bash
# Find related files
find . -name "*portfolio*" -type f

# Search for patterns
grep -r "class Portfolio" --include="*.py"
```

Understand:
- Current patterns and conventions
- Existing tests
- Code organization

## 5. Review Project Context

Familiarize yourself with:
- `project_plan.md` - Overall development roadmap
- `project_strategy.md` - Technical strategy and decisions
- `PROGRESS.md` - Current project status
- `.github/copilot-instructions.md` - General guidelines

## Quick Start Command

```bash
# Run all checks at once
GH_PAGER="" gh pr list && \
ls -lt agent_progress_docs/ | head -5 && \
ls -la architecture_plans/ && \
echo "✓ Pre-work checks complete"
```
