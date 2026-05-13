/**
 * "Ask an agent" CTA (Phase G-2.3).
 *
 * Renders a small amber-outlined button that opens a dialog hosting
 * `CreateExplorationTaskForm` pre-filled with whatever context the host
 * page can supply (portfolio id from the portfolio detail page; tickers
 * from the strategy detail page).
 *
 * The button is intentionally a **secondary** CTA — it sits alongside the
 * page's primary actions, never replacing them. Editorial outline +
 * amber-on-hover styling matches the "Analytics" pill in PortfolioDetail.
 *
 * After submit the dialog closes, a toast surfaces with a link to the new
 * task, and the parent is notified via the optional `onSubmitted`
 * callback so it can re-seed any cached state.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Dialog } from '@/components/ui/Dialog'
import {
  CreateExplorationTaskForm,
  type CreateExplorationTaskFormInitialValues,
} from './CreateExplorationTaskForm'
import type { ExplorationTaskResponse } from '@/services/api/types'

interface AskAnAgentButtonProps {
  /**
   * Triggering surface — `portfolio` or `strategy` — affects the dialog
   * eyebrow / heading wording and the data-testid for E2E tests.
   */
  triggerContext: 'portfolio' | 'strategy'
  /** Optional pre-filled target portfolio id. */
  initialPortfolioId?: string
  /** Optional pre-filled tickers list. */
  initialTickers?: string[]
  /** Optional handler called after a successful submit. */
  onSubmitted?: (task: ExplorationTaskResponse) => void
  /** Optional data-testid override; defaults to context-specific value. */
  'data-testid'?: string
}

export function AskAnAgentButton({
  triggerContext,
  initialPortfolioId,
  initialTickers,
  onSubmitted,
  'data-testid': dataTestId,
}: AskAnAgentButtonProps): React.JSX.Element {
  const [isOpen, setIsOpen] = useState(false)

  // We close the dialog imperatively, then key-bump the form so a re-open
  // remounts it cleanly — preserving the initialValues semantics.
  const [formKey, setFormKey] = useState(0)

  const buttonTestId =
    dataTestId ??
    (triggerContext === 'portfolio'
      ? 'ask-an-agent-portfolio-btn'
      : 'ask-an-agent-strategy-btn')

  const dialogTestId = `ask-an-agent-dialog-${triggerContext}`

  const initialValues: CreateExplorationTaskFormInitialValues = {}
  if (initialPortfolioId !== undefined) {
    initialValues.targetPortfolioId = initialPortfolioId
  }
  if (initialTickers !== undefined && initialTickers.length > 0) {
    initialValues.tickers = initialTickers
  }

  const handleSubmitted = (created: ExplorationTaskResponse): void => {
    // Render the toast with a link to the new task. react-hot-toast's
    // success() takes either a string or a JSX node; we use a node so the
    // anchor stays styleable.
    toast.success(
      (t) => (
        <span className="flex items-center gap-2 text-body-sm text-ink">
          Exploration task queued ·{' '}
          <Link
            to={`/exploration-tasks/${created.id}`}
            onClick={() => toast.dismiss(t.id)}
            className="text-amber underline-offset-4 hover:underline"
            data-testid={`ask-an-agent-toast-link-${triggerContext}`}
          >
            View task
          </Link>
        </span>
      ),
      { duration: 7000 }
    )

    // Close + force a remount so the form's state is fresh next time.
    setIsOpen(false)
    setFormKey((k) => k + 1)
    onSubmitted?.(created)
  }

  const handleClose = (): void => {
    setIsOpen(false)
    // Reset the form state on close so re-opening the dialog gives a
    // fresh, freshly-seeded form rather than the user's half-typed
    // prompt from last time.
    setFormKey((k) => k + 1)
  }

  return (
    <>
      <button
        type="button"
        data-testid={buttonTestId}
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-1.5 border border-amber/60 rounded-editorial px-3 py-2 font-eyebrow text-amber hover:border-amber hover:bg-amber-soft/40 transition-colors duration-quick ease-editorial"
        style={{ minHeight: 'auto' }}
      >
        Ask an agent
      </button>
      {/* Dialog now conditionally renders its children based on isOpen
          (refactored from the ad-hoc workaround applied in PR #267), so
          we just pass isOpen through — no host-side gating needed. */}
      <Dialog
        isOpen={isOpen}
        onClose={handleClose}
        // Hide the built-in dialog header — the form panel renders its
        // own editorial header (eyebrow + display heading).
        className="max-w-2xl w-[92vw] p-0"
      >
        <div data-testid={dialogTestId}>
          <CreateExplorationTaskForm
            key={formKey}
            onCancel={handleClose}
            initialValues={initialValues}
            onSubmitted={handleSubmitted}
          />
        </div>
      </Dialog>
    </>
  )
}
