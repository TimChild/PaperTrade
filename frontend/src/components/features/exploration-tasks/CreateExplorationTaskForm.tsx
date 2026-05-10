/**
 * Editorial form for creating a new exploration task. Fits inside a flush
 * Panel and submits through the `useCreateExplorationTask` mutation. On
 * success the parent navigates to the new task's detail view (or, if a
 * custom `onSubmitted` handler is supplied, the parent owns the next-step
 * navigation).
 *
 * `initialValues` lets a parent seed any of the editable fields when
 * mounting the form (used by the G-2 "Ask an agent" buttons to pre-fill
 * `target_portfolio_id` from the portfolio detail page and `tickers` from
 * the strategy detail page). The form initialises state from those values
 * on mount — to update them after the form has rendered, parents should
 * remount the form via the `key` prop (no `useEffect`-to-sync).
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Panel } from '@/components/ui/Panel'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { useCreateExplorationTask } from '@/hooks/useExplorationTasks'
import { usePortfolios } from '@/hooks/usePortfolio'
import type {
  CreateExplorationTaskRequest,
  ExplorationTaskResponse,
} from '@/services/api/types'

/**
 * Optional seed values for the form on mount. Each field is independently
 * optional so callers can supply only what they have context for (e.g. a
 * portfolio detail page seeds `targetPortfolioId`; a strategy detail page
 * seeds `tickers`).
 */
export interface CreateExplorationTaskFormInitialValues {
  title?: string
  prompt?: string
  /** Pre-selected target portfolio id. */
  targetPortfolioId?: string
  /** Pre-populated tickers (rendered as a comma-separated string in the input). */
  tickers?: string[]
  constraints?: string
}

interface CreateExplorationTaskFormProps {
  onCancel: () => void
  /**
   * Optional initial values for the form fields. Read once on mount.
   * To re-seed after mount, remount the form via the `key` prop.
   */
  initialValues?: CreateExplorationTaskFormInitialValues
  /**
   * Optional handler called instead of the default
   * "navigate to detail page" behaviour. Use for inline / dialog flows
   * where the parent wants to control the next step (close a dialog,
   * surface a toast, etc.).
   */
  onSubmitted?: (task: ExplorationTaskResponse) => void
}

const SELECT_CLASSES =
  'flex h-10 w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50'

const TEXTAREA_CLASSES =
  'flex w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink transition-colors duration-quick ease-editorial focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-ink-subtle resize-y min-h-[140px]'

