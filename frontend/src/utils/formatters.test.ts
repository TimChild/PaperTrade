import { describe, it, expect } from 'vitest'
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatDate,
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
  })
})
