# Git & GitHub CLI Workflow

**All agents MUST use git and the GitHub CLI (`gh`) appropriately.**

## Branch Management

```bash
git branch --show-current       # Check current branch
git status                      # Check status
git checkout -b <type>/<desc>   # Create feature branch
```

Branch naming: `feat/add-portfolio-api`, `fix/trade-calculation`, `docs/update-readme`

## Committing Changes

```bash
git add <files>                 # Stage specific files
git add -A                      # Stage all changes
git commit -m "type(scope): description"
git push -u origin <branch-name>
```

Commit types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`

## Pull Request Creation

```bash
# Auto-fill PR from commits
gh pr view --web 2>/dev/null || gh pr create --fill

# Or with custom title/body
gh pr create --title "feat(scope): description" --body "## Summary
- Change 1

## Related Issues
Closes #123"
```

## GitHub CLI Best Practices

**Always prefix gh commands with `GH_PAGER=""` to prevent pager blocking:**

```bash
# Good - prevents hanging
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view 47
GH_PAGER="" gh issue list
```

## Keeping Up to Date

```bash
git fetch origin                # Fetch latest
git rebase origin/main          # Rebase on main
```
