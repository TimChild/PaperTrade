import { describe, it, expect } from 'vitest'
import { adaptPortfolio } from './adapters'
import type { PortfolioDTO, BalanceResponse } from '@/services/api/types'

const dto: PortfolioDTO = {
  id: 'p-1',
  user_id: 'u-1',
  name: 'Test Portfolio',
  created_at: '2026-01-01T00:00:00Z',
}

const balance: BalanceResponse = {
  cash_balance: '2150.12',
  holdings_value: '7595.23',
  total_value: '9745.35',
  currency: 'USD',
  as_of: '2026-05-09T15:30:00Z',
  daily_change: '551.11',
  daily_change_percent: '6.14',
}

describe('adaptPortfolio', () => {
  it('parses balance numeric fields and exposes balanceAsOf', () => {
    const portfolio = adaptPortfolio(dto, balance)

    expect(portfolio.id).toBe('p-1')
    expect(portfolio.cashBalance).toBe(2150.12)
    expect(portfolio.totalValue).toBe(9745.35)
    expect(portfolio.dailyChange).toBe(551.11)
    // Backend wire format is whole-percent (6.14); frontend uses decimal (0.0614)
    expect(portfolio.dailyChangePercent).toBeCloseTo(0.0614, 4)
    expect(portfolio.balanceAsOf).toBe('2026-05-09T15:30:00Z')
  })

  it('returns balanceAsOf as undefined when no balance is provided', () => {
    const portfolio = adaptPortfolio(dto, null)
    expect(portfolio.balanceAsOf).toBeUndefined()
    expect(portfolio.totalValue).toBe(0)
  })
})
