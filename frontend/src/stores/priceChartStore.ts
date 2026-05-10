/**
 * Shared UI state for price charts.
 *
 * Lifts the timeframe selector (1D / 1W / 1M / 3M / 1Y / ALL) from per-chart
 * local state to a single store so every `LightweightPriceChart` instance on
 * a page reflects the same timeframe. Clicking a timeframe button on any
 * chart updates all of them.
 *
 * State is persisted to `localStorage` so the user's last-chosen timeframe
 * survives a reload.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { TimeRange } from '@/types/price'

export const PRICE_CHART_DEFAULT_TIMEFRAME: TimeRange = '1M'

export interface PriceChartState {
  selectedTimeframe: TimeRange
  setSelectedTimeframe: (timeframe: TimeRange) => void
}

export const usePriceChartStore = create<PriceChartState>()(
  persist(
    (set) => ({
      selectedTimeframe: PRICE_CHART_DEFAULT_TIMEFRAME,
      setSelectedTimeframe: (timeframe: TimeRange): void => {
        set({ selectedTimeframe: timeframe })
      },
    }),
    {
      name: 'zebu-price-chart-store',
      storage: createJSONStorage(() => localStorage),
      version: 1,
      // Only persist the selected timeframe, never the setter.
      partialize: (state): Pick<PriceChartState, 'selectedTimeframe'> => ({
        selectedTimeframe: state.selectedTimeframe,
      }),
    }
  )
)
