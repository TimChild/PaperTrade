# Fix Backend Statistics & Daily Change Calculation

**Date**: January 25, 2026
**Agent**: backend-swe
**Context**: Portfolio "Daily Change" and performance stats are failing to calculate correctly for backdated trades or weekend scenarios.

## Objectives
Ensure "Daily Change" and performance metrics are accurate and robust.

## Tasks

### 1. Fix Portfolio "Daily Change" Logic
- **Issue**: After buying an asset backdated to Thursday (e.g., Jan 22), on Sunday (Jan 25), the Portfolio Daily Change shows `$0.00 (0.00%)` despite the asset moving on Friday (Jan 23).
- **Explanation**: The system likely compares "Current Value" vs "Yesterday's Snapshot". If "Yesterday" (Saturday) has no snapshot, or if the snapshot exists but is identical to Friday, it might fail.
- **Requirement**:
    - "Daily Change" should represent the change from the **previous market close**.
    - If today is Sunday, it should compare Friday Close vs Thursday Close (or Current Price vs Friday Close).
    - Ensure `PortfolioServiceImpl.get_portfolio_value` or relevant logic handles "Previous Market Day" lookups correctly.

### 2. Trigger Snapshot on Backdated Trade (Optional/Investigation)
- **Issue**: Backdated trades don't seem to trigger an immediate recalculation of historical performance snapshots.
- **Requirement**:
    - Investigate if we can/should trigger a partial snapshot rebuild when a backdated trade is inserted.
    - At minimum, ensure the *current* dashboard stats reflect the asset's movement since the trade date.

### 3. Validation
- Create a test case:
    - Create portfolio.
    - Insert backdated Buy (3 days ago).
    - Verify Portfolio.daily_change is non-zero (assuming asset price changed).

## Success Criteria
- [ ] Portfolio Daily Change reflects actual market movement for held assets.
- [ ] Stats handle weekend gaps correctly (don't show 0% if Friday had movement).

## References
- `src/domain/services/portfolio_service.py`
- `src/infrastructure/persistence/repositories/price_repository.py`
