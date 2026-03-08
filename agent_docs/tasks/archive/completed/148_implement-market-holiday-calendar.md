# Task 148: Implement Market Holiday Calendar for Cache Validation

**Agent**: backend-swe
**Priority**: MEDIUM
**Date**: 2026-01-17
**Related**: PR #143 (Task 147 - Weekend cache fix)

## Problem Statement

The weekend cache validation fix (PR #143) successfully prevents wasteful API calls on Saturdays/Sundays, but doesn't account for market holidays. The current `_get_last_trading_day()` method only checks `weekday >= 5` (Sat/Sun).

### Current Limitation

```python
def _get_last_trading_day(self, from_date: datetime) -> datetime:
    """Calculate the most recent trading day from a given date."""
    current_date = from_date.date()
    while current_date.weekday() >= 5:  # Only handles weekends
        current_date -= timedelta(days=1)
    return datetime(current_date.year, current_date.month, current_date.day,
                   21, 0, 0, 0, tzinfo=UTC)
```

### Missing Coverage

US stock markets (NYSE/NASDAQ) are closed on these holidays:
- New Year's Day (Jan 1)
- Martin Luther King Jr. Day (3rd Monday in January)
- Presidents' Day (3rd Monday in February)
- Good Friday (Friday before Easter)
- Memorial Day (Last Monday in May)
- Juneteenth (June 19)
- Independence Day (July 4)
- Labor Day (1st Monday in September)
- Thanksgiving Day (4th Thursday in November)
- Christmas Day (Dec 25)

**Note**: If a holiday falls on a weekend, the market observes it on the nearest weekday (typically Monday for Sunday holidays, Friday for Saturday holidays).

### Impact

Without holiday handling:
- Requests on July 5th (after July 4th) will try to fetch July 4th data → wasteful API call
- Same issue for all 10 market holidays
- Estimated ~10 unnecessary API calls per year per active user

## Objective

Extend the weekend cache fix to include market holidays, making cache validation fully aware of NYSE/NASDAQ trading days.

## Requirements

### 1. Create Market Holiday Calendar Module

**File**: `backend/src/zebu/infrastructure/market_calendar.py`

```python
"""US stock market calendar for NYSE/NASDAQ trading days."""

from datetime import UTC, date, datetime, timedelta
from typing import Set

class MarketCalendar:
    """Calendar of US stock market holidays and trading days."""

    @staticmethod
    def _calculate_easter(year: int) -> date:
        """Calculate Easter Sunday using Computus algorithm (Anonymous Gregorian)."""
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @staticmethod
    def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
        """Get the nth occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)
            n: Which occurrence (1=first, -1=last)
        """
        if n > 0:
            # Find first occurrence of weekday in month
            first = date(year, month, 1)
            first_weekday = first.weekday()
            days_ahead = (weekday - first_weekday) % 7
            first_occurrence = first + timedelta(days=days_ahead)
            # Add (n-1) weeks
            return first_occurrence + timedelta(weeks=n - 1)
        else:
            # Find last occurrence of weekday in month
            # Start from last day of month and work backwards
            if month == 12:
                last = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last = date(year, month + 1, 1) - timedelta(days=1)
            last_weekday = last.weekday()
            days_back = (last_weekday - weekday) % 7
            return last - timedelta(days=days_back)

    @classmethod
    def _get_observed_date(cls, holiday_date: date) -> date:
        """Get the observed date for a holiday.

        If holiday falls on Saturday, observe on Friday.
        If holiday falls on Sunday, observe on Monday.
        """
        if holiday_date.weekday() == 5:  # Saturday
            return holiday_date - timedelta(days=1)
        elif holiday_date.weekday() == 6:  # Sunday
            return holiday_date + timedelta(days=1)
        return holiday_date

    @classmethod
    def get_market_holidays(cls, year: int) -> Set[date]:
        """Get all market holidays for a given year.

        Returns:
            Set of dates when US stock markets are closed
        """
        holidays = set()

        # New Year's Day (January 1)
        holidays.add(cls._get_observed_date(date(year, 1, 1)))

        # Martin Luther King Jr. Day (3rd Monday in January)
        holidays.add(cls._get_nth_weekday(year, 1, 0, 3))  # 0=Monday

        # Presidents' Day (3rd Monday in February)
        holidays.add(cls._get_nth_weekday(year, 2, 0, 3))

        # Good Friday (Friday before Easter)
        easter = cls._calculate_easter(year)
        good_friday = easter - timedelta(days=2)
        holidays.add(good_friday)

        # Memorial Day (Last Monday in May)
        holidays.add(cls._get_nth_weekday(year, 5, 0, -1))

        # Juneteenth (June 19, observed if weekend)
        holidays.add(cls._get_observed_date(date(year, 6, 19)))

        # Independence Day (July 4, observed if weekend)
        holidays.add(cls._get_observed_date(date(year, 7, 4)))

        # Labor Day (1st Monday in September)
        holidays.add(cls._get_nth_weekday(year, 9, 0, 1))

        # Thanksgiving Day (4th Thursday in November)
        holidays.add(cls._get_nth_weekday(year, 11, 3, 4))  # 3=Thursday

        # Christmas Day (December 25, observed if weekend)
        holidays.add(cls._get_observed_date(date(year, 12, 25)))

        return holidays

    @classmethod
    def is_trading_day(cls, check_date: date) -> bool:
        """Check if a given date is a trading day.

        Args:
            check_date: Date to check

        Returns:
            True if market is open, False if weekend or holiday
        """
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check if holiday
        holidays = cls.get_market_holidays(check_date.year)
        return check_date not in holidays
```

### 2. Update AlphaVantageAdapter to Use Market Calendar

**File**: `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py`

Update the `_get_last_trading_day()` method:

```python
from zebu.infrastructure.market_calendar import MarketCalendar

def _get_last_trading_day(self, from_date: datetime) -> datetime:
    """Calculate the most recent trading day from a given date.

    Walks backward from the given date to find the most recent day when
    the US stock market was open (not a weekend or holiday).

    Args:
        from_date: Reference date (UTC)

    Returns:
        Most recent trading day at market close (21:00 UTC)
    """
    current_date = from_date.date()

    # Walk backwards until we hit a trading day
    while not MarketCalendar.is_trading_day(current_date):
        current_date -= timedelta(days=1)

    # Return at market close time (4:00 PM ET = 21:00 UTC)
    return datetime(
        current_date.year,
        current_date.month,
        current_date.day,
        21, 0, 0, 0,
        tzinfo=UTC
    )
```

### 3. Add Comprehensive Tests

**File**: `backend/tests/unit/infrastructure/test_market_calendar.py`

Test coverage requirements:
- ✅ Each holiday calculation (10 tests for 10 holidays)
- ✅ Weekend observation rules (Saturday → Friday, Sunday → Monday)
- ✅ `is_trading_day()` for regular days, weekends, holidays
- ✅ Edge cases: New Year's on Sunday, Christmas on Saturday, etc.
- ✅ Multiple years (2024, 2025, 2026) to verify algorithm consistency

**File**: `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_holidays.py`

Integration test coverage:
- ✅ Cache validation after July 4th holiday
- ✅ Cache validation after Thanksgiving
- ✅ Cache validation after Christmas
- ✅ Multi-day holiday weekend (e.g., Thanksgiving Thursday → request on Monday)
- ✅ Verify no API calls when cache has pre-holiday data

Example test structure:

```python
def test_cache_complete_after_independence_day_holiday(
    alpha_vantage_adapter: AlphaVantageAdapter
) -> None:
    """Should accept July 3rd data as complete when requesting on July 5th."""
    ticker = Ticker("AAPL")

    # Friday, July 5, 2024, 10:00 AM (after July 4th holiday)
    mock_now = datetime(2024, 7, 5, 10, 0, 0, tzinfo=UTC)

    with patch("zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Request data through Friday (July 5)
        start = datetime(2024, 6, 28, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 7, 5, 23, 59, 59, tzinfo=UTC)

        # Cache has data through July 3 (last trading day before holiday)
        cached_data = [
            create_price_point(ticker, datetime(2024, 6, 28, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 1, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 2, 21, 0, 0, tzinfo=UTC)),
            create_price_point(ticker, datetime(2024, 7, 3, 21, 0, 0, tzinfo=UTC)),  # Last trading day
        ]

        # Should be complete (market closed July 4, not open yet on July 5)
        result = alpha_vantage_adapter._is_cache_complete(cached_data, start, end)

        assert result is True
```

### 4. Update Documentation

Add holiday handling documentation to the PR #143 progress doc or create a new one explaining:
- Which holidays are covered
- How observation rules work
- Edge cases handled
- Testing approach

## Success Criteria

1. ✅ `MarketCalendar` class correctly identifies all 10 US market holidays
2. ✅ Weekend observation rules work correctly (Sat→Fri, Sun→Mon)
3. ✅ `_get_last_trading_day()` uses `MarketCalendar.is_trading_day()`
4. ✅ No wasteful API calls on days after holidays
5. ✅ All existing tests still pass (571 backend tests)
6. ✅ New tests added for holiday scenarios (aim for 20+ new tests)
7. ✅ Code passes ruff linting and pyright type checking
8. ✅ Complete type hints (no `Any`)

## Implementation Notes

### Market Close Time
- US markets close at 4:00 PM Eastern Time
- 4:00 PM ET = 21:00 UTC (standard time) or 20:00 UTC (daylight saving)
- For simplicity, use 21:00 UTC consistently (acceptable margin of error)

### Early Closes
Markets close early (1:00 PM ET) on:
- Day before Independence Day (if weekday)
- Black Friday (day after Thanksgiving)
- Christmas Eve (if weekday)

**Decision**: Treat early closes as full trading days for cache validation purposes. This is acceptable since we're checking if data *exists*, not when it was generated.

### Future Enhancements (Out of Scope)
- Real-time market status API (for unexpected closures)
- Pre-market and after-hours trading times
- International market calendars (LSE, TSE, etc.)

## Testing Strategy

1. **Unit tests**: Test `MarketCalendar` in isolation
2. **Integration tests**: Test `_get_last_trading_day()` with real holiday dates
3. **Regression tests**: Ensure weekend handling (PR #143) still works
4. **Historical validation**: Run against known holiday dates from 2020-2026

## Related Files

- `backend/src/zebu/infrastructure/market_calendar.py` (NEW)
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py` (MODIFY)
- `backend/tests/unit/infrastructure/test_market_calendar.py` (NEW)
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_holidays.py` (NEW)
- `backend/tests/unit/adapters/outbound/market_data/test_alpha_vantage_weekend_cache.py` (UPDATE - add import)

## Deployment

After merge:
1. Deploy to production via `task proxmox-vm:deploy`
2. Monitor logs for holiday behavior (next test: MLK Day - Jan 20, 2026)
3. Verify no wasteful API calls on holiday weekends

## Definition of Done

- [ ] `MarketCalendar` class implemented with all 10 holidays
- [ ] `_get_last_trading_day()` uses market calendar
- [ ] 20+ new tests for holiday scenarios (unit + integration)
- [ ] All existing 571 backend tests pass
- [ ] No linting/type errors
- [ ] Documentation updated
- [ ] CI checks green
- [ ] Deployed to production
