/**
 * ExplorationTaskStatusBadge — status pill for an exploration task.
 *
 * Editorial palette (matches the convention from `ActivationStatusBadge`):
 *
 * - DONE        → muted gain      (terminal success)
 * - IN_PROGRESS → amber soft      (in-flight, claimed by an agent)
 * - OPEN        → ink-subtle      (claimable, low emphasis)
 * - ABANDONED   → muted loss      (terminal failure / cancellation)
 *
 * The wrapper carries `data-testid="exploration-task-status-{status}"` so
 * tests can assert state without scraping classnames.
 */
import { cn } from '@/lib/utils'
import type { ExplorationTaskStatus } from '@/services/api/types'

const STATUS_LABELS: Record<ExplorationTaskStatus, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'Claimed',
  DONE: 'Done',
  ABANDONED: 'Abandoned',
}

const STATUS_STYLES: Record<ExplorationTaskStatus, string> = {
  DONE: 'bg-gain-soft text-gain',
  IN_PROGRESS: 'bg-amber-soft text-amber',
  OPEN: 'bg-canvas-raised text-ink-subtle border border-hairline',
  ABANDONED: 'bg-loss-soft text-loss',
}

interface ExplorationTaskStatusBadgeProps {
  status: ExplorationTaskStatus
  className?: string
}

export function ExplorationTaskStatusBadge({
  status,
  className,
}: ExplorationTaskStatusBadgeProps): React.JSX.Element {
  const label = STATUS_LABELS[status]
  return (
    <span
      data-testid={`exploration-task-status-${status}`}
      role="status"
      aria-label={`Exploration task status: ${label}`}
      className={cn(
        'inline-flex items-center font-eyebrow rounded-editorial px-2 py-1',
        STATUS_STYLES[status],
        className
      )}
    >
      {label}
    </span>
  )
}
