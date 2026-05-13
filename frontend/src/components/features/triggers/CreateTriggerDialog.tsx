/**
 * CreateTriggerDialog — modal that attaches a new trigger to an activation.
 *
 * Layout: condition-type select drives a dynamic params section. Cooldown
 * uses a number-plus-unit pair (the wire field is `cooldown_seconds`; the
 * dialog composes from `value × unit` to keep the UX glanceable). The
 * default-API-key select only renders when the user has more than one
 * trade-scoped key.
 *
 * Renders inside the existing app shell as a fixed overlay (matching the
 * pattern used by `ActivateStrategyDialog` and `ConfirmDialog`). The native
 * `<Dialog>` element triggers showModal() which JSDOM doesn't polyfill, so
 * the fixed-overlay pattern keeps unit tests light.
 *
 * Per Phase F Q1, the `CUSTOM_RULE` condition type is intentionally surfaced
 * as a disabled option with an explanatory tooltip — the backend would
 * reject it at construction time anyway.
 */
import { useState, useMemo } from 'react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { useCreateTrigger } from '@/hooks/useTriggers'
import { useApiKeys } from '@/hooks/useApiKeys'
import type {
  ApiKeySummary,
  ConditionType,
  CreateTriggerRequest,
  DrawdownMetric,
} from '@/services/api/types'

const SELECT_CLASSES =
  'flex h-10 w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50'

const TEXTAREA_CLASSES =
  'flex w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink transition-colors duration-quick ease-editorial focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-ink-subtle resize-y min-h-[110px]'

interface CreateTriggerDialogProps {
  isOpen: boolean
  activationId: string
  onClose: () => void
  onSuccess?: () => void
}

type CooldownUnit = 'minutes' | 'hours' | 'days'

const UNIT_SECONDS: Record<CooldownUnit, number> = {
  minutes: 60,
  hours: 3600,
  days: 86_400,
}

/**
 * Default operator-prompt placeholder. Matches the wording recommended in
 * the operating manual (§3.5.x) — when the agent is woken it will receive
 * the trigger's portfolio context plus this text verbatim.
 */
const PROMPT_PLACEHOLDER =
  "When this trigger fires, you'll be invoked with the portfolio context. Tell me what to look for and what action to recommend."

const CONDITION_OPTIONS: { value: ConditionType; label: string }[] = [
  { value: 'DRAWDOWN_THRESHOLD', label: 'Drawdown threshold' },
  { value: 'VOLATILITY_SPIKE', label: 'Volatility spike' },
  { value: 'EARNINGS_PROXIMITY', label: 'Earnings proximity' },
  // CUSTOM_RULE is rendered as a disabled option below.
]

interface FormErrors {
  agent_prompt?: string
  cooldown?: string
  threshold_pct?: string
  lookback_days?: string
  over_days?: string
  days_before?: string
}

/**
 * Pick the user's trade-scoped, non-revoked, non-expired API keys. The
 * default-API-key select only renders when the user has more than one of
 * these — a single key is the implicit default.
 */
function isUsableTradeKey(key: ApiKeySummary): boolean {
  if (!key.is_active) return false
  if (!key.scopes.includes('trade')) return false
  if (key.revoked_at !== null) return false
  if (key.expires_at !== null && new Date(key.expires_at) <= new Date()) {
    return false
  }
  return true
}

