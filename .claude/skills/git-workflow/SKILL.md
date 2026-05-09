---
name: git-workflow
description: Git and GitHub CLI conventions for Zebu — branch naming, conventional commits, PR creation patterns, and gh-pager workarounds.
---

# Git & GitHub Workflow

## Branches

```bash
git branch --show-current
git status
git checkout -b <type>/<short-desc>
```

Names: `feat/add-portfolio-api`, `fix/trade-calculation`, `docs/update-readme`, `refactor/extract-trade-factory`.

## Conventional commits

`type(scope): description`

| Type | Use for |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without behavior change |
| `test` | Adding / updating tests |
| `docs` | Documentation only |
| `chore` | Tooling / dependencies |
| `ci` | CI / workflow changes |

Skip the auto-deploy with `[skip deploy]` in the commit message — useful for docs-only commits to `main`.

## Committing

```bash
git add <specific-files>          # prefer over -A — avoids stray secrets
git commit -m "feat(scope): description"
git push -u origin <branch>
```

## PR creation

```bash
# Auto-fill from commits
gh pr view --web 2>/dev/null || gh pr create --fill

# Or with explicit body
gh pr create --title "feat(scope): description" --body-file .tmp_pr.md
```

For long PR bodies, **use a temp file with `--body-file`** — long inline strings cause shell quoting issues:

```bash
# Write description to a temp file, then:
GH_PAGER="" gh pr create --title "fix: description" --body-file .tmp_pr.md && rm .tmp_pr.md
```

## gh CLI conventions

**Always prefix `gh` with `GH_PAGER=""`** to prevent the pager from blocking:

```bash
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view 47
GH_PAGER="" gh issue list
```

## Keeping branches current

```bash
git fetch origin
git rebase origin/main           # preferred over merge for feature branches
git push --force-with-lease       # safer than --force
```

## Don't

- `git push --force` to `main` (use `--force-with-lease` and only on feature branches)
- Skip pre-commit hooks (`--no-verify`) unless you have a specific reason
- Amend commits that have already been pushed and reviewed
- Use `git add -A` on a dirty workspace — be specific
