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
 * Primary backtest metrics for the recommended candidate (Phase E2).
 *
 * Mirrors `MetricsResponse` /
 * `backend/.../exploration_task.py:ExplorationFindingsMetrics`.
 *
 * Decimal-shaped fields are wire strings (e.g. `"24.4"` means +24.4%) —
 * same convention used for `BacktestRunResponse` metric columns.
 * `total_return_pct` is the only required field; everything else is
 * optional because not every backtest produces all metrics.
 */
export interface ExplorationFindingsMetricsResponse {
  total_return_pct: string
  sharpe_ratio: string | null
  max_drawdown_pct: string | null
  n_trades: number | null
  annualized_return_pct: string | null
}

/**
 * Comparison of the recommended candidate to a baseline backtest (Phase E2).
 *
 * Mirrors `ComparisonResponse` /
 * `backend/.../exploration_task.py:ExplorationFindingsComparison`.
 *
 * Deltas are signed: positive means the candidate outperformed the
 * baseline. The baseline strategy/backtest IDs should also appear in the
 * parent finding's `strategy_ids` / `backtest_run_ids` so a reader can
 * navigate to them.
 */
export interface ExplorationFindingsComparisonResponse {
  baseline_strategy_id: string
  baseline_total_return_pct: string
  delta_total_return_pct: string
  delta_sharpe: string | null
}

/**
 * Typed payload an agent submits when completing a task.
 *
 * Mirrors `FindingsResponse` /
 * `backend/src/zebu/domain/entities/exploration_task.py:ExplorationFindings`.
 *
 * The narrative `summary` is the primary text channel; structured
 * references live in `backtest_run_ids` / `strategy_ids` / the optional
 * bullet-point `notes`.
 *
 * Phase E2 added the structured recommendation fields. They are all
 * optional — narrative-only findings (negative results, no clear winner)
 * leave them as `null` and rely on `summary`.
 */
