/**
 * Recent-activity feed (Phase H2).
 *
 * Renders a chronological list of events authored by the current user
 * across the platform — trades, strategy creations, backtests,
 * activations, exploration tasks, API key minting. Each row's actor
 * column distinguishes Clerk-authored ("you") events from
 * API-key-authored events (the key's human label) so agent activity is
 * visually separable from human activity at a glance.
 *
 * Click a row to navigate to the underlying entity's detail page; the
 * subject_type field controls the destination route.
 */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/skeleton'
import { useActivity } from '@/hooks/useActivity'
import type {
  ActivityEventResponse,
  ActivityEventType,
  SubjectType,
} from '@/services/api/types'
import { formatRelativeTime } from '@/utils/formatters'

interface ActivityFeedProps {
  /** Page size — defaults to 50 to match the backend default. */
  limit?: number
  /** Optional CSS class for the outer container. */
  className?: string
}

interface FilterChip<T extends string> {
  value: T
  label: string
}

const EVENT_TYPE_CHIPS: ReadonlyArray<FilterChip<ActivityEventType>> = [
  { value: 'trade', label: 'Trades' },
  { value: 'strategy_created', label: 'Strategies' },
  { value: 'backtest', label: 'Backtests' },
  { value: 'activation_created', label: 'Activations' },
  { value: 'task_filed', label: 'Tasks' },
  { value: 'api_key_minted', label: 'API keys' },
]

/**
 * Build a destination route for clicking a feed row.
 *
 * The mapping is intentionally explicit (rather than computed from the
 * subject type alone) because the destination url shape varies by
 * type. Subjects without a target page render as non-interactive.
 */
function rowDestination(
  subjectType: SubjectType,
  subjectId: string
): string | null {
  switch (subjectType) {
    case 'portfolio':
      return `/portfolio/${subjectId}`
    case 'backtest':
      return `/backtests/${subjectId}`
    case 'strategy':
      return '/strategies'
    case 'activation':
      return '/activations'
    case 'task':
      // No dedicated detail page yet; navigate to the queue view.
      return null
    case 'api_key':
      return null
    default:
      return null
  }
}

/**
 * Render the actor cell.
 *
 * - `actor_kind="user"` → render "you" in muted ink.
 * - `actor_kind="api_key"` → render the label in primary brand colour
 *   so it visually pops against the rest of the feed.
 */
function ActorCell({ event }: { event: ActivityEventResponse }) {
  if (event.actor_kind === 'user') {
    return (
      <span className="text-foreground-secondary text-sm">you</span>
    )
  }
  const label = event.actor_label ?? '—'
  return (
    <span
      className="text-primary font-medium text-sm"
      data-testid={`activity-feed-actor-label-${label}`}
    >
      {label}
    </span>
  )
}

export function ActivityFeed({
  limit = 50,
  className,
}: ActivityFeedProps): React.JSX.Element {
  const navigate = useNavigate()
  const [activeTypes, setActiveTypes] = useState<ActivityEventType[]>([])

  const params = useMemo(
    () => ({
      limit,
      // Pass undefined when no filter is selected — the backend treats
      // missing `event_type` as "all types".
      event_type: activeTypes.length > 0 ? activeTypes : undefined,
    }),
    [limit, activeTypes]
  )

  const { data, isLoading, isError } = useActivity(params)

  const toggleType = (eventType: ActivityEventType) => {
    setActiveTypes((current) => {
      if (current.includes(eventType)) {
        return current.filter((t) => t !== eventType)
      }
      return [...current, eventType]
    })
  }

  const handleRowClick = (event: ActivityEventResponse) => {
    const dest = rowDestination(event.subject_type, event.subject_id)
    if (dest !== null) {
      navigate(dest)
    }
  }

  return (
    <div className={className} data-testid="activity-feed">
      {/* Filter chip rail */}
      <div
        className="mb-4 flex flex-wrap gap-2"
        data-testid="activity-feed-filters"
      >
        {EVENT_TYPE_CHIPS.map((chip) => {
          const active = activeTypes.includes(chip.value)
          return (
            <button
              key={chip.value}
              type="button"
              onClick={() => toggleType(chip.value)}
              data-testid={`activity-feed-filter-event-type-${chip.value}`}
              aria-pressed={active}
              className={[
                'px-3 py-1 text-xs font-medium uppercase tracking-wide',
                'rounded-button border transition-colors',
                active
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-background-secondary text-foreground-secondary hover:text-foreground-primary',
              ].join(' ')}
            >
              {chip.label}
            </button>
          )
        })}
        {activeTypes.length > 0 && (
          <button
            type="button"
            onClick={() => setActiveTypes([])}
            data-testid="activity-feed-filter-clear"
            className="px-3 py-1 text-xs text-foreground-tertiary hover:text-foreground-primary"
          >
            Clear
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2" data-testid="activity-feed-loading">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : isError ? (
        <div
          className="border border-border rounded-card p-8 text-center"
          data-testid="activity-feed-error"
        >
          <p className="text-sm text-negative">
            Couldn&apos;t load recent activity. Try refreshing.
          </p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState message="No activity yet. Trades, strategies, and tasks will show up here." />
      ) : (
        <div className="border border-border rounded-card overflow-x-auto">
          <table
            className="min-w-full border-collapse"
            data-testid="activity-feed-table"
          >
            <caption className="sr-only">Recent activity</caption>
            <thead className="border-b border-border">
              <tr>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-foreground-secondary"
                >
                  When
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-foreground-secondary"
                >
                  Actor
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-foreground-secondary"
                >
                  What happened
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.items.map((event, idx) => {
                const dest = rowDestination(event.subject_type, event.subject_id)
                const interactive = dest !== null
                return (
                  <tr
                    key={`${event.type}-${event.subject_id}-${event.occurred_at}`}
                    className={
                      interactive
                        ? 'transition-colors hover:bg-muted/40'
                        : ''
                    }
                    data-testid={`activity-feed-row-${idx}`}
                  >
                    <td className="px-4 py-3 align-top">
                      <button
                        type="button"
                        onClick={() => handleRowClick(event)}
                        disabled={!interactive}
                        className={
                          interactive
                            ? 'text-sm font-mono text-foreground-tertiary hover:text-foreground-primary'
                            : 'text-sm font-mono text-foreground-tertiary cursor-default'
                        }
                        data-testid={`activity-feed-row-time-${idx}`}
                      >
                        {formatRelativeTime(event.occurred_at)}
                      </button>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <ActorCell event={event} />
                    </td>
                    <td className="px-4 py-3 align-top">
                      <button
                        type="button"
                        onClick={() => handleRowClick(event)}
                        disabled={!interactive}
                        data-testid={`activity-feed-row-summary-${idx}`}
                        className={
                          interactive
                            ? 'text-left text-sm text-foreground-primary hover:underline'
                            : 'text-left text-sm text-foreground-primary cursor-default'
                        }
                      >
                        {event.summary}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
