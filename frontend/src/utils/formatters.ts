/**
 * Utility functions for formatting financial data
 */

/**
 * Format a number as currency
 * @param value - The numeric value to format
 * @param currency - The currency code (default: 'USD')
 * @param notation - Formatting notation: 'standard' | 'compact' (default: 'standard')
 * @returns Formatted currency string, or fallback string if value is invalid
 */
export function formatCurrency(
  value: number | undefined | null,
  currency = 'USD',
  notation: 'standard' | 'compact' = 'standard'
): string {
  // Handle invalid values
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '---'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    notation,
    compactDisplay: notation === 'compact' ? 'short' : undefined,
  }).format(value)
}

/**
 * Format a number as percentage
 * @param value - The numeric value to format (as decimal, e.g., 0.05 for 5%)
 * @param showSign - Whether to always show the sign (default: true)
 * @returns Formatted percentage string, or fallback string if value is invalid
 */
export function formatPercent(
  value: number | undefined | null,
  showSign: boolean = true
): string {
  // Handle invalid values
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '---'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: showSign ? 'always' : 'auto',
  }).format(value)
}

/**
 * Format a number with thousand separators
 * @param value - The numeric value to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted number string, or fallback string if value is invalid
 */
export function formatNumber(
  value: number | undefined | null,
  decimals: number = 2
): string {
  // Handle invalid values
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '---'
  }

  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Format a date/time string
 * @param dateString - ISO date string
 * @param format - Format style: true/false for includeTime, 'short' for compact, 'long' for full
 * @returns Formatted date string
 */
export function formatDate(
  dateString: string,
  format: boolean | 'short' | 'long' = true
): string {
  const date = new Date(dateString)

  // 'short' format for chart axis labels (e.g., "Jan 5" or "1/5")
  if (format === 'short') {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
    }).format(date)
  }

  // 'long' format for tooltips (e.g., "January 5, 2026")
  if (format === 'long') {
    return new Intl.DateTimeFormat('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    }).format(date)
  }

  // Legacy boolean support for includeTime
  const includeTime = format === true

  if (includeTime) {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(date)
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

/**
 * Format an epoch milliseconds timestamp as `HH:MM:SS` for use in
 * "last updated" captions. Returns `--` when the timestamp is invalid
 * or zero (e.g. before the first fetch settles).
 */
export function formatClockTime(epochMs: number | undefined | null): string {
  if (
    epochMs === null ||
    epochMs === undefined ||
    !Number.isFinite(epochMs) ||
    epochMs === 0
  ) {
    return '--:--:--'
  }
  const date = new Date(epochMs)
  return new Intl.DateTimeFormat('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

/**
 * Format a timestamp as a compact "X ago" relative-time label.
 *
 * The recent-activity feed (Phase H2) renders timestamps in this form
 * because feed entries are most useful in relative terms ("2m ago"
 * is more informative than "8:42 AM" when scanning a list). The
 * granularity steps coarsen as time passes:
 *
 * - <60s: "just now"
 * - <60m: "Nm ago"
 * - <24h: "Nh ago"
 * - <7d:  "Nd ago"
 * - else: full date via `formatDate`
 *
 * Future timestamps (clock skew) render as "just now" rather than a
 * misleading negative.
 *
 * @param dateString ISO 8601 timestamp.
 * @param now Optional clock override for deterministic tests.
 * @returns Compact "X ago" label.
 */
export function formatRelativeTime(
  dateString: string,
  now: Date = new Date()
): string {
  const then = new Date(dateString)
  const deltaMs = now.getTime() - then.getTime()

  if (deltaMs < 60_000) {
    return 'just now'
  }

  const minutes = Math.floor(deltaMs / 60_000)
  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `${hours}h ago`
  }

  const days = Math.floor(hours / 24)
  if (days < 7) {
    return `${days}d ago`
  }

  return formatDate(dateString, 'short')
}

/**
 * Format a calendar-date-only wire value (YYYY-MM-DD) as a short
 * month-day label, free of timezone shift.
 *
 * Why this exists: `formatDate('2024-06-15', 'short')` constructs
 * `new Date('2024-06-15')`, which JavaScript parses as UTC midnight.
 * `Intl.DateTimeFormat` then formats in the local timezone, so in any
 * tz west of UTC the rendered day is one earlier ('Jun 14' for
 * US/Pacific). For wire values that represent a calendar day with no
 * time component (e.g. `simulated_date` on a backtest agent
 * invocation), we want the rendered label to match the date that
 * shipped over the wire — regardless of the viewer's timezone.
 *
 * Implementation: parse the YYYY-MM-DD components directly and
 * synthesise a `Date` in the *local* timezone via the `(year, month,
 * day)` constructor, which never crosses midnight.
 *
 * Accepts the wider `'short' | 'long' | 'numeric'` format hint, all
 * year-omitting variants of the corresponding `formatDate` styles.
 */
export function formatSimulatedDate(
  isoDate: string,
  format: 'short' | 'long' | 'numeric' = 'short'
): string {
  // Defensive: accept ISO-8601 datetime by trimming the time portion.
  // The L-4 wire format is YYYY-MM-DD but a future API server change
  // could surface YYYY-MM-DDTHH:MM:SS.
  const parts = isoDate.slice(0, 10).split('-')
  if (parts.length !== 3) {
    return isoDate
  }
  const [yearStr, monthStr, dayStr] = parts
  const year = Number(yearStr)
  const month = Number(monthStr) // 1-based on wire
  const day = Number(dayStr)
  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    !Number.isInteger(day)
  ) {
    return isoDate
  }
  // `new Date(year, monthIndex, day)` is local-tz midnight on that
  // local calendar day — no UTC parsing, no DST shift.
  const date = new Date(year, month - 1, day)

  if (format === 'short') {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
    }).format(date)
  }
  if (format === 'numeric') {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(date)
  }
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}
