/**
 * Recent-activity feed API client (Phase H2).
 *
 * Mirrors `GET /api/v1/activity`. The endpoint returns a standard
 * `PaginatedResponse<ActivityEventResponse>`.
 */
import { apiClient } from './client'
import type {
  ActivityEventResponse,
  ListActivityParams,
  PaginatedResponse,
} from './types'

export const activityApi = {
  /**
   * Fetch one page of the recent-activity feed for the authenticated
   * user.
   *
   * `event_type` is repeatable on the wire — the underlying axios
   * paramsSerializer flattens an array into multiple `event_type=...`
   * query params, which matches FastAPI's `list[T]` Query convention.
   */
  list: async (
    params?: ListActivityParams
  ): Promise<PaginatedResponse<ActivityEventResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<ActivityEventResponse>
    >('/activity', {
      params,
      // axios serialises array params as `event_type=a&event_type=b`
      // when `paramsSerializer` is omitted, but defaults vary by version
      // so we set it explicitly for stability.
      paramsSerializer: {
        indexes: null,
      },
    })
    return response.data
  },
}
