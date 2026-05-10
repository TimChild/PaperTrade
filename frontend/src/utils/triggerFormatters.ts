/**
 * Trigger-specific formatters (Phase G-1).
 *
 * Renders human-readable summaries for the wire-format condition params
 * (which are an opaque `Record<string, unknown>` on the server contract).
 * The summary strings are read across multiple surfaces — the trigger list
 * row, the fire-log header — so they live as standalone formatters with
 * unit-test coverage.
 */
import type {
  ConditionType,
  DrawdownConditionParams,
  EarningsConditionParams,
  TriggerFireResponse,
  VolatilityConditionParams,
} from '@/services/api/types'

/**
 * Format a `cooldown_seconds` value as a short human-readable label.
 *
 * Examples:
 *
 * - `0`     → `none`
 * - `300`   → `5m`
 * - `3600`  → `1h`
 * - `21600` → `6h`
 * - `86400` → `1d`
 *
 * Steps coarsen as the value grows; the goal is glanceability in a table
 * cell, not exact arithmetic. For exotic non-round values (e.g. 3650), the
 * function falls back to the next coarser unit with a leading whole part
 * (`1h 1m`).
 */
export function formatCooldown(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  if (seconds === 0) return 'none'

  if (seconds < 60) {
    return `${seconds}s`
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remSec = seconds % 60
    if (remSec === 0) return `${minutes}m`
    return `${minutes}m ${remSec}s`
  }
  if (seconds < 86_400) {
    const hours = Math.floor(seconds / 3600)
    const remMin = Math.floor((seconds % 3600) / 60)
    if (remMin === 0) return `${hours}h`
    return `${hours}h ${remMin}m`
  }
  const days = Math.floor(seconds / 86_400)
  const remHour = Math.floor((seconds % 86_400) / 3600)
  if (remHour === 0) return `${days}d`
  return `${days}d ${remHour}h`
}

/**
 * Format a discriminated trigger condition as a one-line summary.
 *
 * The summary lands in the trigger list row (`Condition` column) and on
 * the fire-log header. It's intentionally terse — full params live in the
 * edit dialog. Unknown / unexpected shapes degrade to the bare condition
 * type rather than throwing.
 */
export function formatConditionSummary(
  conditionType: ConditionType,
  params: Record<string, unknown>
): string {
  if (conditionType === 'DRAWDOWN_THRESHOLD') {
    const p = params as Partial<DrawdownConditionParams>
    const threshold = p.threshold_pct ?? '?'
    const lookback = p.lookback_days ?? '?'
    const metric = p.metric === 'PER_TICKER' ? 'per ticker' : 'portfolio'
    return `Drawdown > ${threshold}% over ${lookback}d (${metric})`
  }
  if (conditionType === 'VOLATILITY_SPIKE') {
    const p = params as Partial<VolatilityConditionParams>
    const threshold = p.threshold_pct ?? '?'
    const over = p.over_days ?? '?'
    const ticker =
      Array.isArray(p.tickers) && p.tickers.length > 0
        ? p.tickers.join(', ')
        : 'all tickers'
    return `Volatility > ${threshold}% over ${over}d (${ticker})`
  }
  if (conditionType === 'EARNINGS_PROXIMITY') {
    const p = params as Partial<EarningsConditionParams>
    const days = p.days_before ?? '?'
    const ticker =
      Array.isArray(p.tickers) && p.tickers.length > 0
        ? p.tickers.join(', ')
        : 'all tickers'
    return `Earnings within ${days}d (${ticker})`
  }
  if (conditionType === 'CUSTOM_RULE') {
    return 'Custom rule (unsupported)'
  }
  return conditionType
}

/**
 * Format the `condition_evaluation_data` snapshot a `TriggerFireRecord`
 * carries into a one-line label. Wire shape varies by condition type
 * (see Phase F design §1.5); we extract the most useful single fact and
 * fall back to the raw key list when the shape doesn't match expectations.
 */
export function formatFireSnapshot(fire: TriggerFireResponse): string {
  const data = fire.condition_evaluation_data
  // The snapshot doesn't carry the condition_type — we discover it from the
  // fields present. Order matters: each branch picks the most discriminating
  // field for that shape.
  if (typeof data.drawdown_pct === 'string') {
    const dd = data.drawdown_pct
    const ticker = typeof data.ticker === 'string' ? ` (${data.ticker})` : ''
    return `Drawdown ${dd}%${ticker}`
  }
  if (
    typeof data.realised_vol_pct === 'string' ||
    typeof data.realized_vol_pct === 'string'
  ) {
    const vol =
      typeof data.realised_vol_pct === 'string'
        ? data.realised_vol_pct
        : (data.realized_vol_pct as string)
    const ticker = typeof data.ticker === 'string' ? ` ${data.ticker}` : ''
    return `Volatility ${vol}%${ticker}`
  }
  if (typeof data.days_until === 'number') {
    const ticker = typeof data.ticker === 'string' ? `${data.ticker} ` : ''
    return `${ticker}earnings in ${data.days_until}d`
  }
  // Fallback — list the keys so the snapshot is at least scannable.
  const keys = Object.keys(data).slice(0, 3)
  return keys.length > 0 ? keys.join(', ') : '—'
}
