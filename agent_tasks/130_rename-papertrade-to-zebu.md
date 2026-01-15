# Task 130: Rename Project from PaperTrade to Zebu

**Agent**: refactorer (or backend-swe + frontend-swe in parallel)
**Priority**: High
**Estimated Complexity**: Medium
**Dependencies**: Task 129 (documentation structure finalized)

## Objective

Rename the entire project from "PaperTrade" to "Zebu" (or "ZebuTrader" where appropriate), updating all code, documentation, configuration, and deployment references.

## Background

The application is being renamed to **Zebu** (brand name) / **ZebuTrader** (full product name). Domain: `zebutrader.com`

**Naming conventions**:
- **Brand**: "Zebu" (short, casual references)
- **Product**: "ZebuTrader" (full product name, formal contexts)
- **Domain**: zebutrader.com
- **Code/packages**: `zebu` or `zebutrader` (lowercase, context-dependent)

## Scope

### 1. Python Backend

**Package/module names**:
- `backend/src/papertrade/` → `backend/src/zebu/`
- All imports: `from papertrade.` → `from zebu.`
- `pyproject.toml`: package name `papertrade` → `zebu`

**Code strings & comments**:
- Docstrings mentioning "PaperTrade"
- Error messages
- Log messages
- Comments

**Configuration**:
- Docker image names if they reference papertrade
- Environment variable prefixes if any (though keep existing vars for compatibility)

### 2. Frontend

**Package configuration**:
- `frontend/package.json`: name "papertrade-frontend" → "zebu-frontend"
- Update `description` field

**Code & UI**:
- All user-facing text: "PaperTrade" → "Zebu" or "ZebuTrader"
- HTML title tags: `<title>PaperTrade</title>` → `<title>Zebu</title>`
- Meta tags in `index.html`
- Component names if they reference PaperTrade
- Import paths if needed

**Branding**:
- Page headers, navigation
- Dashboard title
- Any "About" or footer text

### 3. Documentation

**All markdown files** (use case-sensitive search):
- "PaperTrade" → "Zebu" or "ZebuTrader" (context-dependent)
- Update product descriptions
- Update project summaries

