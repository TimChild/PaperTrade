/**
 * Transaction API functions
 */
import { apiClient } from './client'
import type { TransactionListResponse } from './types'

export interface ListTransactionsParams {
  limit?: number
  offset?: number
  transaction_type?: 'DEPOSIT' | 'WITHDRAWAL' | 'BUY' | 'SELL'
}

export const transactionsApi = {
  /**
   * List transactions for a portfolio with pagination and filtering
   */
  list: async (
    portfolioId: string,
    params?: ListTransactionsParams
  ): Promise<TransactionListResponse> => {
    const response = await apiClient.get<TransactionListResponse>(
      `/portfolios/${portfolioId}/transactions`,
      { params }
    )
    return response.data
  },
}
