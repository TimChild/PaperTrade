/**
 * TypeScript types matching backend API DTOs
 * These types mirror the FastAPI Pydantic models
 */

// Portfolio types
export interface PortfolioDTO {
  id: string
  user_id: string
  name: string
  created_at: string // ISO 8601
}

export interface CreatePortfolioRequest {
  name: string
  initial_deposit: string // Decimal as string
  currency?: string
}

export interface CreatePortfolioResponse {
  portfolio_id: string
  transaction_id: string
}

// Transaction types
export interface TransactionDTO {
  id: string
  portfolio_id: string
  transaction_type: 'DEPOSIT' | 'WITHDRAWAL' | 'BUY' | 'SELL'
  timestamp: string // ISO 8601
  cash_change: string // Decimal as string
  ticker?: string | null
  quantity?: string | null // Decimal as string
  price_per_share?: string | null // Decimal as string
  notes?: string | null
}

export interface TransactionListResponse {
  transactions: TransactionDTO[]
  total_count: number
  limit: number
  offset: number
}

// Cash operation types
export interface DepositRequest {
  amount: string // Decimal as string
  currency?: string
}

export interface WithdrawRequest {
  amount: string // Decimal as string
  currency?: string
}

export interface TransactionResponse {
  transaction_id: string
}

// Trade types
export interface TradeRequest {
  action: 'BUY' | 'SELL'
  ticker: string
  quantity: string // Decimal as string
  as_of?: string // Optional ISO 8601 timestamp for backtesting
}

// Balance types
export interface BalanceResponse {
  cash_balance: string // Decimal as string
  holdings_value: string // Decimal as string
  total_value: string // Decimal as string
  currency: string
  as_of: string // ISO 8601 timestamp
  daily_change: string // Decimal as string - NEW
  daily_change_percent: string // Decimal as string - NEW
}

// Holdings types
export interface HoldingDTO {
  ticker: string
  quantity: string // Decimal as string
  cost_basis: string // Decimal as string
  average_cost_per_share: string | null // Decimal as string
}

export interface HoldingsResponse {
  holdings: HoldingDTO[]
}

// Error response - supports both string and structured errors
export interface ErrorResponse {
  detail: string | StructuredErrorDetail
}

// Structured error details for specific error types
export interface StructuredErrorDetail {
  type: string
  message: string
  // Fields for insufficient_funds
  available?: number
  required?: number
  shortfall?: number
  // Fields for insufficient_shares and invalid_ticker
  ticker?: string
  // Fields for market_data_unavailable
  reason?: string
}

// Strategy types
export type StrategyType =
  | 'BUY_AND_HOLD'
  | 'DOLLAR_COST_AVERAGING'
  | 'MOVING_AVERAGE_CROSSOVER'

export interface StrategyResponse {
  id: string
  user_id: string
  name: string
  strategy_type: StrategyType
  tickers: string[]
  parameters: Record<string, unknown>
  created_at: string
}

export interface CreateStrategyRequest {
  name: string
  strategy_type: StrategyType
  tickers: string[]
  parameters: Record<string, unknown>
}

// Backtest types
export type BacktestStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface BacktestRunResponse {
  id: string
  user_id: string
  strategy_id: string | null
  portfolio_id: string
  backtest_name: string
  start_date: string
  end_date: string
  initial_cash: string // decimal string
  status: BacktestStatus
  created_at: string
  completed_at: string | null
  error_message: string | null
  total_return_pct: string | null // decimal string (e.g. "12.5" means 12.5%)
  max_drawdown_pct: string | null
  annualized_return_pct: string | null
  total_trades: number | null
}

export interface RunBacktestRequest {
  strategy_id: string
  backtest_name: string
  start_date: string // YYYY-MM-DD
  end_date: string
  initial_cash: number
}
