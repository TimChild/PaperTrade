/**
 * Admin API service — wraps the admin-only `/admin/*` endpoint family.
 *
 * Currently exposes the data-coverage endpoints introduced in Phase J
 * (Task #212 Layer 4):
 *
 * - `GET  /admin/data-coverage`           — per-ticker price-history coverage
 * - `POST /admin/data-coverage/backfill`  — operator-driven backfill
 *
 * Auth: admin Clerk Bearer JWT only. Non-admin callers get 403; the
 * caller is expected to gate page rendering on the user's admin status
 * before invoking these.
 *
 * Backend source of truth:
 * `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py`.
 */
import { apiClient } from './client'
import type {
  BackfillRequest,
  BackfillResponse,
  DataCoverageResponse,
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
