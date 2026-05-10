/**
 * Triggers API service — wraps the Phase F-5 trigger CRUD + fire-log endpoints.
 *
 * Backend source of truth:
 * `backend/src/zebu/adapters/inbound/api/triggers.py`.
 *
 * Endpoints used by this client:
 *
 * - `POST   /activations/{id}/triggers`  — attach a trigger
 * - `GET    /activations/{id}/triggers`  — list (paginated, includes terminal)
 * - `GET    /triggers/{id}`              — fetch one
 * - `PATCH  /triggers/{id}`              — pause/resume/edit mutable fields
 * - `DELETE /triggers/{id}`              — soft-delete (transitions to EXPIRED)
 * - `GET    /triggers/{id}/fires`        — paginated fire log (newest-first)
 *
 * The kill-switch endpoint (`POST /triggers/disable-all`) is intentionally
 * NOT wired in this client — G-1 scope per the task spec only exposes it via
 * the backend API; the UI surface is a separate small follow-up.
 */
import { apiClient } from './client'
import type {
  CreateTriggerRequest,
  ListTriggerParams,
  PaginatedResponse,
  TriggerFireResponse,
  TriggerResponse,
  UpdateTriggerRequest,
} from './types'

export const triggersApi = {
  /**
   * List every trigger attached to an activation, paginated. Includes
   * terminal-status rows (EXPIRED / MANUALLY_DISABLED) so the UI can render
   * trigger history alongside live ones — matches the backend contract.
   */
  listForActivation: async (
    activationId: string,
    params?: ListTriggerParams
  ): Promise<PaginatedResponse<TriggerResponse>> => {
    const response = await apiClient.get<PaginatedResponse<TriggerResponse>>(
      `/activations/${activationId}/triggers`,
      { params }
    )
    return response.data
  },

  /**
   * Fetch one trigger by id. 404s surface as a TanStack Query error the
   * caller can render via `error` state.
   */
  getById: async (triggerId: string): Promise<TriggerResponse> => {
    const response = await apiClient.get<TriggerResponse>(
      `/triggers/${triggerId}`
    )
    return response.data
  },

  /**
   * Attach a new trigger to an activation. Returns the persisted entity (with
   * server-assigned `id`, `created_at`, etc.). The caller is the activation's
   * owner; 403 if not.
   */
  create: async (
    activationId: string,
    data: CreateTriggerRequest
  ): Promise<TriggerResponse> => {
    const response = await apiClient.post<TriggerResponse>(
      `/activations/${activationId}/triggers`,
      data
    )
    return response.data
  },

  /**
   * Update mutable fields on a trigger (agent_prompt, cooldown, priority,
   * condition_params, or status). Per Phase F design Q3, `status` accepts
   * only `ACTIVE` (resume) or `PAUSED` (pause); lifting MANUALLY_DISABLED via
   * PATCH is rejected by the backend with 422.
   */
  update: async (
    triggerId: string,
    data: UpdateTriggerRequest
  ): Promise<TriggerResponse> => {
    const response = await apiClient.patch<TriggerResponse>(
      `/triggers/${triggerId}`,
      data
    )
    return response.data
  },

  /**
   * Soft-delete a trigger. Transitions the row to EXPIRED on the backend (the
   * row stays so the fire-log endpoint can render history). 204 on success;
   * the API client returns no payload for DELETE.
   */
  delete: async (triggerId: string): Promise<void> => {
    await apiClient.delete(`/triggers/${triggerId}`)
  },

  /**
   * Paginated fire log for one trigger (newest-first). The `condition_evaluation_data`
   * field is per-condition (see Phase F design §1.5) — the UI renders a
   * summary derived from the trigger's `condition_type`.
   */
  listFires: async (
    triggerId: string,
    params?: ListTriggerParams
  ): Promise<PaginatedResponse<TriggerFireResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<TriggerFireResponse>
    >(`/triggers/${triggerId}/fires`, { params })
    return response.data
  },
}
