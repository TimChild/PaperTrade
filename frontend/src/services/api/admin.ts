/**
 * Admin API service — wraps the admin-only `/admin/*` endpoint family.
 *
 * Exposes:
 *
 * - `GET  /admin/data-coverage`           — per-ticker price-history coverage
 * - `POST /admin/data-coverage/backfill`  — operator-driven backfill
 * - `POST /admin/watchlist`               — pin ticker (Task #220)
 * - `DELETE /admin/watchlist/{ticker}`    — unpin ticker (Task #220)
 *
 * Auth: admin Clerk Bearer JWT only. Non-admin callers get 403; the
 * caller is expected to gate page rendering on the user's admin status
 * before invoking these.
 *
 * Backend source of truth:
 * `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py` and
 * `backend/src/zebu/adapters/inbound/api/admin_watchlist.py`.
 */
import { apiClient } from './client'
import type {
  BackfillRequest,
  BackfillResponse,
  DataCoverageResponse,
  PinTickerRequest,
  PinTickerResponse,
} from './types'

export const dataCoverageApi = {
  /**
   * Fetch the per-ticker data-coverage summary. The response includes
   * one entry per ticker known to the system (watchlist ∪ recently-
   * traded ∪ any ticker with rows in price_history), sorted by symbol.
   */
  list: async (): Promise<DataCoverageResponse> => {
    const response = await apiClient.get<DataCoverageResponse>(
      '/admin/data-coverage'
    )
    return response.data
  },

  /**
   * Enqueue a "catch up" backfill task for `ticker`. The backend
   * computes the date range from `ZEBU_HISTORY_EPOCH` and today's UTC
   * date — Task #215 removed the operator-tunable window because
   * Alpha Vantage's daily endpoint is binary (compact vs full) so
   * picking dates had no actual effect on cost or returned data.
   *
   * Idempotent on `(ticker, ZEBU_HISTORY_EPOCH, today)`: if a
   * non-terminal task already exists for the same window, the
   * response's `existing` flag will be true and `task_id` will
   * reference that existing task.
   */
  backfill: async (body: BackfillRequest): Promise<BackfillResponse> => {
    const response = await apiClient.post<BackfillResponse>(
      '/admin/data-coverage/backfill',
      body
    )
    return response.data
  },
}

/**
 * Watchlist Pin/Unpin admin client (Task #220).
 *
 * Pin is *additive* — adding a ticker to the watchlist keeps it in the
 * scheduler's refresh set after the 30-day trade window lapses. It does
 * NOT change scheduler semantics or trigger a backfill side-effect.
 * Unpin is similarly inert — it doesn't remove a recently-traded ticker
 * from the refresh set, just from the watchlist arm of the union.
 */
export const watchlistApi = {
  /**
   * Pin a ticker. Idempotent — re-pinning an already-active ticker is
   * a no-op server-side and returns the same 201 payload.
   */
  add: async (body: PinTickerRequest): Promise<PinTickerResponse> => {
    const response = await apiClient.post<PinTickerResponse>(
      '/admin/watchlist',
      body
    )
    return response.data
  },

  /**
   * Unpin a ticker. Returns 204 on success; the apiClient returns no
   * body. A 404 means the ticker isn't currently in the watchlist
   * (visible signal that the action did nothing) — the caller should
   * surface that via the mutation's `onError`.
   */
  remove: async (ticker: string): Promise<void> => {
    await apiClient.delete(`/admin/watchlist/${ticker}`)
  },
}
