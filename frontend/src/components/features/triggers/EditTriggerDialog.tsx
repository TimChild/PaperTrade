/**
 * EditTriggerDialog — small inline edit modal for an existing trigger.
 *
 * Restricts itself to the fields that change shape across day-to-day tuning:
 * cooldown + agent prompt. The condition type and params are intentionally
 * out of scope (they're heavyweight enough that "delete and recreate" is the
 * cleaner UX). Status changes use a separate one-click pause/resume button.
 *
 * Initial values are passed in via props; the dialog initialises its local
 * form state from them once on mount. We use the `key={trigger.id}` pattern
 * at the call site so each open of the dialog for a different trigger
 * starts with a fresh, correctly-seeded form — avoids the useEffect-to-sync
 * anti-pattern from the frontend conventions doc.
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { useUpdateTrigger } from '@/hooks/useTriggers'
import type {
  TriggerInvocationMode,
  TriggerResponse,
} from '@/services/api/types'

const SELECT_CLASSES =
  'flex h-10 w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50'

const TEXTAREA_CLASSES =
  'flex w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink transition-colors duration-quick ease-editorial focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-ink-subtle resize-y min-h-[110px]'

type CooldownUnit = 'minutes' | 'hours' | 'days'

const UNIT_SECONDS: Record<CooldownUnit, number> = {
  minutes: 60,
  hours: 3600,
  days: 86_400,
}

interface EditTriggerDialogProps {
  trigger: TriggerResponse
  onClose: () => void
  onSuccess?: () => void
}

/**
 * Decompose a seconds count into the most natural (value, unit) pair so the
 * edit dialog opens with a glanceable representation of the current cooldown
 * (e.g. 21600s → "6 hours" rather than "21600 seconds").
 */
function decomposeCooldown(seconds: number): {
  value: string
  unit: CooldownUnit
} {
  if (seconds === 0) return { value: '0', unit: 'minutes' }
  if (seconds % UNIT_SECONDS.days === 0) {
    return { value: String(seconds / UNIT_SECONDS.days), unit: 'days' }
  }
  if (seconds % UNIT_SECONDS.hours === 0) {
    return { value: String(seconds / UNIT_SECONDS.hours), unit: 'hours' }
  }
  return {
    value: String(Math.round(seconds / UNIT_SECONDS.minutes)),
    unit: 'minutes',
  }
}

