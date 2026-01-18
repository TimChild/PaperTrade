"""US stock market calendar for NYSE/NASDAQ trading days.

This module provides utilities for determining when US stock markets are open
or closed based on weekends and official market holidays.

The calendar includes all 10 standard US market holidays:
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

Weekend observation rules:
- If holiday falls on Saturday, observed on Friday
- If holiday falls on Sunday, observed on Monday
"""

from datetime import date, timedelta


class MarketCalendar:
    """Calendar of US stock market holidays and trading days.

    This class provides methods to determine when US stock markets (NYSE/NASDAQ)
    are open for trading. Markets are closed on weekends and official holidays.

    Example:
        >>> from datetime import date
        >>> calendar = MarketCalendar()
        >>> # Check if Independence Day 2024 is a trading day
        >>> calendar.is_trading_day(date(2024, 7, 4))
        False
        >>> # Get all holidays for 2024
        >>> holidays = calendar.get_market_holidays(2024)
        >>> len(holidays)
        10
    """

    @staticmethod
    def _calculate_easter(year: int) -> date:
        """Calculate Easter Sunday using Computus algorithm (Anonymous Gregorian).

        This algorithm computes the date of Easter Sunday for any Gregorian
        calendar year. Easter is used to calculate Good Friday (2 days before).

        Args:
            year: Year to calculate Easter for

        Returns:
            Date of Easter Sunday for the given year

        Example:
            >>> MarketCalendar._calculate_easter(2024)
            datetime.date(2024, 3, 31)
            >>> MarketCalendar._calculate_easter(2025)
            datetime.date(2025, 4, 20)
        """
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
        l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @staticmethod
    def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
        """Get the nth occurrence of a weekday in a month.

        This is used to calculate floating holidays like MLK Day (3rd Monday in
        January) or Memorial Day (last Monday in May).

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)
            n: Which occurrence (1=first, 2=second, 3=third, 4=fourth, -1=last)

        Returns:
            Date of the nth occurrence of the weekday

        Example:
            >>> # Get 3rd Monday in January 2024
            >>> MarketCalendar._get_nth_weekday(2024, 1, 0, 3)
            datetime.date(2024, 1, 15)
            >>> # Get last Monday in May 2024
            >>> MarketCalendar._get_nth_weekday(2024, 5, 0, -1)
            datetime.date(2024, 5, 27)
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

        If a holiday falls on a weekend, the market observes it on the nearest
        weekday according to standard US federal holiday rules.

        Args:
            holiday_date: The actual date of the holiday

        Returns:
            The date when the market will be closed for this holiday

        Example:
            >>> # Christmas 2021 fell on Saturday
            >>> MarketCalendar._get_observed_date(date(2021, 12, 25))
            datetime.date(2021, 12, 24)  # Observed Friday
            >>> # New Year's 2023 fell on Sunday
            >>> MarketCalendar._get_observed_date(date(2023, 1, 1))
            datetime.date(2023, 1, 2)  # Observed Monday
        """
        if holiday_date.weekday() == 5:  # Saturday
            return holiday_date - timedelta(days=1)
        elif holiday_date.weekday() == 6:  # Sunday
            return holiday_date + timedelta(days=1)
        return holiday_date

    @classmethod
    def get_market_holidays(cls, year: int) -> set[date]:
        """Get all market holidays for a given year.

        Returns the set of dates when US stock markets (NYSE/NASDAQ) are closed
        for holidays. This includes all 10 standard market holidays with weekend
        observation rules applied.

        Args:
            year: Year to get holidays for

        Returns:
            Set of dates when US stock markets are closed

        Example:
            >>> holidays = MarketCalendar.get_market_holidays(2024)
            >>> date(2024, 7, 4) in holidays  # Independence Day
            True
            >>> len(holidays)
            10
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

        A trading day is any weekday (Monday-Friday) that is not a market holiday.

        Args:
            check_date: Date to check

        Returns:
            True if market is open, False if weekend or holiday

        Example:
            >>> # Regular weekday
            >>> MarketCalendar.is_trading_day(date(2024, 6, 12))
            True
            >>> # Saturday
            >>> MarketCalendar.is_trading_day(date(2024, 6, 15))
            False
            >>> # Independence Day
            >>> MarketCalendar.is_trading_day(date(2024, 7, 4))
            False
        """
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check if holiday
        holidays = cls.get_market_holidays(check_date.year)
        return check_date not in holidays
