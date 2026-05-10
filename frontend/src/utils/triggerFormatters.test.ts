/**
 * Tests for the trigger-specific formatters (Phase G-1).
 *
 * These pure-function helpers feed both the trigger list table and the fire
 * log view — keeping their contract obvious here means the surfaces above
 * only need to assert "is the right formatter called", not "did it render
 * the right string."
 */
import { describe, it, expect } from 'vitest'
import {
  formatCooldown,
  formatConditionSummary,
  formatFireSnapshot,
} from './triggerFormatters'
import type { ConditionType, TriggerFireResponse } from '@/services/api/types'

describe('formatCooldown', () => {
  it('renders zero as "none"', () => {
    expect(formatCooldown(0)).toBe('none')
  })

  it('returns dash for negative or non-finite values', () => {
    expect(formatCooldown(-1)).toBe('—')
    expect(formatCooldown(Number.NaN)).toBe('—')
  })

  it('renders seconds under 60 with the s suffix', () => {
    expect(formatCooldown(30)).toBe('30s')
  })

  it('renders whole-minute values as "Nm"', () => {
    expect(formatCooldown(300)).toBe('5m')
  })

  it('renders mixed minutes + seconds', () => {
    expect(formatCooldown(125)).toBe('2m 5s')
  })

  it('renders whole-hour values as "Nh"', () => {
    expect(formatCooldown(3600)).toBe('1h')
    expect(formatCooldown(21_600)).toBe('6h')
  })

  it('renders mixed hours + minutes', () => {
    expect(formatCooldown(3900)).toBe('1h 5m')
  })

  it('renders whole-day values as "Nd"', () => {
    expect(formatCooldown(86_400)).toBe('1d')
  })

  it('renders mixed days + hours', () => {
    expect(formatCooldown(90_000)).toBe('1d 1h')
  })
})

describe('formatConditionSummary', () => {
  it('summarises DRAWDOWN_THRESHOLD with metric label', () => {
    const summary = formatConditionSummary('DRAWDOWN_THRESHOLD', {
      threshold_pct: '5',
      lookback_days: 3,
      metric: 'PORTFOLIO_TOTAL',
    })
    expect(summary).toBe('Drawdown > 5% over 3d (portfolio)')
  })

  it('renders per-ticker drawdown variant', () => {
    const summary = formatConditionSummary('DRAWDOWN_THRESHOLD', {
      threshold_pct: '10',
      lookback_days: 7,
      metric: 'PER_TICKER',
    })
    expect(summary).toBe('Drawdown > 10% over 7d (per ticker)')
  })

  it('summarises VOLATILITY_SPIKE with all-tickers fallback', () => {
    const summary = formatConditionSummary('VOLATILITY_SPIKE', {
      threshold_pct: '30',
      over_days: 14,
      tickers: null,
    })
    expect(summary).toBe('Volatility > 30% over 14d (all tickers)')
  })

  it('summarises VOLATILITY_SPIKE with concrete tickers', () => {
    const summary = formatConditionSummary('VOLATILITY_SPIKE', {
      threshold_pct: '40',
      over_days: 21,
      tickers: ['AAPL', 'MSFT'],
    })
    expect(summary).toBe('Volatility > 40% over 21d (AAPL, MSFT)')
  })

  it('summarises EARNINGS_PROXIMITY', () => {
    const summary = formatConditionSummary('EARNINGS_PROXIMITY', {
      days_before: 3,
      tickers: ['NVDA'],
    })
    expect(summary).toBe('Earnings within 3d (NVDA)')
  })

  it('flags CUSTOM_RULE as unsupported', () => {
    const summary = formatConditionSummary('CUSTOM_RULE', {})
    expect(summary).toBe('Custom rule (unsupported)')
  })

  it('falls back to the condition type when params shape is unknown', () => {
    // Cast through unknown to allow an invented condition type for the
    // resilience test.
    const summary = formatConditionSummary(
      'WEIRD_UNKNOWN' as unknown as ConditionType,
      {}
    )
    expect(summary).toBe('WEIRD_UNKNOWN')
  })
})

describe('formatFireSnapshot', () => {
  const baseFire: TriggerFireResponse = {
    id: 'fire-1',
    trigger_id: 'trigger-1',
    activation_id: 'activation-1',
    fired_at: '2026-05-09T12:00:00Z',
    condition_evaluation_data: {},
    agent_invocation_id: null,
    agent_response: 'HOLD',
    agent_response_raw: '',
    resulting_trade_id: null,
    resulting_modify_payload: null,
    resulting_exploration_task_id: null,
    latency_ms: 100,
    api_key_id_used: 'key-1',
  }

  it('renders drawdown snapshots with the percent', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: {
        drawdown_pct: '10.5',
        peak_value: '10000',
      },
    })
    expect(snapshot).toBe('Drawdown 10.5%')
  })

  it('appends ticker when present on a drawdown snapshot', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: {
        drawdown_pct: '8.2',
        ticker: 'AAPL',
      },
    })
    expect(snapshot).toBe('Drawdown 8.2% (AAPL)')
  })

  it('renders volatility snapshots (realised spelling)', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: {
        realised_vol_pct: '35.0',
        ticker: 'TSLA',
      },
    })
    expect(snapshot).toBe('Volatility 35.0% TSLA')
  })

  it('renders volatility snapshots (US spelling fallback)', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: {
        realized_vol_pct: '40.0',
      },
    })
    expect(snapshot).toBe('Volatility 40.0%')
  })

  it('renders earnings-proximity snapshots', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: {
        ticker: 'NVDA',
        days_until: 2,
      },
    })
    expect(snapshot).toBe('NVDA earnings in 2d')
  })

  it('falls back to keys when shape is unrecognised', () => {
    const snapshot = formatFireSnapshot({
      ...baseFire,
      condition_evaluation_data: { foo: 1, bar: 2, baz: 3, extra: 'a' },
    })
    expect(snapshot).toBe('foo, bar, baz')
  })

  it('returns dash for empty snapshot', () => {
    expect(formatFireSnapshot(baseFire)).toBe('—')
  })
})
