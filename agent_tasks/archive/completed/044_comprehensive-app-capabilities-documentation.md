# Task 044: Comprehensive App Capabilities Documentation

**Status**: Open
**Priority**: Medium
**Agent**: qa or documentation specialist
**Estimated Effort**: 3-4 hours
**Created**: 2026-01-03

## Context

Zebu has reached a significant milestone with Phase 1 completion and initial Phase 2 functionality. We now have a working application with portfolio management, real-time trading, and live market data integration. However, the current capabilities, boundaries, and limitations are not clearly documented from a user perspective.

We need a comprehensive, user-facing document that explains:
- What features are currently implemented and working
- What the boundaries/limitations are
- What's planned but not yet implemented
- How to use the current features effectively

This documentation will be created through:
1. **Hands-on manual testing** using the live app (Playwright MCP browser automation)
2. **Code review** to understand technical boundaries
3. **Documentation synthesis** from existing docs, commit history, and architecture plans

## Problem

As a user (or developer) approaching Zebu, it's unclear:
- What can I actually do with the app right now?
- Where will things break or not work as expected?
- What features exist vs. what's coming in the future?
- How do I navigate the UI to accomplish common tasks?

The project has:
- ✅ Phase 1 complete (basic portfolio management, mock prices)
- ✅ Phase 2 partially complete (real market data via Alpha Vantage)
- ✅ E2E tests covering core workflows
- ❓ Unclear boundaries between implemented/planned features

## Objective

Create a comprehensive, user-friendly documentation package consisting of:

1. **Executive Summary** (1 page) - High-level current state
2. **Feature Capability Matrix** (1-2 pages) - What works, what's limited, what's planned
3. **User Guide** (3-5 pages) - How to use current features with screenshots/examples
4. **Technical Boundaries** (1-2 pages) - Known limitations and edge cases

The documentation should be created through **active testing and validation**, not just reading code.

## Requirements

### Phase 1: Manual Testing & Exploration (Required First!)

Use Playwright MCP browser tools to manually test the application:

1. **Portfolio Management**:
   - [ ] Create a new portfolio with various initial deposits ($1,000, $10,000, $100,000)
   - [ ] Create multiple portfolios
   - [ ] View portfolio list/dashboard
   - [ ] Navigate to individual portfolio detail pages
   - [ ] Test edge cases: $0 deposit, negative numbers, very large numbers

2. **Trading Functionality**:
   - [ ] Execute BUY trades with various quantities (1, 10, 100 shares)
   - [ ] Test with different stock symbols (IBM, AAPL, MSFT, GOOGL, TSCO.LON, etc.)
   - [ ] Verify cash balance updates after trades
   - [ ] Verify holdings table updates correctly
   - [ ] Verify transaction history displays
   - [ ] Test insufficient funds error handling
   - [ ] Test invalid ticker symbols
   - [ ] Test fractional shares (if supported)
   - [ ] Test SELL trades (if implemented)

3. **Market Data Integration**:
   - [ ] Verify real-time price display
   - [ ] Test price refresh/updates
   - [ ] Test with international symbols (UK, Canada, Germany, China stocks)
   - [ ] Check for rate limiting behavior (Alpha Vantage: 5 calls/min, 500/day)
   - [ ] Verify cached price handling
   - [ ] Test behavior when market is closed

4. **UI/UX Experience**:
   - [ ] Navigation flow (dashboard → portfolio detail → back)
   - [ ] Form validation and error messages
   - [ ] Loading states during API calls
   - [ ] Success/error dialogs
   - [ ] Responsive design (if implemented)
   - [ ] Accessibility features

5. **Data Persistence**:
   - [ ] Create portfolio, refresh page - data persists
   - [ ] Execute trades, restart Docker - data persists
   - [ ] Test with multiple browser sessions

### Phase 2: Code & Documentation Review

Review existing codebase and documentation to understand:

1. **Architecture Review**:
   - Read `docs/architecture/` to understand design decisions
   - Review `PROGRESS.md` for phase completion status
   - Check `project_plan.md` for planned vs. implemented features
   - Review `BACKLOG.md` for known limitations

2. **Implementation Boundaries**:
   - Check which use cases are implemented in `backend/src/zebu/application/use_cases/`
   - Review domain models for supported operations
   - Check API endpoints in `backend/src/zebu/adapters/inbound/api/`
   - Review frontend components for UI capabilities

3. **Test Coverage Analysis**:
   - Backend tests: Which scenarios are covered?
   - E2E tests: What workflows are validated?
   - Integration tests: What's tested end-to-end?

4. **Known Issues & Limitations**:
   - Check GitHub issues (if any)
   - Review `agent_tasks/progress/` for documented problems
   - Check TODO comments in code

### Phase 3: Documentation Creation

Create the following documents in `docs/`:

#### 1. `docs/USER_GUIDE.md`

Structure:
```markdown
# Zebu User Guide

## What is Zebu?
[Brief intro]

## Current Status (Phase 1 Complete, Phase 2 In Progress)
[Version info, what's live]

## Getting Started
### Creating Your First Portfolio
### Making Your First Trade

## Features
### Portfolio Management
- Creating portfolios
- Viewing portfolio details
- Managing multiple portfolios

### Stock Trading
- Buying stocks
- Selling stocks (if implemented)
- Market vs. limit orders (if implemented)

### Market Data
- Real-time prices
- Supported stock symbols
- International markets

## Known Limitations
[Important boundaries users should know]

## Tips & Best Practices

## Troubleshooting Common Issues
```

