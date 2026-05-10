import { describe, it, expect } from 'vitest'
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatDate,
  formatClockTime,
  formatRelativeTime,
} from '@/utils/formatters'

describe('formatters', () => {
  describe('formatCurrency', () => {
    it('formats positive values correctly', () => {
      expect(formatCurrency(1000)).toBe('$1,000.00')
      expect(formatCurrency(1234.56)).toBe('$1,234.56')
    })

    it('formats negative values correctly', () => {
      expect(formatCurrency(-1000)).toBe('-$1,000.00')
    })

    it('formats zero correctly', () => {
      expect(formatCurrency(0)).toBe('$0.00')
    })

    it('formats with compact notation', () => {
      expect(formatCurrency(1000, 'USD', 'compact')).toBe('$1K')
      expect(formatCurrency(1500000, 'USD', 'compact')).toBe('$1.5M')
    })

    it('handles NaN gracefully', () => {
      expect(formatCurrency(NaN)).toBe('---')
    })

    it('handles undefined gracefully', () => {
      expect(formatCurrency(undefined)).toBe('---')
    })

    it('handles null gracefully', () => {
      expect(formatCurrency(null)).toBe('---')
    })

    it('handles Infinity gracefully', () => {
      expect(formatCurrency(Infinity)).toBe('---')
      expect(formatCurrency(-Infinity)).toBe('---')
    })
  })

  describe('formatPercent', () => {
    it('formats positive percentages with sign', () => {
      expect(formatPercent(0.05)).toBe('+5.00%')
      expect(formatPercent(0.1234)).toBe('+12.34%')
    })

    it('formats negative percentages with sign', () => {
      expect(formatPercent(-0.05)).toBe('-5.00%')
    })

    it('formats zero correctly', () => {
      expect(formatPercent(0)).toBe('+0.00%')
    })

    it('formats without sign when showSign is false', () => {
      expect(formatPercent(0.05, false)).toBe('5.00%')
    })

    it('handles NaN gracefully', () => {
      expect(formatPercent(NaN)).toBe('---')
    })

    it('handles undefined gracefully', () => {
      expect(formatPercent(undefined)).toBe('---')
    })

    it('handles null gracefully', () => {
      expect(formatPercent(null)).toBe('---')
    })
  })

  describe('formatNumber', () => {
    it('formats numbers with thousand separators', () => {
      expect(formatNumber(1000)).toBe('1,000.00')
      expect(formatNumber(1234567.89)).toBe('1,234,567.89')
    })

    it('respects decimal places parameter', () => {
      expect(formatNumber(100, 0)).toBe('100')
      expect(formatNumber(100.123, 3)).toBe('100.123')
    })

    it('handles NaN gracefully', () => {
      expect(formatNumber(NaN)).toBe('---')
    })

    it('handles undefined gracefully', () => {
      expect(formatNumber(undefined)).toBe('---')
    })

    it('handles null gracefully', () => {
      expect(formatNumber(null)).toBe('---')
    })
  })

  describe('formatDate', () => {
    it('formats date with time by default', () => {
      const result = formatDate('2024-01-15T14:30:00Z')
      expect(result).toContain('Jan')
      expect(result).toContain('15')
      expect(result).toContain('2024')
    })

    it('formats date without time when includeTime is false', () => {
      const result = formatDate('2024-01-15T14:30:00Z', false)
      expect(result).toContain('Jan')
      expect(result).toContain('15')
      expect(result).toContain('2024')
    })

    it('formats date in short format for chart labels', () => {
      const result = formatDate('2024-01-15T14:30:00Z', 'short')
      expect(result).toContain('Jan')
      expect(result).toContain('15')
      expect(result).not.toContain('2024') // Short format doesn't include year
    })

    it('formats date in long format for tooltips', () => {
      const result = formatDate('2024-01-15T14:30:00Z', 'long')
      expect(result).toContain('January') // Full month name
      expect(result).toContain('15')
      expect(result).toContain('2024')
    })
  })

  describe('formatClockTime', () => {
    it('formats epoch ms as HH:MM:SS in 24h', () => {
      // 2024-01-15T14:23:08Z — exact UTC; assertion uses regex so the
      // local timezone offset of the runner doesn't break the test.
      const result = formatClockTime(Date.UTC(2024, 0, 15, 14, 23, 8))
      expect(result).toMatch(/^\d{2}:\d{2}:\d{2}$/)
    })

    it('returns the placeholder for undefined / null / 0', () => {
      expect(formatClockTime(undefined)).toBe('--:--:--')
      expect(formatClockTime(null)).toBe('--:--:--')
      expect(formatClockTime(0)).toBe('--:--:--')
    })

    it('returns the placeholder for non-finite values', () => {
      expect(formatClockTime(NaN)).toBe('--:--:--')
      expect(formatClockTime(Infinity)).toBe('--:--:--')
    })
  })

  describe('formatRelativeTime', () => {
    const NOW = new Date('2026-05-10T12:00:00Z')

    it('renders "just now" for recent events (<60s)', () => {
      const ts = new Date(NOW.getTime() - 30_000).toISOString()
      expect(formatRelativeTime(ts, NOW)).toBe('just now')
    })

    it('renders Nm ago for events within an hour', () => {
      const ts = new Date(NOW.getTime() - 12 * 60_000).toISOString()
      expect(formatRelativeTime(ts, NOW)).toBe('12m ago')
    })

    it('renders Nh ago for events within a day', () => {
      const ts = new Date(NOW.getTime() - 5 * 3_600_000).toISOString()
      expect(formatRelativeTime(ts, NOW)).toBe('5h ago')
    })

    it('renders Nd ago for events within a week', () => {
      const ts = new Date(NOW.getTime() - 3 * 86_400_000).toISOString()
      expect(formatRelativeTime(ts, NOW)).toBe('3d ago')
    })

    it('falls back to short date for events older than a week', () => {
      const ts = new Date(NOW.getTime() - 30 * 86_400_000).toISOString()
      const result = formatRelativeTime(ts, NOW)
      // Older than 7 days — should be a short date format like "Apr 10".
      expect(result).not.toMatch(/ago$/)
    })

    it('renders future timestamps as "just now"', () => {
      // Clock-skew defence: a timestamp slightly in the future
      // shouldn't render as "-1m ago".
      const ts = new Date(NOW.getTime() + 5_000).toISOString()
      expect(formatRelativeTime(ts, NOW)).toBe('just now')
    })
  })
})
