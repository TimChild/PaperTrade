# Strategic Plan - Post-Rename Next Steps

**Date**: January 14, 2026
**Status**: In Progress

## Context

Following the successful project rename (PaperTrade → Zebu, PR #132), we're at a strategic decision point with a production-ready application:

**Current State**:
- ✅ All core features complete (Phases 1-3c)
- ✅ 545 backend + 197 frontend tests passing
- ✅ 81% test coverage
- ✅ Deployed to Proxmox (local network)
- ⚠️ Domain/SSL blocked by local network access
- ⚠️ Beta testing happening informally

## Strategic Options Evaluated

### Path 1: Production Deployment
**Status**: Partially blocked
- ✅ Deployed to Proxmox VM
- ❌ Domain/SSL setup requires local network access (blocked)
- 📊 Monitoring infrastructure (~$9/month, 2-3 hours setup)

**Decision**: Defer until local network access available

### Path 2: Quality Polish
**Status**: Mostly complete, some items remaining
- ✅ E2E tests migrated to test IDs (PR #60)
- ✅ E2E suite refactored 60→21 tests (PR #120)
- ⚠️ E2E in agent environment (diagnostics needed)
- ❓ React patterns audit (evaluation needed)

**Decision**: Focus here with diagnostic/evaluation tasks

### Path 3: Advanced Features
**Status**: Deferred
- Limit/stop orders, WebSockets, etc.
- Agree to defer until more user feedback

## Chosen Strategy: Quality-First with Diagnostics

### Active Tasks (In Progress)

1. **Task 133: Verify E2E Tests in Agent Environment**
   - **Agent**: quality-infra
   - **Status**: Running
   - **Goal**: Determine if E2E tests can run in GitHub agent environment
   - **Outcome**: Either ✅ agents can validate E2E or ❌ E2E validation happens in main CI only
   - **Effort**: 30-60 minutes

2. **Task 134: React Patterns Audit - Evaluation**
   - **Agent**: frontend-swe
   - **Status**: Running
   - **Goal**: Audit codebase for useEffect anti-patterns and ESLint suppressions
   - **Deliverable**: Findings report with effort estimates and recommendations
   - **Effort**: 2-3 hours (evaluation only, not implementation)

### Monitoring Infrastructure Research

**Budget Stack Recommendation** ($9/month):
- Sentry Free: Error tracking (5K errors/month) - $0
- Grafana Cloud Free: Infrastructure monitoring - $0
- Plausible: Privacy-focused analytics (10K pageviews) - $9/month

**Setup time**: 2-3 hours total

**Decision**: Defer until domain/local network access available (monitoring useful for production, not for development/beta)

See `.tmp_monitoring_research.md` for full cost analysis and alternatives.

## Next Steps

### Immediate (This Session)
- ✅ Created Task 133 (E2E agent environment verification)
- ✅ Created Task 134 (React patterns audit evaluation)
- ✅ Started both agent tasks
- ✅ Agent findings received

### Agent Findings Summary

**Task 133 - E2E Tests in Agent Environment** (PR #133):
- **Result**: ❌ E2E tests cannot run in agent environment
- **Root Cause**: Playwright browsers not installed (~250MB download)
- **Impact**: Agent timeout (30min) + slow Docker builds (9min) make browser installation impractical
- **Solution**: Agents use unit tests only (545 backend + 197 frontend), E2E validation in main CI
- **Action**: Update copilot-setup-steps.yml to install Playwright browsers (✅ DONE)

**Task 134 - React Patterns Audit** (PR #134):
- **Result**: ✅ Codebase quality is **exceptional**
- **Findings**: Only 1 ESLint suppression across 98 files (TradeForm.tsx setState-in-useEffect)
- **Recommendation**: Optional low-priority refactor (~2 hours, medium ROI)
- **Action**: Defer - current implementation is functional and well-tested

### Completed Actions
- ✅ Moved monitoring research to permanent location (docs/planning/research/)
- ✅ Updated BACKLOG.md with agent findings and monitoring reference
- ✅ Fixed copilot-setup-steps.yml to install Playwright browsers
- ✅ Updated orchestration documentation

### Short-term (Next Actions)
1. **Merge agent PRs** (#133, #134) - Close diagnostic tasks
2. **Optional**: TradeForm refactor (~2 hours, low priority)
3. **Update orchestration docs** with E2E testing limitations

### Medium-term (When Local Network Access Available)
1. Configure custom domain + SSL (~1 hour)
2. Set up monitoring infrastructure ($9/month stack, 2-3 hours) - see [research doc](research/monitoring-solutions-analysis.md)
3. Structured beta user testing (5-10 users)
4. Collect feedback for Phase 4 planning

## Success Metrics

**Quality Metrics**:
- E2E test status in agent environment: Known and documented
- React code quality: Evaluated with actionable recommendations
- Technical debt: Prioritized and scheduled

**Product Metrics** (Future):
- Beta users: 5-10 active users
- Error rate: <1% of requests (via Sentry)
- Retention: Users return after first session

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| E2E tests don't work in agents | Low | Agents focus on unit tests, E2E in main CI |
| React audit reveals large effort | Medium | Prioritize, tackle incrementally |
| Local network access delayed | Low | Continue development, monitoring deferred |

## References

- [Monitoring Cost Analysis](.tmp_monitoring_research.md)
- [Task 133](agent_tasks/133_verify-e2e-agent-environment.md)
- [Task 134](agent_tasks/134_react-patterns-audit.md)
- [Progress Tracking](PROGRESS.md)
- [Backlog](BACKLOG.md)