export function CreateTriggerDialog({
  isOpen,
  activationId,
  onClose,
  onSuccess,
}: CreateTriggerDialogProps): React.JSX.Element | null {
  const [conditionType, setConditionType] =
    useState<ConditionType>('DRAWDOWN_THRESHOLD')

  // Drawdown params
  const [thresholdPct, setThresholdPct] = useState<string>('5')
  const [lookbackDays, setLookbackDays] = useState<string>('3')
  const [metric, setMetric] = useState<DrawdownMetric>('PORTFOLIO_TOTAL')

  // Volatility params
  const [volThresholdPct, setVolThresholdPct] = useState<string>('30')
  const [overDays, setOverDays] = useState<string>('14')

  // Earnings params
  const [daysBefore, setDaysBefore] = useState<string>('3')

  // Common fields
  const [cooldownValue, setCooldownValue] = useState<string>('1')
  const [cooldownUnit, setCooldownUnit] = useState<CooldownUnit>('hours')
  const [agentPrompt, setAgentPrompt] = useState<string>('')
  const [defaultApiKeyId, setDefaultApiKeyId] = useState<string>('')
  const [errors, setErrors] = useState<FormErrors>({})

  const createTrigger = useCreateTrigger()
  const { data: apiKeysList } = useApiKeys()
  const usableKeys = useMemo(
    () => (apiKeysList?.items ?? []).filter(isUsableTradeKey),
    [apiKeysList]
  )
  // Only render the key picker when the user has more than one usable key.
  // With zero or one, the backend fallback rule (most-recently-used) handles
  // attribution implicitly.
  const showKeyPicker = usableKeys.length > 1

  if (!isOpen) return null

  const validate = (): boolean => {
    const next: FormErrors = {}
    const trimmedPrompt = agentPrompt.trim()
    if (!trimmedPrompt) {
      next.agent_prompt = 'Agent prompt is required.'
    } else if (trimmedPrompt.length > 4000) {
      next.agent_prompt = `Agent prompt must be at most 4000 characters (currently ${trimmedPrompt.length}).`
    }

    const cooldownNum = Number(cooldownValue)
    if (
      !cooldownValue.trim() ||
      !Number.isFinite(cooldownNum) ||
      cooldownNum < 0
    ) {
      next.cooldown = 'Cooldown must be a non-negative number.'
    }

    if (conditionType === 'DRAWDOWN_THRESHOLD') {
      const threshold = Number(thresholdPct)
      if (!Number.isFinite(threshold) || threshold <= 0 || threshold > 100) {
        next.threshold_pct = 'Threshold must be in (0, 100].'
      }
      const lookback = Number(lookbackDays)
      if (!Number.isInteger(lookback) || lookback < 1 || lookback > 365) {
        next.lookback_days = 'Lookback must be an integer in [1, 365].'
      }
    }

    if (conditionType === 'VOLATILITY_SPIKE') {
      const threshold = Number(volThresholdPct)
      if (!Number.isFinite(threshold) || threshold <= 0 || threshold > 500) {
        next.threshold_pct = 'Threshold must be in (0, 500].'
      }
      const over = Number(overDays)
      if (!Number.isInteger(over) || over < 5 || over > 90) {
        next.over_days = 'Window must be an integer in [5, 90].'
      }
    }

    if (conditionType === 'EARNINGS_PROXIMITY') {
      const days = Number(daysBefore)
      if (!Number.isInteger(days) || days < 1 || days > 14) {
        next.days_before = 'Days before must be an integer in [1, 14].'
      }
    }

    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!validate()) return

    // Translate cooldown to seconds before submitting.
    const cooldownSeconds = Number(cooldownValue) * UNIT_SECONDS[cooldownUnit]

    let conditionParams: Record<string, unknown>
    if (conditionType === 'DRAWDOWN_THRESHOLD') {
      conditionParams = {
        threshold_pct: thresholdPct,
        lookback_days: Number(lookbackDays),
        metric,
      }
    } else if (conditionType === 'VOLATILITY_SPIKE') {
      conditionParams = {
        threshold_pct: volThresholdPct,
        over_days: Number(overDays),
        tickers: null,
      }
    } else if (conditionType === 'EARNINGS_PROXIMITY') {
      conditionParams = {
        days_before: Number(daysBefore),
        tickers: null,
      }
    } else {
      // CUSTOM_RULE — should not be reachable from the UI (disabled option),
      // but kept for completeness so the path doesn't fall through silently.
      conditionParams = {}
    }

    const body: CreateTriggerRequest = {
      condition_type: conditionType,
      condition_params: conditionParams,
      agent_prompt: agentPrompt.trim(),
      cooldown_seconds: cooldownSeconds,
    }
    if (defaultApiKeyId) {
      body.default_api_key_id = defaultApiKeyId
    }

    createTrigger.mutate(
      { activationId, body },
      {
        onSuccess: () => {
          toast.success('Trigger attached')
          // Reset transient form state for the next open.
          setAgentPrompt('')
          setErrors({})
          onSuccess?.()
          onClose()
        },
        onError: () => {
          toast.error('Failed to attach trigger')
        },
      }
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-canvas-sunken/80 backdrop-blur-sm overflow-y-auto py-8"
      data-testid="trigger-create-dialog-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !createTrigger.isPending) onClose()
      }}
    >
      <div
        className="mx-4 w-full max-w-lg rounded-editorial border border-hairline bg-canvas-raised p-6 shadow-elevated"
        data-testid="trigger-create-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="trigger-create-dialog-title"
      >
        <Eyebrow>Attach trigger</Eyebrow>
        <h3
          id="trigger-create-dialog-title"
          className="mt-1.5 font-display text-display-sm tracking-tight text-ink"
        >
          New trigger
        </h3>
        <p className="mt-2 text-body-sm text-ink-muted">
          When the condition fires, the platform wakes an agent with your prompt
          and the activation&apos;s portfolio context. The agent returns a
          structured decision — BUY, SELL, HOLD, MODIFY, or NEEDS&nbsp;HUMAN —
          and the platform executes it (subject to daily caps).
        </p>

        <form
          onSubmit={handleSubmit}
          data-testid="trigger-create-form"
          className="mt-5 space-y-4"
        >
          {/* Condition type */}
          <div className="space-y-1.5">
            <Label htmlFor="trigger-create-condition-type">
              Condition type
            </Label>
            <select
              id="trigger-create-condition-type"
              data-testid="trigger-create-condition-type"
              value={conditionType}
              onChange={(e) =>
                setConditionType(e.target.value as ConditionType)
              }
              className={SELECT_CLASSES}
            >
              {CONDITION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
              <option
                value="CUSTOM_RULE"
                disabled
                title="Custom rules are deferred — a future release will add a constrained DSL."
              >
                Custom rule (coming soon)
              </option>
            </select>
          </div>

          {/* Dynamic params per condition type */}
          {conditionType === 'DRAWDOWN_THRESHOLD' && (
            <div
              className="grid grid-cols-2 gap-3"
              data-testid="trigger-create-drawdown-params"
            >
              <div className="space-y-1.5">
                <Label htmlFor="trigger-create-threshold-pct">
                  Threshold (%)
                </Label>
                <Input
                  id="trigger-create-threshold-pct"
                  data-testid="trigger-create-threshold-pct"
                  type="number"
                  min="0.01"
                  max="100"
                  // `step="any"` keeps HTML5 constraint validation from
                  // rejecting the default `5` (which violates a 0.01-anchored
                  // 0.1 step grid). Range + decimal validation lives in
                  // `validate()` and the domain VO — the step here is a UX
                  // nicety for keyboard nudging, not a hard contract.
                  step="any"
                  value={thresholdPct}
                  onChange={(e) => setThresholdPct(e.target.value)}
                />
                {errors.threshold_pct && (
                  <p
                    className="text-body-sm text-loss"
                    data-testid="trigger-create-threshold-pct-error"
                  >
                    {errors.threshold_pct}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="trigger-create-lookback-days">
                  Lookback (days)
                </Label>
                <Input
                  id="trigger-create-lookback-days"
                  data-testid="trigger-create-lookback-days"
                  type="number"
                  min="1"
                  max="365"
                  step="1"
                  value={lookbackDays}
                  onChange={(e) => setLookbackDays(e.target.value)}
                />
                {errors.lookback_days && (
                  <p
                    className="text-body-sm text-loss"
                    data-testid="trigger-create-lookback-days-error"
                  >
                    {errors.lookback_days}
                  </p>
                )}
              </div>
              <div
                className="col-span-2 space-y-1.5"
                data-testid="trigger-create-metric-group"
              >
                <Eyebrow>Metric</Eyebrow>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-body-sm text-ink">
                    <input
                      type="radio"
                      name="trigger-metric"
                      data-testid="trigger-create-metric-portfolio"
                      value="PORTFOLIO_TOTAL"
                      checked={metric === 'PORTFOLIO_TOTAL'}
                      onChange={() => setMetric('PORTFOLIO_TOTAL')}
                      className="accent-amber"
                    />
                    Portfolio
                  </label>
                  <label className="flex items-center gap-2 text-body-sm text-ink">
                    <input
                      type="radio"
                      name="trigger-metric"
                      data-testid="trigger-create-metric-per-ticker"
                      value="PER_TICKER"
                      checked={metric === 'PER_TICKER'}
                      onChange={() => setMetric('PER_TICKER')}
                      className="accent-amber"
                    />
                    Per ticker
                  </label>
                </div>
              </div>
            </div>
          )}

          {conditionType === 'VOLATILITY_SPIKE' && (
            <div
              className="grid grid-cols-2 gap-3"
              data-testid="trigger-create-volatility-params"
            >
              <div className="space-y-1.5">
                <Label htmlFor="trigger-create-vol-threshold-pct">
                  Threshold (%)
                </Label>
                <Input
                  id="trigger-create-vol-threshold-pct"
                  data-testid="trigger-create-vol-threshold-pct"
                  type="number"
                  min="0.01"
                  max="500"
                  // `step="any"` — same reason as the drawdown threshold
                  // above: the default value of `30` does not sit on a
                  // 0.01-anchored 0.5 step grid, so the browser-level
                  // constraint validator would block form submission
                  // before our `onSubmit` even ran.
                  step="any"
                  value={volThresholdPct}
                  onChange={(e) => setVolThresholdPct(e.target.value)}
                />
                {errors.threshold_pct && (
                  <p
                    className="text-body-sm text-loss"
                    data-testid="trigger-create-vol-threshold-pct-error"
                  >
                    {errors.threshold_pct}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="trigger-create-over-days">Window (days)</Label>
                <Input
                  id="trigger-create-over-days"
                  data-testid="trigger-create-over-days"
                  type="number"
                  min="5"
                  max="90"
                  step="1"
                  value={overDays}
                  onChange={(e) => setOverDays(e.target.value)}
                />
                {errors.over_days && (
                  <p
                    className="text-body-sm text-loss"
                    data-testid="trigger-create-over-days-error"
                  >
                    {errors.over_days}
                  </p>
                )}
              </div>
            </div>
          )}

          {conditionType === 'EARNINGS_PROXIMITY' && (
            <div
              className="space-y-1.5"
              data-testid="trigger-create-earnings-params"
            >
              <Label htmlFor="trigger-create-days-before">
                Days before earnings
              </Label>
              <Input
                id="trigger-create-days-before"
                data-testid="trigger-create-days-before"
                type="number"
                min="1"
                max="14"
                step="1"
                value={daysBefore}
                onChange={(e) => setDaysBefore(e.target.value)}
              />
              {errors.days_before && (
                <p
                  className="text-body-sm text-loss"
                  data-testid="trigger-create-days-before-error"
                >
                  {errors.days_before}
                </p>
              )}
            </div>
          )}

          {/* Cooldown */}
          <div className="space-y-1.5">
            <Label htmlFor="trigger-create-cooldown-value">
              Cooldown{' '}
              <span className="text-ink-subtle font-tabular normal-case tracking-normal">
                (minimum time between fires)
              </span>
            </Label>
            <div className="flex gap-2">
              <Input
                id="trigger-create-cooldown-value"
                data-testid="trigger-create-cooldown-value"
                type="number"
                min="0"
                step="1"
                value={cooldownValue}
                onChange={(e) => setCooldownValue(e.target.value)}
                className="w-24"
              />
              <select
                data-testid="trigger-create-cooldown-unit"
                value={cooldownUnit}
                onChange={(e) =>
                  setCooldownUnit(e.target.value as CooldownUnit)
                }
                className={SELECT_CLASSES}
                aria-label="Cooldown unit"
              >
                <option value="minutes">minutes</option>
                <option value="hours">hours</option>
                <option value="days">days</option>
              </select>
            </div>
            {errors.cooldown && (
              <p
                className="text-body-sm text-loss"
                data-testid="trigger-create-cooldown-error"
              >
                {errors.cooldown}
              </p>
            )}
          </div>

          {/* Agent prompt */}
          <div className="space-y-1.5">
            <Label htmlFor="trigger-create-agent-prompt">Agent prompt</Label>
            <textarea
              id="trigger-create-agent-prompt"
              data-testid="trigger-create-agent-prompt"
              value={agentPrompt}
              onChange={(e) => setAgentPrompt(e.target.value)}
              placeholder={PROMPT_PLACEHOLDER}
              className={TEXTAREA_CLASSES}
              rows={4}
            />
            {errors.agent_prompt && (
              <p
                className="text-body-sm text-loss"
                data-testid="trigger-create-agent-prompt-error"
              >
                {errors.agent_prompt}
              </p>
            )}
          </div>

          {/* Default API key picker — only when the user has multiple
              trade-scoped keys. With zero/one the backend fallback rule
              handles attribution implicitly. */}
          {showKeyPicker && (
            <div className="space-y-1.5">
              <Label htmlFor="trigger-create-default-api-key">
                Default API key{' '}
                <span
                  className="text-ink-subtle font-tabular normal-case tracking-normal"
                  title="The agent will trade against this portfolio using this key."
                >
                  (optional)
                </span>
              </Label>
              <select
                id="trigger-create-default-api-key"
                data-testid="trigger-create-default-api-key"
                value={defaultApiKeyId}
                onChange={(e) => setDefaultApiKeyId(e.target.value)}
                className={SELECT_CLASSES}
              >
                <option value="">
                  Auto (most-recently-used trade-scoped key)
                </option>
                {usableKeys.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              data-testid="trigger-create-cancel-btn"
              disabled={createTrigger.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="trigger-create-submit-btn"
              disabled={createTrigger.isPending}
            >
              {createTrigger.isPending ? 'Attaching...' : 'Attach trigger'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
