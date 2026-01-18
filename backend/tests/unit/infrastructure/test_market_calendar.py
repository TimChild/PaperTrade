"""Unit tests for MarketCalendar.

Tests the US stock market holiday calendar implementation, including:
- All 10 market holidays
- Weekend observation rules
- is_trading_day() validation
- Edge cases and multi-year consistency
"""

from datetime import date

from zebu.infrastructure.market_calendar import MarketCalendar


class TestEasterCalculation:
    """Tests for Easter Sunday calculation using Computus algorithm."""

    def test_easter_2024(self) -> None:
        """Easter 2024 is March 31."""
        assert MarketCalendar._calculate_easter(2024) == date(2024, 3, 31)

    def test_easter_2025(self) -> None:
        """Easter 2025 is April 20."""
        assert MarketCalendar._calculate_easter(2025) == date(2025, 4, 20)

    def test_easter_2026(self) -> None:
        """Easter 2026 is April 5."""
        assert MarketCalendar._calculate_easter(2026) == date(2026, 4, 5)

    def test_easter_edge_case_early(self) -> None:
        """Test early Easter date (March 23, 2008)."""
        # One of the earliest possible Easter dates in recent history
        assert MarketCalendar._calculate_easter(2008) == date(2008, 3, 23)

    def test_easter_edge_case_late(self) -> None:
        """Test late Easter date (April 24, 2011)."""
        # One of the latest possible Easter dates in recent history
        assert MarketCalendar._calculate_easter(2011) == date(2011, 4, 24)


class TestNthWeekday:
    """Tests for _get_nth_weekday helper method."""

    def test_third_monday_january_2024(self) -> None:
        """MLK Day 2024 is January 15 (3rd Monday)."""
        result = MarketCalendar._get_nth_weekday(2024, 1, 0, 3)
        assert result == date(2024, 1, 15)
        assert result.weekday() == 0  # Monday

    def test_third_monday_february_2024(self) -> None:
        """Presidents Day 2024 is February 19 (3rd Monday)."""
        result = MarketCalendar._get_nth_weekday(2024, 2, 0, 3)
        assert result == date(2024, 2, 19)
        assert result.weekday() == 0  # Monday

    def test_last_monday_may_2024(self) -> None:
        """Memorial Day 2024 is May 27 (last Monday)."""
        result = MarketCalendar._get_nth_weekday(2024, 5, 0, -1)
        assert result == date(2024, 5, 27)
        assert result.weekday() == 0  # Monday

    def test_first_monday_september_2024(self) -> None:
        """Labor Day 2024 is September 2 (1st Monday)."""
        result = MarketCalendar._get_nth_weekday(2024, 9, 0, 1)
        assert result == date(2024, 9, 2)
        assert result.weekday() == 0  # Monday

    def test_fourth_thursday_november_2024(self) -> None:
        """Thanksgiving 2024 is November 28 (4th Thursday)."""
        result = MarketCalendar._get_nth_weekday(2024, 11, 3, 4)
        assert result == date(2024, 11, 28)
        assert result.weekday() == 3  # Thursday

    def test_fourth_thursday_november_2025(self) -> None:
        """Thanksgiving 2025 is November 27 (4th Thursday)."""
        result = MarketCalendar._get_nth_weekday(2025, 11, 3, 4)
        assert result == date(2025, 11, 27)
        assert result.weekday() == 3  # Thursday


class TestWeekendObservation:
    """Tests for weekend observation rules."""

    def test_holiday_on_monday(self) -> None:
        """Holiday on Monday should be observed on Monday."""
        monday = date(2024, 1, 1)  # Jan 1, 2024 is Monday
        assert monday.weekday() == 0
        assert MarketCalendar._get_observed_date(monday) == monday

    def test_holiday_on_wednesday(self) -> None:
        """Holiday on Wednesday should be observed on Wednesday."""
        wednesday = date(2024, 7, 3)
        assert wednesday.weekday() == 2
        assert MarketCalendar._get_observed_date(wednesday) == wednesday

    def test_holiday_on_friday(self) -> None:
        """Holiday on Friday should be observed on Friday."""
        friday = date(2024, 5, 31)
        assert friday.weekday() == 4
        assert MarketCalendar._get_observed_date(friday) == friday

    def test_holiday_on_saturday_observed_friday(self) -> None:
        """Holiday on Saturday should be observed on Friday."""
        saturday = date(2026, 7, 4)  # July 4, 2026 is Saturday
        assert saturday.weekday() == 5
        observed = MarketCalendar._get_observed_date(saturday)
        assert observed == date(2026, 7, 3)  # Friday
        assert observed.weekday() == 4

    def test_holiday_on_sunday_observed_monday(self) -> None:
        """Holiday on Sunday should be observed on Monday."""
        # Jan 1, 2023 is Sunday
        sunday = date(2023, 1, 1)
        assert sunday.weekday() == 6
        observed = MarketCalendar._get_observed_date(sunday)
        assert observed == date(2023, 1, 2)  # Monday
        assert observed.weekday() == 0


