/**
 * ActivationStatusBadge — small UI element rendering an ActivationStatus.
 *
 * Editorial palette:
 *
 * - ACTIVE  → muted gain
 * - PAUSED  → amber soft (in-flight, action required)
 * - STOPPED → ink-faint (terminal, low emphasis)
 * - ERROR   → muted loss
 *
 * The wrapper element carries `data-testid="activation-status-{status}"` so
 * tests can assert state without scraping classnames.
 */
import { cn } from '@/lib/utils'
import type { ActivationStatus } from '@/services/api/types'

const STATUS_LABELS: Record<ActivationStatus, string> = {
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  STOPPED: 'Stopped',
  ERROR: 'Error',
}

const STATUS_STYLES: Record<ActivationStatus, string> = {
  ACTIVE: 'bg-gain-soft text-gain',
  PAUSED: 'bg-amber-soft text-amber',
  STOPPED: 'bg-canvas-raised text-ink-subtle border border-hairline',
  ERROR: 'bg-loss-soft text-loss',
}

interface ActivationStatusBadgeProps {
  status: ActivationStatus
  className?: string
}

export function ActivationStatusBadge({
  status,
  className,
}: ActivationStatusBadgeProps): React.JSX.Element {
  const label = STATUS_LABELS[status]
  return (
    <span
      data-testid={`activation-status-${status}`}
      role="status"
      aria-label={`Activation status: ${label}`}
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
