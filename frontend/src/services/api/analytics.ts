/**
 * Analytics API functions
 */
import { apiClient } from './client'

export interface DataPoint {
  date: string
  total_value: number
  cash_balance: number
  holdings_value: number
}

export interface PerformanceMetrics {
  starting_value: number
  ending_value: number
  absolute_gain: number
  percentage_gain: number
  highest_value: number
  lowest_value: number
}

export interface PerformanceResponse {
  portfolio_id: string
  range: string
  data_points: DataPoint[]
  metrics: PerformanceMetrics | null
}

export interface CompositionItem {
  ticker: string
  value: number
  percentage: number
  quantity: number | null
}

export interface CompositionResponse {
  portfolio_id: string
  total_value: number
  composition: CompositionItem[]
}

export type TimeRange = '1W' | '1M' | '3M' | '1Y' | 'ALL'

export const analyticsApi = {
  /**
   * Get portfolio performance data over time
   */
  getPerformance: async (
    portfolioId: string,
    range: TimeRange = '1M'
  ): Promise<PerformanceResponse> => {
    const response = await apiClient.get<PerformanceResponse>(
      `/portfolios/${portfolioId}/performance`,
      {
        params: { range },
      }
    )
    return response.data
  },

  /**
   * Get portfolio composition (asset allocation)
   */
  getComposition: async (portfolioId: string): Promise<CompositionResponse> => {
    const response = await apiClient.get<CompositionResponse>(
      `/portfolios/${portfolioId}/composition`
    )
    return response.data
  },
}
