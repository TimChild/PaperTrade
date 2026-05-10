/**
 * Editorial skeleton loader for the Dashboard portfolio grid. Mirrors the
 * shape of PortfolioCard (eyebrow, name, total, day/cash row) so the
 * loading state has the same compositional weight as the loaded grid.
 */
import { Skeleton } from '@/components/ui/skeleton'

export function PortfolioListSkeleton(): React.JSX.Element {
  return (
    <div
      className="grid gap-5 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      data-testid="portfolio-list-skeleton"
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-editorial border border-hairline bg-canvas-raised/40 p-6"
        >
          <Skeleton className="h-3 w-20 mb-3" />
          <Skeleton className="h-6 w-3/4 mb-6" />

          <Skeleton className="h-3 w-16 mb-2" />
          <Skeleton className="h-9 w-32 mb-5" />

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-hairline">
            <div>
              <Skeleton className="h-3 w-12 mb-2" />
              <Skeleton className="h-4 w-20" />
            </div>
            <div>
              <Skeleton className="h-3 w-12 mb-2" />
              <Skeleton className="h-4 w-20" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
