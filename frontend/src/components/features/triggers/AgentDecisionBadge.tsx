/**
 * AgentDecisionBadge — small UI element rendering an `AgentDecision`.
 *
 * Editorial palette (matches the Phase F task spec for the fire log):
 *
 * - BUY               → text-gain
 * - SELL              → text-loss
 * - HOLD              → text-ink-subtle
 * - MODIFY            → text-amber (accent — a parameter change is notable)
 * - NEEDS_HUMAN       → bg-amber-soft amber pill — an exploration task was filed
 * - INVOCATION_FAILED → bg-loss-soft loss pill — system-recorded failure
 *
 * The wrapper element carries `data-testid="agent-decision-{decision}"` so
 * tests can assert state without scraping classnames.
 */
import { cn } from '@/lib/utils'
import type { AgentDecision } from '@/services/api/types'

const DECISION_LABELS: Record<AgentDecision, string> = {
  BUY: 'Buy',
  SELL: 'Sell',
  HOLD: 'Hold',
  MODIFY: 'Modify',
  NEEDS_HUMAN: 'Needs human',
  INVOCATION_FAILED: 'Invocation failed',
}

const DECISION_STYLES: Record<AgentDecision, string> = {
  BUY: 'text-gain',
  SELL: 'text-loss',
  HOLD: 'text-ink-subtle',
  MODIFY: 'text-amber',
  NEEDS_HUMAN: 'bg-amber-soft text-amber px-2 py-1 rounded-editorial',
  INVOCATION_FAILED: 'bg-loss-soft text-loss px-2 py-1 rounded-editorial',
}

interface AgentDecisionBadgeProps {
  decision: AgentDecision
  className?: string
}

export function AgentDecisionBadge({
  decision,
  className,
}: AgentDecisionBadgeProps): React.JSX.Element {
  const label = DECISION_LABELS[decision]
  return (
    <span
      data-testid={`agent-decision-${decision}`}
      role="status"
      aria-label={`Agent decision: ${label}`}
      className={cn(
        'inline-flex items-center font-eyebrow',
        DECISION_STYLES[decision],
        className
      )}
    >
      {label}
    </span>
  )
}
