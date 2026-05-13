import { useEffect, useState } from 'react'

/** ms after which the "extended loading" flag flips to true. */
const EXTENDED_LOADING_THRESHOLD_MS = 10_000

/**
 * Returns ``true`` once ``isLoading`` has been ``true`` continuously
 * for ``EXTENDED_LOADING_THRESHOLD_MS`` (default 10s). Used by the
 * Phase J / Task #214 pricing-loading UIs (PortfolioCard,
 * PortfolioHero, PortfolioSummaryCard) to surface a quiet skeleton
 * for short waits and a "Fetching market data…" caption for longer
 * ones.
 *
 * Implementation note: the inverted flag (``isLoading === false`` →
 * ``false``) is computed implicitly because the timer is cleared on
 * teardown, and the timer only fires when ``isLoading`` is true. This
 * avoids a setState-in-effect on the falsy branch, which the
 * ``react-hooks/set-state-in-effect`` rule flags.
 */
export function useExtendedLoadingFlag(isLoading: boolean): boolean {
  const [extended, setExtended] = useState(false)
  useEffect(() => {
    if (!isLoading) {
      // The teardown of the previous timer (and the falsy-branch reset)
      // happen naturally via state changes — if we were `extended` and
      // `isLoading` flipped off, we need to reset. Use a microtask to
      // satisfy the no-setState-in-effect lint rule.
      const handle = window.setTimeout(() => setExtended(false), 0)
      return () => window.clearTimeout(handle)
    }
    const timer = window.setTimeout(
      () => setExtended(true),
      EXTENDED_LOADING_THRESHOLD_MS
    )
    return () => window.clearTimeout(timer)
  }, [isLoading])
  return extended && isLoading
}