#### 2. `docs/FEATURE_STATUS.md`

Create a detailed capability matrix:

| Feature | Status | Notes | Phase |
|---------|--------|-------|-------|
| Create Portfolio | ✅ Full | Any deposit amount | Phase 1 |
| View Portfolios | ✅ Full | Dashboard view | Phase 1 |
| Buy Stocks | ✅ Full | Real-time prices via Alpha Vantage | Phase 2 |
| Sell Stocks | ❌ Not Implemented | Planned for Phase 2 | Phase 2 |
| Portfolio Analytics | ⚠️ Limited | Shows P&L but no charts | Phase 3 |
| ... | ... | ... | ... |

Legend:
- ✅ Full: Feature complete and tested
- ⚠️ Limited: Partially implemented
- 🚧 In Progress: Currently being developed
- ❌ Not Implemented: Planned for future

#### 3. `docs/EXECUTIVE_SUMMARY.md`

One-page summary:
- **Current State**: What works today
- **Key Features**: 3-5 bullet points
- **Known Limitations**: Critical boundaries
- **Roadmap**: What's coming next
- **For Users**: How to get started
- **For Developers**: How to contribute

### Phase 4: Validation & Refinement

1. **Screenshot/Recording Capture**:
   - Capture key workflows (portfolio creation, trading)
   - Save to `docs/screenshots/` or link in documentation

2. **Accuracy Check**:
   - Cross-reference documented features with actual behavior
   - Verify all limitations are documented
   - Ensure technical details match code reality

3. **User Perspective Review**:
   - Is the documentation approachable for non-technical users?
   - Are common questions answered?
   - Is the getting-started path clear?

## Technical Requirements

1. **Use Playwright MCP for Testing**:
   - Launch browser with `browser_navigate` to http://localhost:5173
   - Use `browser_snapshot` to capture page state
   - Use `browser_click`, `browser_type` for interactions
   - Document exact steps taken

2. **Local Environment**:
   - Ensure full Docker stack running: `task docker:up:all`
   - Use demo Alpha Vantage API key (already configured)
   - Test against PostgreSQL (persistent data)

3. **Documentation Standards**:
   - Use Markdown format
   - Include code examples where helpful
   - Use tables for structured information
   - Link between related docs
   - Keep language clear and user-friendly

## Deliverables

1. **Primary Documents**:
   - [ ] `docs/EXECUTIVE_SUMMARY.md` (1 page, ~300 words)
   - [ ] `docs/FEATURE_STATUS.md` (2 pages, detailed matrix)
   - [ ] `docs/USER_GUIDE.md` (4-6 pages, comprehensive)
   - [ ] `docs/TECHNICAL_BOUNDARIES.md` (2 pages, limitations & edge cases)

2. **Supporting Materials**:
   - [ ] `docs/screenshots/` directory with key workflow images
   - [ ] Manual testing report in `agent_tasks/progress/`

3. **Updates**:
   - [ ] Update `README.md` with link to new documentation
   - [ ] Update `PROGRESS.md` to reflect documentation completion

## Success Criteria

- [ ] All Phase 1 features documented with clear usage instructions
- [ ] All Phase 2 features documented with current status (complete/partial/planned)
- [ ] At least 10 core user workflows tested manually and documented
- [ ] Known limitations clearly stated (e.g., no sell trades, rate limits, etc.)
- [ ] Executive summary provides clear snapshot of app capabilities
- [ ] Documentation validated through actual app usage (not just code reading)
- [ ] All deliverable documents created and committed

## Out of Scope

- Detailed API documentation (that's separate)
- Developer setup guide (exists in README.md)
- Architecture deep-dives (exists in docs/architecture/)
- Contributing guidelines (future task)

## Testing Notes

**Alpha Vantage Demo Key**: Use `ALPHA_VANTAGE_API_KEY=demo` for testing
- Rate limit: 5 API calls/min, 500 calls/day
- Symbols to test: IBM, AAPL, MSFT, GOOGL, TSCO.LON

**Docker Stack**:
```bash
task docker:up:all    # Start all services
task docker:logs      # View logs
task docker:down      # Stop services
```

**App URLs**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## References

- `PROGRESS.md` - Phase completion tracking
- `project_plan.md` - Original feature specifications
- `docs/architecture/phase*.md` - Technical architecture
- `frontend/tests/e2e/*.spec.ts` - E2E test scenarios (show working features)
- `backend/tests/integration/` - Integration test coverage

## Agent Notes

**Recommended Approach**:
1. Start with manual testing (Phase 1) - spend 1.5-2 hours exploring
2. Take detailed notes during testing
3. Review code/docs (Phase 2) - 30-45 minutes
4. Write documentation (Phase 3) - 1-1.5 hours
5. Validate & refine (Phase 4) - 30 minutes

**Communication**:
- Document surprises or unexpected behavior
- Note any bugs discovered during testing
- Flag unclear boundaries for user confusion

**Format**:
Use clear, friendly language. Think "user manual" not "technical spec."