export interface ExplorationFindingsResponse {
  summary: string
  backtest_run_ids: string[]
  strategy_ids: string[]
  notes: string[] | null
  recommended_strategy_id: string | null
  /**
   * Free-form per-strategy-type parameter dict — its shape varies by
   * strategy type (MA-crossover has `fast_window`/`slow_window`/
   * `invest_fraction`; DCA has `frequency_days`/`amount_per_period`/
   * `allocation`; etc.). Rendered as a key/value list in the UI;
   * specific renderers can switch on the recommended strategy's type
   * to produce a typed view.
   */
  recommended_parameters: Record<string, unknown> | null
  metrics: ExplorationFindingsMetricsResponse | null
  comparison_to_baseline: ExplorationFindingsComparisonResponse | null
  confidence: number | null
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

// Triggers (Phase F + G-1) ----------------------------------------------------

/**
 * Discriminator for the trigger's evaluation type.
 *
 * Mirrors `backend/src/zebu/domain/value_objects/trigger_condition.py:ConditionType`.
 *
 * - `DRAWDOWN_THRESHOLD` — fires when the activation's portfolio (or a single
 *   ticker, depending on `metric`) is down >= `threshold_pct` from its
 *   `lookback_days`-window peak.
 * - `VOLATILITY_SPIKE` — fires when realised volatility of any covered ticker
 *   over `over_days` exceeds `threshold_pct` (annualised).
 * - `EARNINGS_PROXIMITY` — fires when any covered ticker's next earnings date
 *   is within `days_before` trading days.
 * - `CUSTOM_RULE` — reserved enum value; rejected at construction time per
 *   Phase F design Q1. The UI surfaces this as a disabled option with a
 *   tooltip explaining the deferral.
 */
export type ConditionType =
  | 'DRAWDOWN_THRESHOLD'
  | 'VOLATILITY_SPIKE'
  | 'EARNINGS_PROXIMITY'
  | 'CUSTOM_RULE'

/**
 * Drawdown metric variant.
 *
 * Mirrors `DrawdownMetric` in
 * `backend/src/zebu/domain/value_objects/trigger_condition.py`.
 */
export type DrawdownMetric = 'PORTFOLIO_TOTAL' | 'PER_TICKER'

/**
 * Lifecycle state for a `StrategyConditionTrigger`.
 *
 * Mirrors `TriggerStatus` in
 * `backend/src/zebu/domain/value_objects/trigger_status.py`.
 *
 * - `ACTIVE` — Evaluator will check this trigger each tick.
 * - `PAUSED` — Temporarily disabled by the user; can resume.
 * - `EXPIRED` — Terminal. Set by the evaluator when `expires_at` lapses, or
 *   by a user-driven DELETE (soft-delete).
 * - `MANUALLY_DISABLED` — Terminal. Set by the kill switch. Per Phase F Q3,
 *   the lift path is "delete and recreate", not PATCH.
 */
export type TriggerStatus =
  | 'ACTIVE'
  | 'PAUSED'
  | 'EXPIRED'
  | 'MANUALLY_DISABLED'

/**
 * Discrete outcomes the woken agent (or the executor's downgrade path) can
 * record on a `TriggerFireRecord`.
 *
 * Mirrors `AgentDecision` in
 * `backend/src/zebu/domain/value_objects/agent_decision.py`.
 *
 * - `BUY` / `SELL` — trade was executed (see `resulting_trade_id`).
 * - `HOLD` — no action (the most common no-op outcome).
 * - `MODIFY` — strategy parameters were updated (`resulting_modify_payload`).
 * - `NEEDS_HUMAN` — exploration task filed for follow-up
 *   (`resulting_exploration_task_id`).
 * - `INVOCATION_FAILED` — system-recorded when the agent invocation errored;
 *   the fire is still in the audit log so the failure is visible.
 */
export type AgentDecision =
  | 'BUY'
  | 'SELL'
  | 'HOLD'
  | 'MODIFY'
  | 'NEEDS_HUMAN'
  | 'INVOCATION_FAILED'

/**
 * Per-condition params shapes. Discriminated by `ConditionType`. Wire format
 * is a JSON object; the backend `params_from_dict(condition_type, raw)`
 * factory reconstructs the typed VO server-side.
 *
 * Decimal-shaped fields ride the wire as strings (e.g. `"5.0"` for 5%) to
 * preserve precision — same convention as backtest metrics.
 */
export interface DrawdownConditionParams {
  threshold_pct: string // decimal as string (0, 100]
  lookback_days: number // integer [1, 365]
  metric: DrawdownMetric
}

export interface VolatilityConditionParams {
  threshold_pct: string // decimal as string (0, 500]
  over_days: number // integer [5, 90]
  tickers: string[] | null // null = "all strategy tickers"
}

export interface EarningsConditionParams {
  days_before: number // integer [1, 14]
  tickers: string[] | null // null = "all strategy tickers"
}

/**
 * Wire shape for a `StrategyConditionTrigger`.
 *
 * Mirrors `TriggerResponse` in
 * `backend/src/zebu/adapters/inbound/api/schemas/triggers.py`.
 *
 * `condition_params` is kept as a structural `Record<string, unknown>` on the
 * type to match the backend's wire format (JSON dict). Renderers narrow it
 * via `condition_type` before accessing keyed fields.
 */
/**
 * Trigger invocation mode (Phase J — Task #213).
 *
 * `direct` — the default. The platform calls Anthropic Haiku inline when
 *   the condition fires.
 * `queue` — Pattern B. The platform files an URGENT `ExplorationTask`
 *   for the user's desktop agent (Claude Code / Desktop / Gemini CLI) to
 *   claim via MCP and process with that client's own connectors.
 *
 * Mirrors the `TriggerInvocationMode` StrEnum on the backend.
 */
export type TriggerInvocationMode = 'direct' | 'queue'

export interface TriggerResponse {
  id: string
  activation_id: string
  user_id: string
  condition_type: ConditionType
  condition_params: Record<string, unknown>
  agent_prompt: string
  cooldown_seconds: number
  last_fired_at: string | null
  status: TriggerStatus
  priority: number
  default_api_key_id: string | null
  expires_at: string | null
  created_at: string
  created_by: string
  updated_at: string
  mode: TriggerInvocationMode
}

/**
 * Request body for `POST /activations/{id}/triggers`.
 *
 * Per Phase F design Q3, `status` is not in the create payload — new
 * triggers always start `ACTIVE` on the backend. The `condition_params`
 * shape depends on `condition_type` (use the discriminated `*ConditionParams`
 * helpers above when constructing).
 */
export interface CreateTriggerRequest {
  condition_type: ConditionType
  condition_params: Record<string, unknown>
  agent_prompt: string
  cooldown_seconds?: number
  priority?: number
  default_api_key_id?: string | null
  expires_at?: string | null
  /**
   * Invocation mode (Phase J — Task #213). Defaults to `direct` on the
   * backend. Set to `queue` to opt into Pattern B (URGENT
   * ExplorationTask filing for an out-of-band desktop agent to claim).
   */
  mode?: TriggerInvocationMode
}

/**
 * Request body for `PATCH /triggers/{id}`. All fields optional; only the
 * supplied ones are mutated. Per Phase F design Q3, `status` accepts only
 * `ACTIVE` (resume) or `PAUSED` (pause).
 */
export interface UpdateTriggerRequest {
  agent_prompt?: string
  cooldown_seconds?: number
  priority?: number
  condition_params?: Record<string, unknown>
  status?: 'ACTIVE' | 'PAUSED'
  /**
   * Optional invocation-mode update (Phase J — Task #213). Switching from
   * `direct` to `queue` (or back) takes effect on the next fire.
   */
  mode?: TriggerInvocationMode
}

/**
 * Wire shape for a `TriggerFireRecord` row.
 *
 * Mirrors `TriggerFireResponse` in
 * `backend/src/zebu/adapters/inbound/api/schemas/triggers.py`.
 *
 * `agent_response_raw` is truncated to 8000 chars server-side; the full
 * body lives in observability. `condition_evaluation_data` is per-condition
 * (see Phase F design §1.5).
 */
export interface TriggerFireResponse {
  id: string
  trigger_id: string
  activation_id: string
  fired_at: string
  condition_evaluation_data: Record<string, unknown>
  agent_invocation_id: string | null
  agent_response: AgentDecision
  agent_response_raw: string
  resulting_trade_id: string | null
  resulting_modify_payload: Record<string, unknown> | null
  resulting_exploration_task_id: string | null
  latency_ms: number
  api_key_id_used: string
}

/** Pagination params for trigger fire log + trigger list endpoints. */
export interface ListTriggerParams {
  limit?: number
  offset?: number
}

/**
 * Response from `POST /triggers/disable-all` and its admin twin.
 *
 * Mirrors `DisableAllResponse` in
 * `backend/src/zebu/adapters/inbound/api/schemas/triggers.py`.
 */
export interface DisableAllResponse {
  disabled_count: number
}
