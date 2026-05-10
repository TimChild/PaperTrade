/**
 * API key list — renders the user's keys in a table with revoke action.
 *
 * Column set: label, scopes, id (last 8 chars), created at, last used,
 * status, revoke button. Revoked / expired keys remain in the list with
 * a status pill so the user can audit history (matching the backend's
 * never-hard-delete policy).
 */
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/utils/formatters'
import type { ApiKeyScope, ApiKeySummary } from '@/services/api/types'

interface ApiKeyListProps {
  items: ApiKeySummary[]
  onRevoke: (apiKey: ApiKeySummary) => void
  pendingRevokeId: string | null
}

const SCOPE_TONE: Record<ApiKeyScope, string> = {
  read: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  trade: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  admin:
    'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200',
}

function shortId(id: string): string {
  return id.replace(/-/g, '').slice(-8)
}

export function ApiKeyList({
  items,
  onRevoke,
  pendingRevokeId,
}: ApiKeyListProps): React.JSX.Element {
  return (
    <div
      className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
      data-testid="api-key-list"
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Label
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Scopes
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              ID
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Created
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Last used
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Status
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((apiKey) => (
            <ApiKeyRow
              key={apiKey.id}
              apiKey={apiKey}
              onRevoke={onRevoke}
              isPending={pendingRevokeId === apiKey.id}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface ApiKeyRowProps {
  apiKey: ApiKeySummary
  onRevoke: (apiKey: ApiKeySummary) => void
  isPending: boolean
}

function ApiKeyRow({
  apiKey,
  onRevoke,
  isPending,
}: ApiKeyRowProps): React.JSX.Element {
  const statusBadge = renderStatus(apiKey)

  return (
    <tr
      data-testid={`api-key-list-row-${apiKey.id}`}
      className="border-b border-gray-100 dark:border-gray-800"
    >
      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
        {apiKey.label}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {apiKey.scopes.map((scope) => (
            <span
              key={scope}
              className={`inline-flex items-center rounded-button px-2 py-0.5 font-mono text-xs ${SCOPE_TONE[scope]}`}
              data-testid={`api-key-row-scope-${apiKey.id}-${scope}`}
            >
              {scope}
            </span>
          ))}
        </div>
      </td>
      <td
        className="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400"
        title={apiKey.id}
      >
        …{shortId(apiKey.id)}
      </td>
      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
        {formatDate(apiKey.created_at, false)}
      </td>
      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
        {apiKey.last_used_at !== null
          ? formatDate(apiKey.last_used_at, false)
          : 'Never'}
      </td>
      <td className="px-4 py-3">{statusBadge}</td>
      <td className="px-4 py-3 text-right">
        {apiKey.is_active ? (
          <Button
            variant="destructive"
            size="sm"
            data-testid={`api-key-revoke-${apiKey.id}-btn`}
            onClick={() => onRevoke(apiKey)}
            disabled={isPending}
          >
            {isPending ? 'Revoking…' : 'Revoke'}
          </Button>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
    </tr>
  )
}

function renderStatus(apiKey: ApiKeySummary): React.JSX.Element {
  if (apiKey.revoked_at !== null) {
    return (
      <Badge variant="destructive" data-testid={`api-key-status-${apiKey.id}`}>
        Revoked
      </Badge>
    )
  }
  if (
    apiKey.expires_at !== null &&
    new Date(apiKey.expires_at).getTime() < Date.now()
  ) {
    return (
      <Badge variant="secondary" data-testid={`api-key-status-${apiKey.id}`}>
        Expired
      </Badge>
    )
  }
  return <Badge data-testid={`api-key-status-${apiKey.id}`}>Active</Badge>
}
