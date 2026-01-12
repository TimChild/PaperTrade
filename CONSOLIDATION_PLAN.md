# Environment Consolidation & Standardization Plan

**Date**: January 11, 2026
**Orchestrator**: CTO/Senior SWE
**Goal**: Solidify environment setup, ensure agents can run all tests, consolidate workflows

## Problems Identified

### 1. Missing Critical Commands
- ❌ No `task ci` (referenced in docs but doesn't exist)
- ❌ No `task validate:env` for environment verification
- ❌ No centralized scripts for environment validation

### 2. Workflow Inconsistencies
- ⚠️ CI workflow has inline setup steps instead of using tasks
- ⚠️ Copilot setup workflow has inline validation instead of using tasks
- ⚠️ E2E test setup duplicated across workflows
- ⚠️ Different environment variable handling in each workflow

### 3. Scripts Organization
- ⚠️ Only proxmox scripts exist, no general-purpose setup/validation scripts
- ⚠️ Seed scripts are in backend/scripts instead of root scripts/
- ⚠️ No validation scripts for checking environment prerequisites

### 4. Testing Gaps
- ⚠️ No clear way for agents to verify they can run E2E tests
- ⚠️ No health check task before running tests
- ⚠️ Docker service readiness checks are inline in workflows

## Consolidation Strategy

### Phase 1: Validation Infrastructure ✅ PRIORITY
**Agent**: quality-infra
**PR**: Environment validation infrastructure

Create:
1. `scripts/validate-environment.sh` - Comprehensive environment validator
2. `task validate:env` - Calls validation script
3. `task ci` - Full CI simulation for local use
4. `task health:all` - Check all services before running tests

Script checks:
- Tool versions (uv, npm, Task, Docker, Python, Node)
- Required secrets/env vars
- Docker services health
- Backend/frontend server responsiveness
- Import checks (Python modules)

### Phase 2: Taskfile Consolidation ✅ PRIORITY
**Agent**: quality-infra
**PR**: Consolidate Taskfile commands

Consolidate:
1. Add `task ci` that mirrors CI workflow exactly
2. Add `task validate:env`
3. Add `task health:all` (combines existing health checks)
4. Refactor `task test:e2e` to use health checks first
5. Extract complex inline logic to scripts/

New task structure:
```yaml
validate:env         # Run validation script
validate:secrets     # Check required secrets exist
health:all           # Check all services healthy
ci                   # Full CI suite (quality + tests)
ci:backend           # Backend CI only
ci:frontend          # Frontend CI only
```

### Phase 3: Update Workflows ✅ PRIORITY
**Agent**: quality-infra
**PR**: Standardize workflow files

Changes:
1. **ci.yml**: Use task commands instead of inline steps
   - `task setup:backend` → already done
   - `task setup:frontend` → already done
   - `task quality:backend` → already done
   - `task quality:frontend` → already done
   - Add `task validate:env` step
   - Simplify E2E setup using tasks

2. **copilot-setup-steps.yml**: Use task commands
   - Keep minimal inline setup (checkout, install tools)
   - Replace inline validation with `task validate:env`
   - Use `task docker:up` → already done
   - Add clear success/failure reporting

### Phase 4: Agent Testing ✅ VALIDATION
**Agents**: backend-swe, frontend-swe
**Task Files**: agent_tasks/NNN_validate-agent-environment-*.md

Create task files that instruct agents to:
1. Run `task validate:env` and report results
2. Run `task test:backend` (backend agent)
3. Run `task test:frontend` (frontend agent)
4. Run `task test:e2e` (both agents)
5. Report any failures with detailed logs

Agents should:
- Take screenshots/logs of any failures
- Verify all secrets are accessible
- Confirm Docker services are healthy
- Run actual tests and report coverage

### Phase 5: CI Validation ✅ VALIDATION
**Method**: Direct PR creation
**PR**: Test consolidated workflows

Create PR with:
- All consolidation changes
- Trigger CI automatically
- Verify all jobs pass
- Check E2E tests run successfully

### Phase 6: Documentation Updates 📝 FINAL
**Agent**: copilot-instructions-updater
**PR**: Update all documentation

Update:
- `.github/copilot-instructions.md` - New task commands
- `AGENT_ORCHESTRATION.md` - New validation procedures
- `docs/mcp-tools.md` - If any MCP usage patterns change
- Agent instructions - New pre-testing validation steps

## Implementation Order

1. ✅ **Phase 1 + 2 together** (validation infrastructure + Taskfile)
   - Single PR with scripts and tasks
   - Can be tested locally immediately

2. ✅ **Phase 3** (update workflows)
   - Separate PR that uses new tasks
   - Will test in CI automatically

3. ✅ **Phase 4** (agent testing)
   - Launch background agents
   - They report back success/failure
   - Fix any issues found

4. ✅ **Phase 5** (CI validation)
   - Merge Phase 1+2
   - Merge Phase 3
   - Verify everything works

5. 📝 **Phase 6** (documentation)
   - Update all docs to reflect new reality
   - Final cleanup

## Success Criteria

### Environment Validation
- [x] Script exists: `scripts/validate-environment.sh`
- [x] Task exists: `task validate:env`
- [x] Task exists: `task ci`
- [x] Validation runs in all workflows
- [x] Clear output showing what's checked

### Workflow Consolidation
- [x] CI workflow uses task commands primarily
- [x] Copilot workflow uses task commands primarily
- [x] No duplicated setup logic
- [x] E2E setup is streamlined

### Agent Capabilities
- [x] Backend agent can run `task test:backend` ✅
- [x] Frontend agent can run `task test:frontend` ✅
- [x] Both agents can run `task test:e2e` ✅
- [x] Agents can run `task validate:env` ✅
- [x] Clear error messages when something fails

### Documentation
- [x] All docs reference correct task commands
- [x] No references to non-existent commands
- [x] Clear setup instructions for new developers

## Rollback Plan

If issues arise:
1. Revert workflow changes (Phase 3) - workflows can go back to inline steps
2. Keep new tasks (Phase 1+2) - they're additive and don't break existing functionality
3. Validation scripts are optional - don't break existing workflows

## Timeline Estimate

- Phase 1+2: 1-2 hours (implementation + testing)
- Phase 3: 30 minutes (straightforward refactor)
- Phase 4: 2-4 hours (agent runtime + iteration)
- Phase 5: 1 hour (CI runtime + verification)
- Phase 6: 30 minutes (doc updates)

**Total**: ~5-8 hours of orchestrator time + agent runtime
