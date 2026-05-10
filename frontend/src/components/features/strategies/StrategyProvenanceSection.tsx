/**
 * Strategy provenance detail section (Phase G-2.1).
 *
 * Larger, more detailed counterpart to `StrategyProvenanceChip` — renders
 * inside a `Panel` on the strategy detail page. Always renders something
 * (a "Human" attribution for human-authored strategies) so the section
 * shows up unconditionally and the reader understands *who* created the
 * strategy, not just *whether* an agent did.
 *
 * The "Recommended in <task>" line only appears when an exploration task
 * is linked to the strategy via `findings.recommended_strategy_id`.
 */
import { Link } from 'react-router-dom'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Panel } from '@/components/ui/Panel'
import { formatDate } from '@/utils/formatters'
import { useStrategyProvenance } from '@/hooks/useStrategyProvenance'

interface StrategyProvenanceSectionProps {
  strategyId: string
  /**
   * ISO 8601 timestamp the strategy was created. Always shown in the
   * section regardless of author kind.
   */
  createdAt: string
}

/**
 * Provenance panel on the strategy detail page. Always renders — the
 * "Author kind" row defaults to "Human" when no `strategy_created`
 * activity row is found for an api_key actor.
 */
export function StrategyProvenanceSection({
  strategyId,
  createdAt,
}: StrategyProvenanceSectionProps): React.JSX.Element {
  const { authorKind, agentLabel, recommendingTask, isLoading } =
    useStrategyProvenance(strategyId)

  const authorKindLabel = authorKind === 'agent' ? 'Agent' : 'Human'
  const isAgent = authorKind === 'agent'

  return (
    <Panel data-testid={`strategy-provenance-section-${strategyId}`}>
      <Eyebrow>Provenance</Eyebrow>
      <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
        How this strategy came to be
      </h2>
      <dl className="mt-4 grid gap-5 sm:grid-cols-2">
        <Field label="Author kind">
          <span
            className={
              isAgent
                ? 'text-amber font-eyebrow'
                : 'text-ink-muted font-eyebrow'
            }
            data-testid={`strategy-provenance-author-kind-${strategyId}`}
          >
            {isLoading && authorKind === 'unknown'
              ? 'Loading…'
              : authorKindLabel}
          </span>
        </Field>
        {isAgent && (
          <Field label="API key label">
            {agentLabel !== null ? (
              <Link
                to={`/activity?actor_label=${encodeURIComponent(agentLabel)}`}
                className="font-tabular text-body-md text-amber hover:underline underline-offset-4"
                data-testid={`strategy-provenance-key-label-${strategyId}`}
              >
                {agentLabel}
              </Link>
            ) : (
              <span className="font-tabular text-body-md text-ink-muted">
                Unlabelled key
              </span>
            )}
          </Field>
        )}
        <Field label="Created">
          <span className="font-tabular text-body-md text-ink">
            {formatDate(createdAt, true)}
          </span>
        </Field>
      </dl>
      {recommendingTask !== null && (
        <p
          className="mt-5 text-body-sm text-ink-muted"
          data-testid={`strategy-provenance-task-link-${strategyId}`}
        >
          Recommended in{' '}
          <Link
            to={`/exploration-tasks/${recommendingTask.taskId}`}
            className="text-amber hover:underline underline-offset-4"
          >
            {recommendingTask.taskTitle}
          </Link>
        </p>
      )}
    </Panel>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="space-y-1.5">
      <dt>
        <Eyebrow>{label}</Eyebrow>
      </dt>
      <dd>{children}</dd>
    </div>
  )
}