class TestMarketHolidays2024:
    """Tests for all 10 market holidays in 2024."""

    def test_new_years_day_2024(self) -> None:
        """New Year's Day 2024 - Jan 1 (Monday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 1, 1) in holidays

    def test_mlk_day_2024(self) -> None:
        """MLK Day 2024 - January 15 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 1, 15) in holidays

    def test_presidents_day_2024(self) -> None:
        """Presidents Day 2024 - February 19 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 2, 19) in holidays

    def test_good_friday_2024(self) -> None:
        """Good Friday 2024 - March 29 (2 days before Easter)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        # Easter is March 31, so Good Friday is March 29
        assert date(2024, 3, 29) in holidays

    def test_memorial_day_2024(self) -> None:
        """Memorial Day 2024 - May 27 (last Monday in May)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 5, 27) in holidays

    def test_juneteenth_2024(self) -> None:
        """Juneteenth 2024 - June 19 (Wednesday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 6, 19) in holidays

    def test_independence_day_2024(self) -> None:
        """Independence Day 2024 - July 4 (Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 7, 4) in holidays

    def test_labor_day_2024(self) -> None:
        """Labor Day 2024 - September 2 (1st Monday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 9, 2) in holidays

    def test_thanksgiving_2024(self) -> None:
        """Thanksgiving 2024 - November 28 (4th Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 11, 28) in holidays

    def test_christmas_2024(self) -> None:
        """Christmas 2024 - December 25 (Wednesday)."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert date(2024, 12, 25) in holidays

    def test_total_holidays_2024(self) -> None:
        """Should have exactly 10 holidays in 2024."""
        holidays = MarketCalendar.get_market_holidays(2024)
        assert len(holidays) == 10


class TestMarketHolidays2025:
    """Tests for all 10 market holidays in 2025."""

    def test_new_years_day_2025(self) -> None:
        """New Year's Day 2025 - Jan 1 (Wednesday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 1, 1) in holidays

    def test_mlk_day_2025(self) -> None:
        """MLK Day 2025 - January 20 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 1, 20) in holidays

    def test_presidents_day_2025(self) -> None:
        """Presidents Day 2025 - February 17 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 2, 17) in holidays

    def test_good_friday_2025(self) -> None:
        """Good Friday 2025 - April 18 (2 days before Easter)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        # Easter is April 20, so Good Friday is April 18
        assert date(2025, 4, 18) in holidays

    def test_memorial_day_2025(self) -> None:
        """Memorial Day 2025 - May 26 (last Monday in May)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 5, 26) in holidays

    def test_juneteenth_2025(self) -> None:
        """Juneteenth 2025 - June 19 (Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 6, 19) in holidays

    def test_independence_day_2025(self) -> None:
        """Independence Day 2025 - July 4 (Friday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 7, 4) in holidays

    def test_labor_day_2025(self) -> None:
        """Labor Day 2025 - September 1 (1st Monday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 9, 1) in holidays

    def test_thanksgiving_2025(self) -> None:
        """Thanksgiving 2025 - November 27 (4th Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 11, 27) in holidays

    def test_christmas_2025(self) -> None:
        """Christmas 2025 - December 25 (Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert date(2025, 12, 25) in holidays

    def test_total_holidays_2025(self) -> None:
        """Should have exactly 10 holidays in 2025."""
        holidays = MarketCalendar.get_market_holidays(2025)
        assert len(holidays) == 10


class TestMarketHolidays2026:
    """Tests for all 10 market holidays in 2026."""

    def test_new_years_day_2026_observed(self) -> None:
        """New Year's Day 2026 - Jan 1 (Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 1, 1) in holidays

    def test_mlk_day_2026(self) -> None:
        """MLK Day 2026 - January 19 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 1, 19) in holidays

    def test_presidents_day_2026(self) -> None:
        """Presidents Day 2026 - February 16 (3rd Monday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 2, 16) in holidays

    def test_good_friday_2026(self) -> None:
        """Good Friday 2026 - April 3 (2 days before Easter)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        # Easter is April 5, so Good Friday is April 3
        assert date(2026, 4, 3) in holidays

    def test_memorial_day_2026(self) -> None:
        """Memorial Day 2026 - May 25 (last Monday in May)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 5, 25) in holidays

    def test_juneteenth_2026(self) -> None:
        """Juneteenth 2026 - June 19 (Friday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 6, 19) in holidays

    def test_independence_day_2026_observed(self) -> None:
        """Independence Day 2026 - July 4 (Saturday), observed Friday July 3."""
        holidays = MarketCalendar.get_market_holidays(2026)
        # July 4 is Saturday, so observed on Friday July 3
        assert date(2026, 7, 3) in holidays
        assert date(2026, 7, 4) not in holidays

    def test_labor_day_2026(self) -> None:
        """Labor Day 2026 - September 7 (1st Monday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 9, 7) in holidays

    def test_thanksgiving_2026(self) -> None:
        """Thanksgiving 2026 - November 26 (4th Thursday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 11, 26) in holidays

    def test_christmas_2026(self) -> None:
        """Christmas 2026 - December 25 (Friday)."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 12, 25) in holidays

    def test_total_holidays_2026(self) -> None:
        """Should have exactly 10 holidays in 2026."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert len(holidays) == 10


