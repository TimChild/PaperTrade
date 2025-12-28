/**
 * Portfolio API functions
 */
import { apiClient } from './client'
import type {
  PortfolioDTO,
  CreatePortfolioRequest,
  CreatePortfolioResponse,
  BalanceResponse,
  HoldingsResponse,
  DepositRequest,
  WithdrawRequest,
  TransactionResponse,
  TradeRequest,
} from './types'

export const portfoliosApi = {
  /**
   * Create a new portfolio with initial deposit
   */
  create: async (data: CreatePortfolioRequest): Promise<CreatePortfolioResponse> => {
    const response = await apiClient.post<CreatePortfolioResponse>('/portfolios', data)
    return response.data
  },

  /**
   * Get all portfolios for the current user
   */
  list: async (): Promise<PortfolioDTO[]> => {
    const response = await apiClient.get<PortfolioDTO[]>('/portfolios')
    return response.data
  },

  /**
   * Get a specific portfolio by ID
   */
  getById: async (portfolioId: string): Promise<PortfolioDTO> => {
    const response = await apiClient.get<PortfolioDTO>(`/portfolios/${portfolioId}`)
    return response.data
  },

  /**
   * Get cash balance for a portfolio
   */
  getBalance: async (portfolioId: string): Promise<BalanceResponse> => {
    const response = await apiClient.get<BalanceResponse>(
      `/portfolios/${portfolioId}/balance`
    )
    return response.data
  },

  /**
   * Get stock holdings for a portfolio
   */
  getHoldings: async (portfolioId: string): Promise<HoldingsResponse> => {
    const response = await apiClient.get<HoldingsResponse>(
      `/portfolios/${portfolioId}/holdings`
    )
    return response.data
  },

  /**
   * Deposit cash into a portfolio
   */
  deposit: async (
    portfolioId: string,
    data: DepositRequest
  ): Promise<TransactionResponse> => {
    const response = await apiClient.post<TransactionResponse>(
      `/portfolios/${portfolioId}/deposit`,
      data
    )
    return response.data
  },

  /**
   * Withdraw cash from a portfolio
   */
  withdraw: async (
    portfolioId: string,
    data: WithdrawRequest
  ): Promise<TransactionResponse> => {
    const response = await apiClient.post<TransactionResponse>(
      `/portfolios/${portfolioId}/withdraw`,
      data
    )
    return response.data
  },

  /**
   * Execute a trade (buy or sell)
   */
  executeTrade: async (
    portfolioId: string,
    data: TradeRequest
  ): Promise<TransactionResponse> => {
    const response = await apiClient.post<TransactionResponse>(
      `/portfolios/${portfolioId}/trades`,
      data
    )
    return response.data
  },
}
