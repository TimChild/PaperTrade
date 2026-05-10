/**
 * Activity page (Phase G-2.2) — standalone drill-down view for the
 * recent-activity feed.
 *
 * Reads the `actor_label` query param from the URL to filter the
 * feed. When present, the page renders a contextual header noting
 * "Activity by <label>" plus a chip rail of all known actor labels
 * (derived from the user's API keys) so they can pivot between actors
 * without going back to the dashboard.
 *
 * When no `actor_label` is set, the page renders the unfiltered feed.
 * This keeps the page useful as a bookmark target — `/activity` is a
 * legitimate "give me everything" view.
 */
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { ActivityFeed } from '@/components/features/activity/ActivityFeed'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { useApiKeys } from '@/hooks/useApiKeys'
import { cn } from '@/lib/utils'

export function Activity(): React.JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams()
  const actorLabel = searchParams.get('actor_label') ?? null

  const { data: apiKeysData } = useApiKeys()
  const actorLabels = (apiKeysData?.items ?? [])
    .map((k) => k.label)
    .filter((label, idx, arr) => arr.indexOf(label) === idx)
    .sort((a, b) => a.localeCompare(b))

  const handleSelectActor = (label: string | null): void => {
    if (label === null) {
      setSearchParams({})
    } else {
      setSearchParams({ actor_label: label })
    }
  }

  return (
    <PageFrame>
      <Link
        to="/dashboard"
        data-testid="activity-page-back-link"
        className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
        style={{ minHeight: 'auto' }}
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Dashboard
      </Link>

      <div
        className="mt-4 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="activity-page"
      >
        <SectionHeader
          eyebrow={actorLabel ? 'Drill-down' : 'Activity'}
          title={actorLabel ? `Activity by ${actorLabel}` : 'Recent activity'}
          as="h1"
          description={
            actorLabel
              ? `Showing every event the "${actorLabel}" API key has authored over the last 7 days. Click an event row to navigate to its detail page.`
              : 'Trades, backtests, strategies, and agent activity across your portfolios.'
          }
          withRule
        />
      </div>

      {actorLabels.length > 0 && (
        <section
          className="mt-6 reveal"
          style={{ ['--reveal-delay' as string]: '60ms' }}
          data-testid="activity-page-actor-rail"
        >
          <Eyebrow>Filter by actor</Eyebrow>
          <div
            className="mt-3 flex flex-wrap gap-2"
            role="tablist"
            aria-label="Filter activity by actor label"
          >
            <ActorChip
              label="Everyone"
              testId="activity-page-actor-chip-all"
              active={actorLabel === null}
              onClick={() => handleSelectActor(null)}
            />
            {actorLabels.map((label) => (
              <ActorChip
                key={label}
                label={label}
                testId={`activity-page-actor-chip-${label}`}
                active={actorLabel === label}
                onClick={() => handleSelectActor(label)}
              />
            ))}
          </div>
        </section>
      )}

      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        <ActivityFeed
          // Re-mount when the filter changes so the underlying state
          // (e.g. selected event-type chips) is reset between views.
          key={actorLabel ?? '__all__'}
          actorLabel={actorLabel ?? undefined}
        />
      </section>
    </PageFrame>
  )
}

interface ActorChipProps {
  label: string
  testId: string
  active: boolean
  onClick: () => void
}

function ActorChip({
  label,
  testId,
  active,
  onClick,
}: ActorChipProps): React.JSX.Element {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-testid={testId}
      onClick={onClick}
      className={cn(
        'rounded-editorial border px-3 py-1.5 font-eyebrow transition-colors duration-quick ease-editorial',
        active
          ? 'border-amber bg-amber-soft text-amber'
          : 'border-hairline bg-canvas-raised/40 text-ink-muted hover:border-hairline-strong hover:text-ink'
      )}
    >
      {label}
    </button>
  )
}

function PageFrame({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="mx-auto max-w-[1240px] px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-16">
        {children}
      </div>
    </div>
  )
}
