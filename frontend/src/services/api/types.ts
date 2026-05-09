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

/**
 * Generic paginated response envelope used by all backend list endpoints.
 *
 * The backend returns this exact shape from `PaginatedResponse[T]` (see
 * `backend/src/zebu/adapters/inbound/api/schemas/pagination.py`).
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
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

/**
 * Stable, machine-readable error codes emitted by the backend.
 *
 * Mirrors `backend/src/zebu/adapters/inbound/api/schemas/errors.py:ErrorCode`.
 * Open-ended `string` so unknown codes from older/newer servers degrade
 * gracefully into "default" handling.
 */
export type ErrorCode =
  | 'insufficient_funds'
  | 'insufficient_shares'
  | 'invalid_ticker'
  | 'invalid_quantity'
  | 'invalid_money'
  | 'ticker_not_found'
  | 'market_data_unavailable'
  | 'invalid_strategy'
  | 'validation_error'
  | 'not_found'
  | 'unauthorized'
  | 'forbidden'
  | 'internal_error'
  | (string & {})

/**
 * Standard error envelope returned from every backend 4xx/5xx response.
 *
 * Mirrors `backend/src/zebu/adapters/inbound/api/schemas/errors.py:ErrorResponse`.
 * `detail` is always a human-readable string; structured payload now lives in
 * `code` (machine-readable) and `fields` (per-field map: validation messages
 * OR auxiliary data such as `available`, `required`, `shortfall`).
 */
export interface ErrorResponse {
  detail: string
  code?: ErrorCode | null
  fields?: Record<string, string> | null
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
