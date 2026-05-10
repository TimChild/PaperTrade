/**
 * TriggerStatusBadge — small UI element rendering a `TriggerStatus`.
 *
 * Editorial palette (matches the Phase F task spec):
 *
 * - ACTIVE             → muted gain (`bg-gain-soft`)
 * - PAUSED             → ink-subtle (the trigger is dormant but not terminal)
 * - MANUALLY_DISABLED  → muted loss (`bg-loss-soft`) — kill switch fingerprint
 * - EXPIRED            → ink-faint — terminal, low emphasis
 *
 * The wrapper element carries `data-testid="trigger-status-{status}"` so
 * tests can assert state without scraping classnames.
 */
import { cn } from '@/lib/utils'
import type { TriggerStatus } from '@/services/api/types'

const STATUS_LABELS: Record<TriggerStatus, string> = {
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  EXPIRED: 'Expired',
  MANUALLY_DISABLED: 'Disabled',
}

const STATUS_STYLES: Record<TriggerStatus, string> = {
  ACTIVE: 'bg-gain-soft text-gain',
  PAUSED: 'bg-canvas-raised text-ink-subtle border border-hairline',
  EXPIRED: 'bg-canvas-raised text-ink-faint border border-hairline',
  MANUALLY_DISABLED: 'bg-loss-soft text-loss',
}

interface TriggerStatusBadgeProps {
  status: TriggerStatus
  className?: string
}

export function TriggerStatusBadge({
  status,
  className,
}: TriggerStatusBadgeProps): React.JSX.Element {
  const label = STATUS_LABELS[status]
  return (
    <span
      data-testid={`trigger-status-${status}`}
      role="status"
      aria-label={`Trigger status: ${label}`}
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
