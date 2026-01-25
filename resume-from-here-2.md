# Resume Point: Frontend UX & Bug Investigation

**Date**: January 25, 2026
**Status**: Investigation complete, issues identified

---

## What Was Accomplished

### System Check & Investigation
- Successfully updated `resume-from-here.md` with correct Docker commands.
- Booted full stack (`task docker:build && task docker:up:all`) and verified app is running.
- Used Playwright MCP to navigate the site, take screenshots, and test user flows.

### Tests Performed
1. **Chart Visualization**: Checked 1D, 1W, 1M, 3M views.
2. **Trading Flow**: Executed a backdated "Buy" order (IBM, 1 share, 2026-01-22).
3. **Data Verification**: Checked "Daily Change" calculation for the portfolio after the backdated trade.

---

## Identified Issues

### 1. Chart Rendering Issues
- **1M View Layout**: The chart in 1M time range shows data compressed to the right side; the x-axis scale or domain appears incorrect (`chart-1m-issue.png`).
- **1D View on Weekends**: Shows "No price data available". Should likely show the most recent trading session (Friday) instead of an empty state on Sunday.

### 2. Stats & Calculations
- **Portfolio Daily Change**: Shows `+$0.00 (+0.00%)` on the dashboard and portfolio detail.
  - *Context*: Bought IBM backdated to Thursday Jan 22nd. Friday Jan 23rd was a trading day.
  - *Expectation*: Should show the percent change from Thursday close to Friday close (or most recent trading day change).
  - *Observation*: System fails to calculate/display this change, defaulting to 0.

### 3. Console Errors & Bugs
- **Delete Portfolio Error**: Console showed `API error: {type: invalid_quantity, message: Shares must be non-negative...}` when interacting with the dashboard.
- **WebSocket Errors**: Multiple Vite HMR connection refuals in console (likely dev environment noise, but worth noting).

### 4. Analytics UX
- **Empty State**: Analytics page shows "No performance data available yet" even after backdated trades. While strictly "correct" (snapshots generate nightly), the UX could be clearer about *when* data will appear or trigger a recalculation for backdated activity.

---

## Next Steps

**Task Creation**:
Compile these issues into a comprehensive task file (`agent_tasks/180_frontend_ux_and_stats_fixes.md`) for the Frontend/Backend agents to address.

**Priorities**:
1. Fix Chart X-Axis scaling (TradingView config).
2. Fix Portfolio Daily Change calculation (Backend/Service logic).
3. Improve Empty States (1D chart, Analytics).

---

## Quick Commands

```bash
# Check PR status
GH_PAGER="" gh pr list

# Quality checks
task quality:frontend

# Start dev environment (full stack)
task docker:build && task docker:up:all
```