export function CreateExplorationTaskForm({
  onCancel,
  initialValues,
  onSubmitted,
}: CreateExplorationTaskFormProps): React.JSX.Element {
  const navigate = useNavigate()
  // Initialise state from `initialValues` exactly once on mount — see the
  // module-level JSDoc for the key-prop pattern parents should use to
  // re-seed.
  const [title, setTitle] = useState(initialValues?.title ?? '')
  const [prompt, setPrompt] = useState(initialValues?.prompt ?? '')
  const [tickersInput, setTickersInput] = useState(
    initialValues?.tickers && initialValues.tickers.length > 0
      ? initialValues.tickers.join(', ')
      : ''
  )
  const [targetPortfolioId, setTargetPortfolioId] = useState(
    initialValues?.targetPortfolioId ?? ''
  )
  const [constraints, setConstraints] = useState(
    initialValues?.constraints ?? ''
  )
  const [errors, setErrors] = useState<Record<string, string>>({})

  const createTask = useCreateExplorationTask()
  const { data: portfoliosPage } = usePortfolios()
  const portfolios = portfoliosPage?.items ?? []

  const tickers = tickersInput
    .split(',')
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean)

  const validate = (): boolean => {
    const next: Record<string, string> = {}
    if (!prompt.trim()) {
      next.prompt =
        'Prompt is required — describe what the agent should investigate.'
    } else if (prompt.length > 4000) {
      next.prompt = `Prompt must be at most 4000 characters (currently ${prompt.length}).`
    }
    if (tickers.length > 50) {
      next.tickers = `Tickers must be at most 50 entries (currently ${tickers.length}).`
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!validate()) return

    // Build the request: title is folded into the prompt as a leading line
    // (the backend has no separate `title` column — every visible "title"
    // in the UI is derived from the prompt's first line). Optional fields
    // are omitted when empty so the entity sees `None` rather than `""`.
    const composedPrompt = title.trim()
      ? `${title.trim()}\n\n${prompt.trim()}`
      : prompt.trim()

    const trimmedConstraints = constraints.trim()
    const payload: CreateExplorationTaskRequest = {
      prompt: composedPrompt,
    }
    if (targetPortfolioId) {
      payload.target_portfolio_id = targetPortfolioId
    }
    if (tickers.length > 0) {
      payload.tickers = tickers
    }
    if (trimmedConstraints) {
      // Free-form text constraint: the structured `constraints` payload
      // (max_backtests, allow_live_activation, strategy_type_whitelist)
      // doesn't fit a single textarea cleanly, so the human note is folded
      // into the prompt as an additional paragraph instead. The structured
      // form fields are deferred to a later iteration once we see real
      // usage patterns.
      payload.prompt = `${payload.prompt}\n\nConstraints: ${trimmedConstraints}`
    }

    createTask.mutate(payload, {
      onSuccess: (created) => {
        if (onSubmitted) {
          // Parent owns the post-submit flow (e.g. close dialog +
          // its own toast).
          onSubmitted(created)
        } else {
          toast.success('Exploration task created')
          void navigate(`/exploration-tasks/${created.id}`)
        }
      },
      onError: () => {
        toast.error('Failed to create exploration task')
      },
    })
  }

  return (
    <Panel>
      <header className="mb-5">
        <Eyebrow>New task</Eyebrow>
        <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
          Queue a task for an agent
        </h2>
        <p className="mt-2 text-body-sm text-ink-muted max-w-prose">
          Describe what you want investigated. Any agent on the platform may
          claim this task and submit findings against it.
        </p>
      </header>
      <form
        onSubmit={handleSubmit}
        data-testid="exploration-task-create-form"
        className="space-y-4"
      >
        {/* Title (optional, folded into the prompt) */}
        <div className="space-y-1.5">
          <Label htmlFor="exploration-task-title">
            Title{' '}
            <span className="text-ink-subtle font-tabular normal-case tracking-normal">
              (optional, surfaces as the headline)
            </span>
          </Label>
          <Input
            id="exploration-task-title"
            data-testid="exploration-task-create-title-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Mean-reversion on AAPL/MSFT this quarter"
          />
        </div>

        {/* Prompt — primary input */}
        <div className="space-y-1.5">
          <Label htmlFor="exploration-task-prompt">Prompt</Label>
          <textarea
            id="exploration-task-prompt"
            data-testid="exploration-task-create-prompt-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Explore mean-reversion strategies on AAPL and MSFT, focusing on the last quarter. Watch for FOMC reactions and report back with the strongest variant."
            className={TEXTAREA_CLASSES}
            rows={6}
          />
          {errors.prompt && (
            <p
              className="text-body-sm text-loss"
              data-testid="exploration-task-create-prompt-error"
            >
              {errors.prompt}
            </p>
          )}
        </div>

        {/* Target portfolio */}
        <div className="space-y-1.5">
          <Label htmlFor="exploration-task-portfolio">
            Target portfolio{' '}
            <span className="text-ink-subtle font-tabular normal-case tracking-normal">
              (optional)
            </span>
          </Label>
          <select
            id="exploration-task-portfolio"
            data-testid="exploration-task-create-portfolio-select"
            value={targetPortfolioId}
            onChange={(e) => setTargetPortfolioId(e.target.value)}
            className={SELECT_CLASSES}
          >
            <option value="">No specific portfolio</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Tickers */}
        <div className="space-y-1.5">
          <Label htmlFor="exploration-task-tickers">
            Tickers{' '}
            <span className="text-ink-subtle font-tabular normal-case tracking-normal">
              (optional, comma-separated)
            </span>
          </Label>
          <Input
            id="exploration-task-tickers"
            data-testid="exploration-task-create-tickers-input"
            value={tickersInput}
            onChange={(e) => setTickersInput(e.target.value)}
            placeholder="AAPL, MSFT, GOOG"
          />
          {errors.tickers && (
            <p
              className="text-body-sm text-loss"
              data-testid="exploration-task-create-tickers-error"
            >
              {errors.tickers}
            </p>
          )}
          {tickers.length > 0 && (
            <div
              className="mt-2 flex flex-wrap gap-1.5"
              data-testid="exploration-task-create-tickers-chips"
            >
              {tickers.map((t) => (
                <span
                  key={t}
                  className="rounded-editorial bg-canvas-sunken border border-hairline px-2 py-0.5 font-tabular text-body-sm text-ink"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Constraints (free-form) */}
        <div className="space-y-1.5">
          <Label htmlFor="exploration-task-constraints">
            Constraints{' '}
            <span className="text-ink-subtle font-tabular normal-case tracking-normal">
              (optional, free-form)
            </span>
          </Label>
          <textarea
            id="exploration-task-constraints"
            data-testid="exploration-task-create-constraints-input"
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
            placeholder="No live activation. Cap at 5 backtests. Stick to MOVING_AVERAGE_CROSSOVER."
            className={TEXTAREA_CLASSES}
            rows={3}
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            data-testid="exploration-task-create-cancel-btn"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            data-testid="exploration-task-create-submit-btn"
            disabled={createTask.isPending}
          >
            {createTask.isPending ? 'Creating...' : 'Queue task'}
          </Button>
        </div>
      </form>
    </Panel>
  )
}