**Key files**:
- `README.md` - main project description
- `CONTRIBUTING.md` - project references
- `docs/planning/executive-summary.md` (after Task 129 completes)
- `docs/planning/product-roadmap.md` (after Task 129 completes)
- All files in `docs/`
- Agent task files (historical - reference only, don't change)
- Architecture plans (historical - reference only, don't change)

**Leave unchanged**:
- `agent_progress_docs/` - historical record
- `architecture_plans/` - historical record
- Git commit messages (can't change)

### 4. Configuration Files

**Docker**:
- `docker-compose.yml` - service names (optional), image names
- `docker-compose.prod.yml` - image names
- `backend/Dockerfile` - labels, comments
- `frontend/Dockerfile` - labels, comments

**GitHub**:
- `.github/copilot-instructions.md` - all references
- `.github/agents/*.md` - agent descriptions
- `.github/workflows/*.yml` - workflow names, comments
- Note: Repository name stays "PaperTrade" on GitHub (can't rename via PR)

**Other configs**:
- `Taskfile.yml` - comments, descriptions
- `.vscode/settings.json` - if any project-specific references

### 5. Deployment & Domain

**Proxmox VM scripts**:
- `scripts/proxmox-vm/*.sh` - comments, git clone URL (stays PaperTrade on GitHub)
- Deployment docs - update to reference zebutrader.com

**Domain references**:
- Update placeholder URLs to zebutrader.com where appropriate
- CORS origins (when deploying to production)
- Frontend API base URL comments

**Environment examples**:
- `.env.example` - comments explaining the project
- `.env.production.example` - domain references

### 6. Search Strategy

Use multiple search patterns to catch all variations:
```bash
# Case-sensitive searches
rg "PaperTrade" --type-add 'config:*.{json,yml,yaml,toml,env}' -t config -t py -t ts -t tsx -t md
rg "papertrade" -i  # case-insensitive for lowercase
rg "PAPERTRADE"     # all caps (env vars, constants)
```

**Verify no matches remain** (except in historical/archive):
- agent_progress_docs/ (keep historical)
- architecture_plans/ (keep historical)
- .git/ (ignore)

## Replacement Guidelines

**Context-aware replacements**:

| Context | Old | New | Example |
|---------|-----|-----|---------|
| Formal product name | PaperTrade | ZebuTrader | "Welcome to ZebuTrader" |
| Casual/brand | PaperTrade | Zebu | "Learn trading with Zebu" |
| Python package | papertrade | zebu | `from zebu.domain` |
| NPM package | papertrade-frontend | zebu-frontend | package.json |
| Domain | N/A | zebutrader.com | Production URLs |
| Code comments | PaperTrade | Zebu | "Zebu application" |

**Judgment calls**:
- Use "Zebu" for casual, short references
- Use "ZebuTrader" for formal, product-focused content
- When in doubt, use "Zebu" (shorter, friendlier)

## Tasks

1. **Backend rename**:
   - [ ] Rename `backend/src/papertrade/` to `backend/src/zebu/`
   - [ ] Update all imports throughout backend
   - [ ] Update `pyproject.toml` package name
   - [ ] Update docstrings, comments, error messages
   - [ ] Run `task quality:backend` to verify

2. **Frontend rename**:
   - [ ] Update `package.json` name and description
   - [ ] Update all user-facing text in components
   - [ ] Update `index.html` title and meta tags
   - [ ] Update branding in navigation/headers
   - [ ] Run `task quality:frontend` to verify

3. **Documentation updates**:
   - [ ] Update README.md
   - [ ] Update CONTRIBUTING.md
   - [ ] Update all docs/ markdown files
   - [ ] Update .github/copilot-instructions.md
   - [ ] Update agent definitions in .github/agents/

4. **Configuration updates**:
   - [ ] Docker compose files
   - [ ] Dockerfiles (comments, labels)
   - [ ] GitHub workflow files
   - [ ] Environment examples
   - [ ] Taskfile.yml

5. **Deployment updates**:
   - [ ] Proxmox VM scripts (comments)
   - [ ] Deployment documentation
   - [ ] Domain references

6. **Verification**:
   - [ ] Run `rg "PaperTrade|papertrade" --type-add 'ignore:*.{git}' -g '!agent_progress_docs' -g '!architecture_plans'` shows no matches
   - [ ] All tests pass: `task ci`
   - [ ] Backend imports work: `cd backend && python -c "from zebu.domain.entities.portfolio import Portfolio; print('OK')"`
   - [ ] Frontend builds: `task build:frontend`

## Acceptance Criteria

- [ ] All code references to "papertrade" updated to "zebu"
- [ ] All user-facing text updated to "Zebu" or "ZebuTrader"
- [ ] All documentation updated
- [ ] Python package renamed and imports working
- [ ] NPM package renamed
- [ ] All tests passing (backend, frontend, E2E)
- [ ] Docker images build successfully
- [ ] No PaperTrade references remain (except historical docs/commits)

## Implementation Notes

**Python package rename**:
```bash
cd backend/src
git mv papertrade zebu
# Update all imports
rg "from papertrade" --files-with-matches | xargs sed -i '' 's/from papertrade/from zebu/g'
rg "import papertrade" --files-with-matches | xargs sed -i '' 's/import papertrade/import zebu/g'
```

**Testing after rename**:
```bash
task quality:backend   # Verify backend still works
task quality:frontend  # Verify frontend still works
task ci                # Run all CI checks
```

**Git commit strategy**:
- Single commit with all changes OR
- Separate commits for backend, frontend, docs, config (agent's choice)
- Use conventional commit: `refactor: rename project from PaperTrade to Zebu`

## Known Limitations

**Won't change**:
- GitHub repository name (stays `TimChild/PaperTrade` - requires manual GitHub action)
- Git clone URLs in scripts (stay as `github.com/TimChild/PaperTrade.git`)
- Historical documentation in `agent_progress_docs/`
- Architecture plans in `architecture_plans/`
- Git commit history (can't rewrite)

**Follow-up tasks** (separate from this PR):
- Update Proxmox VM deployment with new name
- Configure zebutrader.com domain with NPMplus
- Update GitHub repository name (manual admin action)

## Testing

**Manual verification**:
1. Backend server starts: `task docker:up:backend && curl http://localhost:8000/health`
2. Frontend builds: `task build:frontend`
3. Import test: `python -c "from zebu.domain.entities.portfolio import Portfolio"`
4. Full stack: `task docker:up:all` and test portfolio creation
5. Search verification: `rg "papertrade" -i -g '!agent_progress_docs' -g '!architecture_plans' -g '!.git'` shows minimal/expected results

## Related

- Domain: zebutrader.com (already registered, per Task 089)
- Deployment will need re-deployment to Proxmox VM after merge
- GitHub repo rename is manual admin action (not part of this PR)
