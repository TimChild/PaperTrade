/**
 * Recent-activity feed (Phase H2 / Phase G-2.2).
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
 *
 * Phase G-2 added the actor-label drill-down: clicking an agent's actor
 * label navigates to `/activity?actor_label=<label>`, which mounts a
 * filtered ActivityFeed via the `actorLabel` prop. The prop also lets
 * the standalone page seed the filter from the URL search param.
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
  /**
   * Optional actor-label filter. When set, only API-key-authored events
   * with this label are surfaced. Mounted by the `/activity` page when
   * the `actor_label` query param is present.
   */
  actorLabel?: string
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
 * - `actor_kind="api_key"` → render the label as a clickable link that
 *   navigates to `/activity?actor_label=<label>`, surfacing the same
 *   actor's activity in isolation. Falls back to a plain span when the
 *   label is missing.
 *
 * The `onActorClick` prop is optional — when omitted, the actor renders
 * as a non-interactive span (used by the standalone activity page when
 * we're already filtered to a single actor, so re-clicking the label
 * would be a no-op).
 */
function ActorCell({
  event,
  onActorClick,
}: {
  event: ActivityEventResponse
  onActorClick?: (label: string) => void
}) {
  if (event.actor_kind === 'user') {
    return <span className="text-foreground-secondary text-sm">you</span>
  }
  const label = event.actor_label ?? '—'
  if (event.actor_label !== null && onActorClick) {
    return (
      <button
        type="button"
        onClick={() => onActorClick(label)}
        data-testid={`activity-actor-link-${label}`}
        className="text-primary font-medium text-sm hover:underline underline-offset-4 cursor-pointer"
        aria-label={`Filter activity by ${label}`}
      >
        {label}
      </button>
    )
  }
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
  actorLabel,
}: ActivityFeedProps): React.JSX.Element {
  const navigate = useNavigate()
  const [activeTypes, setActiveTypes] = useState<ActivityEventType[]>([])

  const params = useMemo(
    () => ({
      limit,
      // Pass undefined when no filter is selected — the backend treats
      // missing `event_type` as "all types".
      event_type: activeTypes.length > 0 ? activeTypes : undefined,
      actor_label: actorLabel,
    }),
    [limit, activeTypes, actorLabel]
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

  // Clicking an actor label routes to the standalone activity drill-down.
  // When the feed is *already* filtered (we have an `actorLabel` prop),
  // we suppress the click handler so the label isn't interactive — that
  // would be a no-op navigation.
  const handleActorClick = actorLabel
    ? undefined
    : (label: string): void => {
        navigate(`/activity?actor_label=${encodeURIComponent(label)}`)
        // Scroll the new view to the top — the drill-down page mounts a
        // fresh ActivityFeed.
        window.scrollTo({ top: 0, behavior: 'smooth' })
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
                const dest = rowDestination(
                  event.subject_type,
                  event.subject_id
                )
                const interactive = dest !== null
                return (
                  <tr
                    key={`${event.type}-${event.subject_id}-${event.occurred_at}`}
                    className={
                      interactive ? 'transition-colors hover:bg-muted/40' : ''
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
                      <ActorCell
                        event={event}
                        onActorClick={handleActorClick}
                      />
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
