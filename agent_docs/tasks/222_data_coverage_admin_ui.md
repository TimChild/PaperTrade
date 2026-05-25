# Task 222 — Data-coverage admin UI: delete button + gap mini-viz

## Overview

Two surface additions to `/admin/data-coverage`:

1. **Delete column** — destructive "remove this ticker entirely" action with a
   confirmation modal. Wired to the new `DELETE
   /api/v1/admin/data-coverage/tickers/{ticker}` endpoint.
2. **Inline mini-viz** — small SVG strip per row showing the coverage span
   (`coverage_start` → `coverage_end`) with gap segments rendered as red
   stripes. Consumes the new `gap_ranges` field on the coverage response.

## Context

### What exists

- `frontend/src/pages/AdminDataCoverage.tsx` — the page being modified. Already
  has columns: Ticker, Track button, Catch up button, Range, Last refresh, Gap
  count, Status.
- Tailwind for styling; no chart lib needed — render the mini-viz as a small
  inline SVG (~120×16px). Match the existing dark-editorial palette
  (red-500 for gaps, neutral-700 for the covered band).
- TanStack Query for data fetching. The page already invalidates the coverage
  query on mutation success — wire the new delete the same way.
- An existing confirm-modal pattern? Check
  `frontend/src/components/ui/` for any Dialog/Modal primitive. If there isn't
  one, build a small inline AlertDialog with focus trap + ESC + click-outside
  to dismiss. Don't pull in a new dependency.

### What the new API contract looks like (delivered by Task 221)

Per coverage entry, additionally:

```json
{
  "gap_ranges": [
    {"start": "2026-04-12", "end": "2026-04-12"},
    {"start": "2026-05-15", "end": "2026-05-17"}
  ]
}
```

New endpoint:

```
DELETE /api/v1/admin/data-coverage/tickers/{ticker}  →  204 | 404
```

`POST /admin/watchlist` now returns 422 when AV doesn't recognise the symbol.
The pin button should surface this error with a clear toast / inline message
("Ticker NOT_A_REAL_TICKER is not recognised by the market-data provider").

## Architecture

### Mini-viz spec

- Width: fixed 120px (responsive scaling not needed at table width).
- Height: 14–16px.
- Background band: covered range from `coverage_start` to `coverage_end` in a
  neutral-700 fill.
- Gap segments: red-500 stripes positioned proportionally inside the band.
  Each gap range's start/end maps to a percentage of the
  `[coverage_start, coverage_end]` span.
- Hover tooltip: list the gap dates as `Apr 12, 2026` or `May 15–17, 2026`.
  Use a native `<title>` element inside the SVG for accessibility; native
  tooltip is fine for now.
- Empty state: when `gap_ranges.length === 0`, render the solid neutral band
  only (no stripes).
- No-coverage state: when `coverage_start`/`coverage_end` is `null`, render
  nothing (current behaviour for the gap-count cell).

Put this in `frontend/src/components/features/admin/CoverageGapBar.tsx`. Pure
component, props: `{ coverageStart: string | null; coverageEnd: string | null;
gapRanges: Array<{start: string; end: string}> }`.

### Delete column

- New column after "Status".
- Button labelled "Delete" with red text + outline; on click opens a confirm
  modal: "Delete TICKER? This removes the watchlist entry and all stored
  price history. This action cannot be undone." Two buttons: "Cancel" /
  "Delete TICKER".
- The mutation calls `DELETE /api/v1/admin/data-coverage/tickers/{ticker}`.
  Disable both buttons in the modal while in-flight.
- On 204: invalidate the coverage query and close the modal.
- On 404: toast "Ticker TICKER not found." and close the modal.
- On other errors: toast the error envelope's `detail` and leave the modal
  open so the operator can retry.

### Validation error on pin

`POST /admin/watchlist` returning 422 should surface the `detail` field
verbatim in the existing pin-error UI (toast or inline). Today the page
swallows the error or shows a generic message — fix that so the operator can
distinguish "invalid ticker symbol format" from "AV doesn't recognise this
symbol".

## Implementation plan

1. **Add `gapRanges` to the coverage row type + Zod (or TS interface) schema**
   in `frontend/src/lib/api/admin-data-coverage.ts` (or wherever the API
   client lives). Default to `[]` if backend returns the field omitted (only
   for the pre-deploy interim — the field will always be present once the
   backend ships).
2. **Build `CoverageGapBar`** with a Vitest story / test asserting the SVG
   has the right number of `<rect>` elements for various inputs.
3. **Wire `CoverageGapBar` into the table row** next to or beneath the gap
   count.
4. **Add the Delete column + confirm modal** + mutation hook + Playwright
   E2E walkthrough: pin a fake ticker → confirm delete → confirm it
   disappears from the table. (The E2E will need backend test fixtures —
   use the same pattern as the existing data-coverage E2E.)
5. **Improve pin-error surface** for the new 422 case.
6. **Manual smoke** with the real backend running before opening the PR.

## Testing strategy

- Unit tests for `CoverageGapBar` (Vitest): correct number/positioning of
  gap rects; renders empty state; handles `null` coverage dates.
- E2E (Playwright): delete flow including the modal and the empty-row
  consequence.
- Manual: visual review at the actual table width to confirm the mini-viz
  reads correctly.

## Success criteria

- New Delete column visible; clicking opens a confirm modal; confirming
  removes the row.
- Mini-viz renders per row with correct gap positions.
- Pin error message surfaces 422 detail correctly.
- All existing tests pass; lint + typecheck clean.

## Out of scope

- Backend changes — that's Task 221.
- Visualising the *expected* (clamped) epoch range vs the actual data —
  potential follow-up, but for now the mini-viz only shows `coverage_start →
  coverage_end`. We can extend it later to show the head-gap (epoch to
  coverage_start) as a different colour if useful.

## Agent assignment

`frontend-swe` (Sonnet 4.6). One PR. Wait for Task 221's PR to merge before
opening this PR (frontend depends on the new contract). Follow the standard
PR-lifecycle: open PR, run `/code-review <PR#>`, address findings, self-merge
on green.

## References

- `agent_docs/tasks/220_watchlist_admin_surface.md` — pin/unpin UI pattern.
- `agent_docs/tasks/221_data_coverage_admin_ops.md` — backend contract.
- `frontend/src/pages/AdminDataCoverage.tsx` — the page being modified.
- `docs/architecture/principles.md` — Clean Architecture / React conventions.
