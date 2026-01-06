# Resume From Here: Phase 3c Analytics Implementation

**Created**: January 5, 2026
**Last Phase Completed**: Phase 3b Authentication (PR #72)
**Next Phase**: Phase 3c Analytics & Insights

## Quick Context

PaperTrade is a stock market emulation platform. We just completed Clerk authentication integration. Now implementing portfolio analytics: performance charts, composition visualizations, and simple backtesting.

## Current State

### What's Complete
- ✅ Phase 1: Core ledger (portfolios, transactions, holdings)
- ✅ Phase 2a: Real-time prices (Alpha Vantage integration)
- ✅ Phase 2b: Historical price data with charts
- ✅ Phase 3a: SELL orders (complete trading loop)
- ✅ Phase 3b: Clerk authentication with E2E tests
- ✅ Infrastructure: Docker, CI/CD, 499+ tests passing

### Repository Status
- **Branch**: `main` (clean working tree)
- **All CI**: Passing
- **No open PRs**

## Phase 3c Tasks Ready

Six task files created in `agent_tasks/`:

| Task | File | Description | Effort |
|------|------|-------------|--------|
| **056** | `056_phase3c-analytics-domain-layer.md` | `PortfolioSnapshot` entity, `PerformanceMetrics` value object | 2-3 days |
| **057** | `057_phase3c-analytics-repository.md` | Database schema, `SnapshotRepositoryPort` | 2 days |
| **058** | `058_phase3c-analytics-api.md` | `/performance` and `/composition` endpoints | 2-3 days |
| **059** | `059_phase3c-analytics-snapshot-job.md` | Daily snapshot background job | 2 days |
| **060** | `060_phase3c-analytics-frontend-charts.md` | Recharts components (line, pie, metrics) | 4-5 days |
| **061** | `061_phase3c-analytics-backtesting.md` | `as_of` parameter for time-travel trades | 3-4 days |

### Dependency Order
```
056 (Domain) → 057 (Repository) → 058 (API) + 059 (Job) → 060 (Charts) → 061 (Backtest)
```

## Architecture Reference

**Full specification**: `architecture_plans/phase3-refined/phase3c-analytics.md`

### Key Design Decisions
1. **Pre-computed snapshots** - Daily snapshot calculation (not real-time) for chart performance
2. **Recharts** - Already used in Phase 2b, React-native, MVP-appropriate
3. **Time-travel backtesting** - `as_of` parameter on existing trade use case (DRY)
4. **End-of-day prices** - MVP simplicity

### New Domain Entities
- `PortfolioSnapshot` - Daily portfolio value snapshot (total, cash, holdings)
- `PerformanceMetrics` - Calculated gain/loss, ROI, high/low values

### New API Endpoints
- `GET /api/v1/portfolios/{id}/performance?range={1W|1M|3M|1Y|ALL}`
- `GET /api/v1/portfolios/{id}/composition`
- `POST /api/v1/portfolios/{id}/trades` (updated with optional `as_of`)

### New Frontend Components
- `PerformanceChart` - Line chart with time range selector
- `CompositionChart` - Pie chart for holdings allocation
- `MetricsCards` - Summary statistics display

## Recommended Approach

### Option A: Sequential (Safer)
1. Start Task 056 (Domain) - Foundation for everything else
2. Then 057 (Repository) - Persistence layer
3. Then 058 + 059 in parallel (API + Job)
4. Then 060 (Frontend)
5. Finally 061 (Backtesting)

### Option B: Parallel Backend/Frontend
1. Backend agent: Tasks 056 → 057 → 058 → 059
2. Frontend agent: Task 060 (can mock API responses with MSW)
3. Integration: Task 061 after both complete

## Commands Reference

```bash
# Development
task dev              # Start all services
task test             # Run all tests
task test:backend     # Backend tests only
task test:frontend    # Frontend tests only
task test:e2e         # E2E tests

# Create feature branch
git checkout -b feat/phase3c-analytics
```

## Success Criteria (from architecture doc)

- [ ] Users can view portfolio value chart (line chart)
- [ ] Chart supports 1W, 1M, 3M, 1Y, ALL time ranges
- [ ] Users can see gain/loss metrics ($ and %)
- [ ] Users can view holdings composition (pie chart)
- [ ] Daily snapshots calculated automatically
- [ ] Users can execute trades with `as_of` parameter (backtesting)
- [ ] All existing tests still pass
- [ ] 40+ new tests for analytics functionality
- [ ] E2E tests verify chart rendering

## Files to Review First

1. `architecture_plans/phase3-refined/phase3c-analytics.md` - Full spec
2. `agent_tasks/056_phase3c-analytics-domain-layer.md` - First task
3. `backend/app/domain/` - Existing domain patterns
4. `frontend/src/components/prices/PriceHistoryChart.tsx` - Existing Recharts usage

## Notes

- Recharts is already installed (used in Phase 2b)
- Follow existing Clean Architecture patterns
- All tasks include detailed implementation guidance and test requirements
- Estimated total: 3-4 weeks

---

*Delete this file after starting Phase 3c implementation.*
