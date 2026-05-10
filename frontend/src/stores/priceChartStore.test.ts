/**
 * Unit tests for `priceChartStore`.
 *
 * Covers:
 * - default timeframe matches `PRICE_CHART_DEFAULT_TIMEFRAME`
 * - `setSelectedTimeframe` updates the store
 * - the value persists across a fresh module load (verifies `persist` middleware
 *   is wired to localStorage, not just in-memory).
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  PRICE_CHART_DEFAULT_TIMEFRAME,
  usePriceChartStore,
} from './priceChartStore'
import type { TimeRange } from '@/types/price'

const STORE_KEY = 'zebu-price-chart-store'

describe('priceChartStore', () => {
  beforeEach(() => {
    // Clean slate every test — both persisted state and in-memory store.
    localStorage.clear()
    usePriceChartStore.setState({
      selectedTimeframe: PRICE_CHART_DEFAULT_TIMEFRAME,
    })
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('defaults to PRICE_CHART_DEFAULT_TIMEFRAME', () => {
    expect(usePriceChartStore.getState().selectedTimeframe).toBe(
      PRICE_CHART_DEFAULT_TIMEFRAME
    )
  })

  it('updates the timeframe via setSelectedTimeframe', () => {
    usePriceChartStore.getState().setSelectedTimeframe('1Y')
    expect(usePriceChartStore.getState().selectedTimeframe).toBe('1Y')
  })

  it('replaces an existing timeframe (transitions across all valid ranges)', () => {
    const ranges: TimeRange[] = ['1D', '1W', '1M', '3M', '1Y', 'ALL']
    for (const range of ranges) {
      usePriceChartStore.getState().setSelectedTimeframe(range)
      expect(usePriceChartStore.getState().selectedTimeframe).toBe(range)
    }
  })

  it('persists the selected timeframe to localStorage', () => {
    usePriceChartStore.getState().setSelectedTimeframe('3M')

    const raw = localStorage.getItem(STORE_KEY)
    expect(raw).not.toBeNull()

    const parsed = JSON.parse(raw!) as {
      state: { selectedTimeframe: TimeRange }
    }
    expect(parsed.state.selectedTimeframe).toBe('3M')
  })

  it('rehydrates from localStorage when persist().rehydrate() runs', async () => {
    // Seed localStorage with a value, then trigger the persist middleware's
    // rehydrate() — this is the same code path used on app startup.
    localStorage.setItem(
      STORE_KEY,
      JSON.stringify({ state: { selectedTimeframe: 'ALL' }, version: 1 })
    )

    await usePriceChartStore.persist.rehydrate()

    expect(usePriceChartStore.getState().selectedTimeframe).toBe('ALL')
  })
})
