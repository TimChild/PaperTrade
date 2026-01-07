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
