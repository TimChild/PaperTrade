# Git & GitHub CLI Workflow

**All agents MUST use git and the GitHub CLI (`gh`) appropriately.**

## Branch Management

1. **Check current branch status** before starting work:
   ```bash
   git branch --show-current
   git status
   ```

2. **Create a feature branch** if on `main`:
   ```bash
   git checkout -b <type>/<short-description>
   ```
   Branch naming: `feat/add-portfolio-api`, `fix/trade-calculation`, `docs/update-readme`

## Committing Changes

1. **Stage changes** selectively:
   ```bash
   git add <specific-files>
   # or for all changes:
   git add -A
   ```

2. **Commit with conventional format**:
   ```bash
   git commit -m "type(scope): description"
   ```
   Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`

3. **Push to remote**:
   ```bash
   git push -u origin <branch-name>
   ```

## Pull Request Creation

Use the GitHub CLI to create PRs:

```bash
# Check if PR already exists for current branch
gh pr view --web 2>/dev/null || gh pr create --fill
```

Or with more control:
```bash
gh pr create --title "feat(scope): description" --body "## Summary
- Change 1
- Change 2

## Related Issues
Closes #123"
```

## GitHub CLI Best Practices

**Always prefix gh commands with `GH_PAGER=""` to prevent interactive pager blocking:**

```bash
# Good
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view 47
GH_PAGER="" gh issue list

# Bad - may hang waiting for pager input
gh pr list
gh pr view 47
```

## Keeping Up to Date

```bash
# Fetch latest changes
git fetch origin

# If on a feature branch, rebase on main when needed
git rebase origin/main
```

## Workflow Summary

1. Check/create feature branch
2. Make changes
3. Stage and commit (conventional commits)
4. Push to remote
5. Create PR via `gh pr create` if none exists
6. Update PR description if needed
