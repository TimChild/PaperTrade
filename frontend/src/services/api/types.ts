/**
 * TypeScript types matching backend API DTOs
 * These types mirror the FastAPI Pydantic models
 */

// Portfolio types
export type PortfolioType = 'PAPER_TRADING' | 'BACKTEST'

export interface PortfolioDTO {
  id: string
  user_id: string
  name: string
  created_at: string // ISO 8601
  portfolio_type?: PortfolioType
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

// Strategy activation types
/**
 * Lifecycle state of a strategy activation.
 *
 * Mirrors `backend/src/zebu/domain/value_objects/activation_status.py:ActivationStatus`.
 *
 * - `ACTIVE` — Activation is enabled and will be executed by the scheduler.
 * - `PAUSED` — Temporarily disabled by the user; can resume to ACTIVE.
 * - `STOPPED` — Permanently terminated; a fresh activation is required to resume.
 * - `ERROR` — Last execution failed; `last_error` should describe why.
 */
export type ActivationStatus = 'ACTIVE' | 'PAUSED' | 'STOPPED' | 'ERROR'

/**
 * Execution cadence for a strategy activation.
 *
 * Mirrors `backend/src/zebu/domain/value_objects/activation_frequency.py:ActivationFrequency`.
 * Phase C1 ships with a single cadence; the union is forward-compatible.
 */
export type ActivationFrequency = 'DAILY_MARKET_CLOSE'

/**
 * Wire shape for a `StrategyActivation`.
 *
 * Mirrors `StrategyActivationResponse` in
 * `backend/src/zebu/adapters/inbound/api/strategy_activations.py`.
 */
export interface StrategyActivationResponse {
  id: string
  user_id: string
  strategy_id: string
  portfolio_id: string
  status: ActivationStatus
  frequency: ActivationFrequency
  last_executed_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

/**
 * Request body for `POST /strategies/{id}/activate`.
 */
export interface ActivateStrategyRequest {
  portfolio_id: string
  frequency?: ActivationFrequency
}

/**
 * Request body for `POST /activations/{id}/deactivate`.
 *
 * The optional `reason` is captured on the activation's `last_error` field
 * (the entity's auxiliary text channel) so the UI can surface it.
 */
export interface DeactivateActivationRequest {
  reason?: string
}

/**
 * Response from `POST /activations/{id}/run-now`.
 *
 * Carries the immediate execution outcome plus the post-run activation state.
 */
export interface RunNowResponse {
  activation: StrategyActivationResponse
  succeeded: boolean
  trades: number
  error: string | null
}

// Exploration task types (Phase H1)
/**
 * Lifecycle status of an exploration task.
 *
 * Mirrors
 * `backend/src/zebu/domain/entities/exploration_task.py:ExplorationTaskStatus`.
 *
 * - `OPEN` — Created by a human; available for any agent to claim.
 * - `IN_PROGRESS` — Claimed by an agent and being worked. (Some UI surfaces
 *   refer to this as "claimed".)
 * - `DONE` — Agent submitted findings and marked it complete.
 * - `ABANDONED` — Cancelled (terminal). Currently `DELETE` is a hard delete
 *   server-side, so abandoned tasks won't show up in the list — but the
 *   entity supports the state and a future "soft abandon" endpoint could
 *   surface it. The UI is forward-compatible.
 */
export type ExplorationTaskStatus =
  | 'OPEN'
  | 'IN_PROGRESS'
  | 'DONE'
  | 'ABANDONED'

/**
 * Optional structured guardrails attached to an exploration task.
 *
 * Mirrors `ConstraintsResponse` /
 * `backend/src/zebu/domain/entities/exploration_task.py:ExplorationConstraints`.
 */
export interface ExplorationConstraintsResponse {
  max_backtests: number | null
  allow_live_activation: boolean
  strategy_type_whitelist: string[] | null
}

/**
 * Typed payload an agent submits when completing a task.
 *
 * Mirrors `FindingsResponse` /
 * `backend/src/zebu/domain/entities/exploration_task.py:ExplorationFindings`.
 *
 * Note: the backend does not surface free-form `links` separately — the
 * agent's narrative `summary` is the primary text channel, and any
 * structured references live in `backtest_run_ids` / `strategy_ids` /
 * the optional bullet-point `notes`.
 */
export interface ExplorationFindingsResponse {
  summary: string
  backtest_run_ids: string[]
  strategy_ids: string[]
  notes: string[] | null
}

/**
 * Wire shape for an `ExplorationTask`.
 *
 * Mirrors `ExplorationTaskResponse` in
 * `backend/src/zebu/adapters/inbound/api/exploration_tasks.py`.
 *
 * `claimed_by` is a free-form string label the agent chose at claim time
 * (typically the API-key label, e.g. "claude-code-laptop-explorer"). The
 * raw user UUID may appear here if the claim was made through a Clerk-only
 * session, but in normal agent operation this is the API key's label.
 */
export interface ExplorationTaskResponse {
  id: string
  created_by: string
  prompt: string
  status: ExplorationTaskStatus
  target_portfolio_id: string | null
  tickers: string[] | null
  constraints: ExplorationConstraintsResponse | null
  claimed_by: string | null
  claimed_at: string | null
  findings: ExplorationFindingsResponse | null
  created_at: string
  updated_at: string
}

/**
 * Request body for `POST /exploration-tasks`.
 *
 * `prompt` is the only required field — every other field is optional.
 */
export interface CreateExplorationTaskRequest {
  prompt: string
  target_portfolio_id?: string
  tickers?: string[]
  constraints?: {
    max_backtests?: number
    allow_live_activation?: boolean
    strategy_type_whitelist?: string[]
  }
}

/**
 * Query params accepted by `GET /exploration-tasks`. The backend supports
 * a `scope=mine|all` toggle (default `all`) and a `status` filter; under
 * `scope=all` the default status is `OPEN` (the queue view).
 */
export interface ListExplorationTasksParams {
  scope?: 'all' | 'mine'
  status?: ExplorationTaskStatus
  limit?: number
  offset?: number
}

// API Key types --------------------------------------------------------------

/**
 * Permission scopes an API key can carry.
 *
 * Mirrors `backend/src/zebu/domain/value_objects/api_key_scope.py`:
 * - `read`: Read-only access (list, get).
 * - `trade`: Write access to trading operations.
 * - `admin`: Administrative access (cannot mint/revoke other API keys —
 *   that path is Clerk-gated only).
 */
export type ApiKeyScope = 'read' | 'trade' | 'admin'

/**
 * Summary of an API key. The raw secret is **never** included here;
 * only on `CreateApiKeyResponse` immediately after minting.
 *
 * Mirrors `ApiKeySummary` in `backend/.../api_keys.py`.
 */
export interface ApiKeySummary {
  id: string
  label: string
  scopes: ApiKeyScope[]
  created_at: string // ISO 8601
  last_used_at: string | null
  revoked_at: string | null
  expires_at: string | null
  is_active: boolean
}

export interface ApiKeyListResponse {
  items: ApiKeySummary[]
  total: number
}

export interface CreateApiKeyRequest {
  label: string
  scopes: ApiKeyScope[]
  expires_at?: string | null // ISO 8601, omit for no expiry
}

/**
 * Response after minting a key. The `raw_key` field is returned **once**.
 * The server keeps only the hash; a lost key must be revoked and re-minted.
 */
export interface CreateApiKeyResponse {
  id: string
  label: string
  scopes: ApiKeyScope[]
  raw_key: string
  created_at: string
  expires_at: string | null
}

// Recent-activity feed (Phase H2) ------------------------------------------

/**
 * Discriminator for the kind of underlying event a row represents.
 *
 * Mirrors the backend enum at
 * `backend/src/zebu/application/dtos/activity_event_dto.py:ActivityEventType`.
 * The wire shape allows unknown future values to degrade gracefully.
 */
export type ActivityEventType =
  | 'trade'
  | 'backtest'
  | 'strategy_created'
  | 'activation_created'
  | 'activation_run'
  | 'task_filed'
  | 'task_claimed'
  | 'task_done'
  | 'api_key_minted'

/**
 * Whether the row was authored via Clerk Bearer (a human via UI) or via
 * an API key (an agent / scheduled task / MCP server).
 *
 * - `user`: Clerk-authenticated. `actor_label` is `null`; the UI typically
 *   renders this as "you" since the feed is per-user.
 * - `api_key`: API-key authenticated. `actor_label` carries the key's
 *   human label.
 */
export type ActorKind = 'user' | 'api_key'

/**
 * The kind of underlying entity a feed row points at.
 *
 * Drives the click-to-navigate behaviour on the frontend: the row's
 * `subject_id` plus `subject_type` together identify the destination
 * detail page.
 */
export type SubjectType =
  | 'portfolio'
  | 'strategy'
  | 'backtest'
  | 'activation'
  | 'task'
  | 'api_key'

/**
 * Wire shape for one row in the recent-activity feed.
 *
 * Mirrors `ActivityEventResponse` in
 * `backend/src/zebu/adapters/inbound/api/activity.py`.
 */
export interface ActivityEventResponse {
  type: ActivityEventType
  occurred_at: string // ISO 8601 UTC
  actor_kind: ActorKind
  actor_label: string | null
  actor_user_id: string
  subject_type: SubjectType
  subject_id: string
  subject_name: string | null
  summary: string
}

/**
 * Query parameters for the activity feed.
 *
 * `event_type` is repeatable (passed as multiple `event_type=...` params
 * when the array has multiple entries).
 */
export interface ListActivityParams {
  limit?: number
  offset?: number
  since?: string // ISO 8601
  actor_label?: string
  event_type?: ActivityEventType[]
}