class TestIsTradingDay:
    """Tests for is_trading_day() method."""

    def test_regular_monday(self) -> None:
        """Regular Monday should be a trading day."""
        # Monday, June 3, 2024 (not a holiday)
        assert MarketCalendar.is_trading_day(date(2024, 6, 3)) is True

    def test_regular_tuesday(self) -> None:
        """Regular Tuesday should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 4)) is True

    def test_regular_wednesday(self) -> None:
        """Regular Wednesday should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 5)) is True

    def test_regular_thursday(self) -> None:
        """Regular Thursday should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 6)) is True

    def test_regular_friday(self) -> None:
        """Regular Friday should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 7)) is True

    def test_saturday_not_trading_day(self) -> None:
        """Saturday should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 8)) is False

    def test_sunday_not_trading_day(self) -> None:
        """Sunday should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 6, 9)) is False

    def test_independence_day_not_trading_day(self) -> None:
        """Independence Day should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 7, 4)) is False

    def test_christmas_not_trading_day(self) -> None:
        """Christmas should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 12, 25)) is False

    def test_thanksgiving_not_trading_day(self) -> None:
        """Thanksgiving should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 11, 28)) is False

    def test_good_friday_not_trading_day(self) -> None:
        """Good Friday should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 3, 29)) is False

    def test_mlk_day_not_trading_day(self) -> None:
        """MLK Day should not be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 1, 15)) is False

    def test_day_before_independence_day_is_trading_day(self) -> None:
        """July 3, 2024 should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 7, 3)) is True

    def test_day_after_independence_day_is_trading_day(self) -> None:
        """July 5, 2024 should be a trading day."""
        assert MarketCalendar.is_trading_day(date(2024, 7, 5)) is True


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_new_years_on_sunday_2023(self) -> None:
        """New Year's 2023 falls on Sunday, observed Monday Jan 2."""
        holidays = MarketCalendar.get_market_holidays(2023)
        # Should have Monday Jan 2 as holiday, not Sunday Jan 1
        assert date(2023, 1, 2) in holidays
        # Sunday Jan 1 is in the set (because _get_observed_date returns Monday,
        # but the actual date Sunday is not added)
        # Actually, let me reconsider - we only add the observed date
        assert date(2023, 1, 1) not in holidays

    def test_christmas_on_saturday_2021(self) -> None:
        """Christmas 2021 falls on Saturday, observed Friday Dec 24."""
        holidays = MarketCalendar.get_market_holidays(2021)
        # Should have Friday Dec 24 as holiday
        assert date(2021, 12, 24) in holidays
        # Saturday Dec 25 should not be in holidays (we add observed date only)
        assert date(2021, 12, 25) not in holidays

    def test_independence_day_on_saturday_2026(self) -> None:
        """July 4, 2026 falls on Saturday, observed Friday July 3."""
        holidays = MarketCalendar.get_market_holidays(2026)
        assert date(2026, 7, 3) in holidays
        # Check that Friday is not a trading day
        assert MarketCalendar.is_trading_day(date(2026, 7, 3)) is False
        # Check that Saturday July 4 is not a trading day (weekend)
        assert MarketCalendar.is_trading_day(date(2026, 7, 4)) is False

    def test_day_after_thanksgiving_black_friday(self) -> None:
        """Black Friday (day after Thanksgiving) should be a trading day.

        Note: Markets close early on Black Friday, but we treat it as a
        full trading day for cache validation purposes.
        """
        # Thanksgiving 2024 is Nov 28, so Black Friday is Nov 29
        assert MarketCalendar.is_trading_day(date(2024, 11, 29)) is True

    def test_christmas_eve_is_trading_day(self) -> None:
        """Christmas Eve should be a trading day (early close but open).

        Note: Markets close early on Christmas Eve, but we treat it as a
        full trading day for cache validation purposes.
        """
        # Christmas 2024 is Dec 25 (Wednesday), so Christmas Eve is Dec 24 (Tuesday)
        assert MarketCalendar.is_trading_day(date(2024, 12, 24)) is True

    def test_july_3_is_trading_day_when_july_4_is_weekday(self) -> None:
        """July 3 should be a trading day when July 4 is a weekday."""
        # July 4, 2024 is Thursday, so July 3 is Wednesday (trading day)
        assert MarketCalendar.is_trading_day(date(2024, 7, 3)) is True

    def test_multiple_years_consistency(self) -> None:
        """Holiday counts should be consistent across years."""
        holidays_2024 = MarketCalendar.get_market_holidays(2024)
        holidays_2025 = MarketCalendar.get_market_holidays(2025)
        holidays_2026 = MarketCalendar.get_market_holidays(2026)

        # Each year should have exactly 10 holidays
        assert len(holidays_2024) == 10
        assert len(holidays_2025) == 10
        assert len(holidays_2026) == 10