export function EditTriggerDialog({
  trigger,
  onClose,
  onSuccess,
}: EditTriggerDialogProps): React.JSX.Element {
  const initialCooldown = decomposeCooldown(trigger.cooldown_seconds)
  // Initialize once on mount via the `key`-prop pattern at the call site —
  // no useEffect to sync props to state.
  const [cooldownValue, setCooldownValue] = useState<string>(
    initialCooldown.value
  )
  const [cooldownUnit, setCooldownUnit] = useState<CooldownUnit>(
    initialCooldown.unit
  )
  const [agentPrompt, setAgentPrompt] = useState<string>(trigger.agent_prompt)
  // Invocation mode (Phase J / Task #213). Seeded from the persisted
  // value so the form opens reflecting the current backend state.
  const [mode, setMode] = useState<TriggerInvocationMode>(trigger.mode)
  const [errors, setErrors] = useState<{
    cooldown?: string
    agent_prompt?: string
  }>({})

  const updateTrigger = useUpdateTrigger()

  const validate = (): boolean => {
    const next: typeof errors = {}
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
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!validate()) return

    const cooldownSeconds = Number(cooldownValue) * UNIT_SECONDS[cooldownUnit]

    updateTrigger.mutate(
      {
        triggerId: trigger.id,
        body: {
          agent_prompt: agentPrompt.trim(),
          cooldown_seconds: cooldownSeconds,
          mode,
        },
      },
      {
        onSuccess: () => {
          toast.success('Trigger updated')
          onSuccess?.()
          onClose()
        },
        onError: () => {
          toast.error('Failed to update trigger')
        },
      }
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-canvas-sunken/80 backdrop-blur-sm overflow-y-auto py-8"
      data-testid={`trigger-edit-dialog-backdrop-${trigger.id}`}
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !updateTrigger.isPending) onClose()
      }}
    >
      <div
        className="mx-4 w-full max-w-lg rounded-editorial border border-hairline bg-canvas-raised p-6 shadow-elevated"
        data-testid={`trigger-edit-dialog-${trigger.id}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="trigger-edit-dialog-title"
      >
        <Eyebrow>Edit</Eyebrow>
        <h3
          id="trigger-edit-dialog-title"
          className="mt-1.5 font-display text-display-sm tracking-tight text-ink"
        >
          Edit trigger
        </h3>
        <p className="mt-2 text-body-sm text-ink-muted">
          Tune the cooldown and the prompt the agent receives on fire. The
          condition itself is immutable — delete and recreate the trigger to
          change condition type or params.
        </p>

        <form
          onSubmit={handleSubmit}
          data-testid={`trigger-edit-form-${trigger.id}`}
          className="mt-5 space-y-4"
        >
          {/* Cooldown */}
          <div className="space-y-1.5">
            <Label htmlFor={`trigger-edit-cooldown-value-${trigger.id}`}>
              Cooldown
            </Label>
            <div className="flex gap-2">
              <Input
                id={`trigger-edit-cooldown-value-${trigger.id}`}
                data-testid={`trigger-edit-cooldown-value-${trigger.id}`}
                type="number"
                min="0"
                step="1"
                value={cooldownValue}
                onChange={(e) => setCooldownValue(e.target.value)}
                className="w-24"
              />
              <select
                data-testid={`trigger-edit-cooldown-unit-${trigger.id}`}
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
                data-testid={`trigger-edit-cooldown-error-${trigger.id}`}
              >
                {errors.cooldown}
              </p>
            )}
          </div>

          {/* Agent prompt */}
          <div className="space-y-1.5">
            <Label htmlFor={`trigger-edit-agent-prompt-${trigger.id}`}>
              Agent prompt
            </Label>
            <textarea
              id={`trigger-edit-agent-prompt-${trigger.id}`}
              data-testid={`trigger-edit-agent-prompt-${trigger.id}`}
              value={agentPrompt}
              onChange={(e) => setAgentPrompt(e.target.value)}
              className={TEXTAREA_CLASSES}
              rows={5}
            />
            {errors.agent_prompt && (
              <p
                className="text-body-sm text-loss"
                data-testid={`trigger-edit-agent-prompt-error-${trigger.id}`}
              >
                {errors.agent_prompt}
              </p>
            )}
          </div>

          {/* Invocation mode (Phase J / Task #213) */}
          <div
            className="space-y-1.5"
            data-testid={`trigger-edit-mode-group-${trigger.id}`}
            role="radiogroup"
            aria-labelledby={`trigger-edit-mode-eyebrow-${trigger.id}`}
          >
            <Eyebrow id={`trigger-edit-mode-eyebrow-${trigger.id}`}>
              Invocation mode
            </Eyebrow>
            <div className="flex flex-col gap-2">
              <label className="flex items-start gap-2 text-body-sm text-ink">
                <input
                  type="radio"
                  name={`trigger-edit-mode-${trigger.id}`}
                  data-testid={`trigger-edit-mode-direct-${trigger.id}`}
                  value="direct"
                  checked={mode === 'direct'}
                  onChange={() => setMode('direct')}
                  className="mt-1 accent-amber"
                />
                <span>
                  <span className="block font-medium text-ink">
                    Direct (Anthropic Haiku)
                  </span>
                  <span className="block text-body-sm text-ink-muted">
                    Default. The platform invokes the agent inline.
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-body-sm text-ink">
                <input
                  type="radio"
                  name={`trigger-edit-mode-${trigger.id}`}
                  data-testid={`trigger-edit-mode-queue-${trigger.id}`}
                  value="queue"
                  checked={mode === 'queue'}
                  onChange={() => setMode('queue')}
                  className="mt-1 accent-amber"
                />
                <span>
                  <span className="block font-medium text-ink">
                    Queue (Desktop Claude / Gemini CLI)
                  </span>
                  <span className="block text-body-sm text-ink-muted">
                    Files an URGENT task. Your desktop agent polls and processes
                    it.
                  </span>
                </span>
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={updateTrigger.isPending}
              data-testid={`trigger-edit-cancel-btn-${trigger.id}`}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid={`trigger-edit-submit-btn-${trigger.id}`}
              disabled={updateTrigger.isPending}
            >
              {updateTrigger.isPending ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
