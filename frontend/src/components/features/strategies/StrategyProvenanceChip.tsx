/**
 * Strategy provenance eyebrow chip (Phase G-2.1).
 *
 * Small editorial label that surfaces "Authored by <agent-label>" beneath
 * an agent-authored strategy's name. Renders nothing for human-authored
 * strategies (the human-authored case is the default — no chip means "you
 * created this") and nothing while the underlying provenance query is
 * still loading.
 *
 * The chip is intentionally quiet — it's a footnote, not a primary
 * affordance — so we use `font-eyebrow` + `text-amber` and avoid borders,
 * backgrounds, or icons. Clicking the chip is a future enhancement (would
 * drill into the activity feed for the actor); for G-2 it's read-only.
 */
import { Link } from 'react-router-dom'
import { useStrategyProvenance } from '@/hooks/useStrategyProvenance'

interface StrategyProvenanceChipProps {
  strategyId: string
  /** Optional CSS class applied to the outer span. */
  className?: string
}

/**
 * Eyebrow chip rendered below an agent-authored strategy's name.
 *
 * Returns `null` for human-authored / unknown / loading cases so callers
 * can compose it inside a header without conditional wrapping.
 */
export function StrategyProvenanceChip({
  strategyId,
  className,
}: StrategyProvenanceChipProps): React.JSX.Element | null {
  const { authorKind, agentLabel } = useStrategyProvenance(strategyId)

  if (authorKind !== 'agent') {
    return null
  }

  const label = agentLabel ?? 'an agent'
  const baseClasses = 'font-eyebrow text-amber inline-flex items-baseline gap-1'
  const composedClass = className ? `${baseClasses} ${className}` : baseClasses
  return (
    <span
      className={composedClass}
      data-testid={`strategy-provenance-${strategyId}`}
    >
      <span className="text-ink-muted">Authored by</span>
      {agentLabel !== null ? (
        <Link
          to={`/activity?actor_label=${encodeURIComponent(agentLabel)}`}
          data-testid={`strategy-provenance-actor-link-${strategyId}`}
          className="text-amber hover:underline underline-offset-4"
        >
          {label}
        </Link>
      ) : (
        <span>{label}</span>
      )}
    </span>
  )
}
