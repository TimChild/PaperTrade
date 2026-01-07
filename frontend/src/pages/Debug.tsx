import type { JSX } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth, useClerk } from '@clerk/clerk-react'
import { debugApi } from '@/services/api/debug'

/**
 * Debug page that displays runtime environment information
 * Path: /debug
 *
 * Security Note: This page displays redacted API key information
 * and is intended for development/debugging only.
 */
export function Debug(): JSX.Element {
  const {
    data: backendInfo,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['debug'],
    queryFn: () => debugApi.getInfo(),
  })

  const { isSignedIn, userId } = useAuth()
  const clerk = useClerk()

  // Frontend environment info
  const frontendEnv = {
    nodeEnv: import.meta.env.MODE,
    apiUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    clerkPublishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
  }

  // Browser info
  const browserInfo = {
    userAgent: navigator.userAgent,
    windowSize: `${window.innerWidth}x${window.innerHeight}`,
    localStorageKeys: Object.keys(localStorage),
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            🔧 Debug Information
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Runtime environment and configuration status
          </p>
        </div>

        {/* Warning Banner */}
        <div className="mb-6 rounded-lg border-2 border-yellow-400 bg-yellow-50 p-4 dark:bg-yellow-900/20">
          <div className="flex items-start">
            <span className="mr-2 text-2xl">⚠️</span>
            <div>
              <p className="font-semibold text-yellow-800 dark:text-yellow-300">
                Development Only
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-400">
                This page is for development and debugging. It will be removed
                or protected before production deployment.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Frontend Environment */}
          <DebugSection title="Frontend Environment">
            <DebugRow label="Environment" value={frontendEnv.nodeEnv} />
            <DebugRow label="React" value="19.2.0" />
            <DebugRow label="Backend URL" value={frontendEnv.apiUrl} />
          </DebugSection>

          {/* Authentication Status */}
          <DebugSection title="Authentication (Clerk)">
            <DebugRow
              label="Clerk loaded"
              value={clerk.loaded ? '✅ Yes' : '❌ No'}
            />
            <DebugRow
              label="Publishable key present"
              value={frontendEnv.clerkPublishableKey ? '✅ Yes' : '❌ No'}
            />
            {frontendEnv.clerkPublishableKey && (
              <DebugRow
                label="Publishable key (prefix)"
                value={frontendEnv.clerkPublishableKey.substring(0, 20) + '...'}
                mono
              />
            )}
            <DebugRow
              label="Signed in"
              value={isSignedIn ? '✅ Yes' : '❌ No'}
            />
            {userId && <DebugRow label="User ID" value={userId} mono />}
          </DebugSection>

          {/* Browser/Client Info */}
          <DebugSection title="Browser / Client">
            <DebugRow label="Window size" value={browserInfo.windowSize} />
            <DebugRow
              label="LocalStorage keys"
              value={
                browserInfo.localStorageKeys.length > 0
                  ? browserInfo.localStorageKeys.join(', ')
                  : 'None'
              }
            />
            <DebugRow label="User Agent" value={browserInfo.userAgent} small />
          </DebugSection>

          {/* Backend Status */}
          {isLoading && (
            <DebugSection title="Backend Status">
              <div className="flex items-center justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600 dark:border-gray-700 dark:border-t-blue-400" />
              </div>
            </DebugSection>
          )}

          {error && (
            <DebugSection title="Backend Status">
              <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
                <p className="font-semibold text-red-800 dark:text-red-300">
                  ❌ Failed to connect to backend
                </p>
                <p className="mt-1 text-sm text-red-700 dark:text-red-400">
                  {error instanceof Error ? error.message : 'Unknown error'}
                </p>
              </div>
            </DebugSection>
          )}

          {backendInfo && (
            <>
              {/* Backend Environment */}
              <DebugSection title="Backend Environment">
                <DebugRow
                  label="Environment"
                  value={backendInfo.environment.environment}
                />
                <DebugRow
                  label="Python"
                  value={backendInfo.environment.python_version}
                />
                <DebugRow
                  label="FastAPI"
                  value={backendInfo.environment.fastapi_version}
                />
              </DebugSection>

              {/* Database Status */}
              <DebugSection title="Database">
                <DebugRow
                  label="Connected"
                  value={
                    backendInfo.database.connected
                      ? '✅ Connected'
                      : '❌ Not connected'
                  }
                />
                <DebugRow
                  label="URL"
                  value={backendInfo.database.url}
                  mono
                  small
                />
                <DebugRow
                  label="Pool size"
                  value={backendInfo.database.pool_size.toString()}
                />
              </DebugSection>

              {/* Redis Status */}
              <DebugSection title="Redis">
                <DebugRow
                  label="Connected"
                  value={
                    backendInfo.redis.connected
                      ? '✅ Connected'
                      : '❌ Not connected'
                  }
                />
                <DebugRow
                  label="URL"
                  value={backendInfo.redis.url}
                  mono
                  small
                />
                <DebugRow label="Ping" value={backendInfo.redis.ping} />
              </DebugSection>

              {/* API Keys */}
              <DebugSection title="API Keys (Redacted)">
                <ApiKeyRow
                  label="Clerk Secret Key"
                  keyInfo={backendInfo.api_keys.clerk_secret_key}
                />
                <ApiKeyRow
                  label="Alpha Vantage API Key"
                  keyInfo={backendInfo.api_keys.alpha_vantage_api_key}
                />
              </DebugSection>

              {/* External Services */}
              {Object.keys(backendInfo.services).length > 0 && (
                <DebugSection title="External Services">
                  {backendInfo.services.clerk && (
                    <DebugRow
                      label="Clerk API"
                      value={`✅ Configured (checked: ${new Date(backendInfo.services.clerk.last_check).toLocaleTimeString()})`}
                    />
                  )}
                  {backendInfo.services.alpha_vantage && (
                    <DebugRow
                      label="Alpha Vantage"
                      value={`✅ Configured (checked: ${new Date(backendInfo.services.alpha_vantage.last_check).toLocaleTimeString()})`}
                    />
                  )}
                </DebugSection>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

interface DebugSectionProps {
  title: string
  children: React.ReactNode
}

function DebugSection({ title, children }: DebugSectionProps): JSX.Element {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-white">
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

interface DebugRowProps {
  label: string
  value: string
  mono?: boolean
  small?: boolean
}

function DebugRow({
  label,
  value,
  mono = false,
  small = false,
}: DebugRowProps): JSX.Element {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:gap-4">
      <dt className="min-w-[200px] font-medium text-gray-700 dark:text-gray-300">
        {label}:
      </dt>
      <dd
        className={`
          text-gray-900 dark:text-gray-100
          ${mono ? 'font-mono' : ''}
          ${small ? 'text-sm break-all' : ''}
        `}
      >
        {value}
      </dd>
    </div>
  )
}

interface ApiKeyRowProps {
  label: string
  keyInfo: { present: boolean; prefix?: string; length?: number }
}

function ApiKeyRow({ label, keyInfo }: ApiKeyRowProps): JSX.Element {
  if (!keyInfo.present) {
    return <DebugRow label={label} value="❌ Not configured" />
  }

  const value = `✅ ${keyInfo.prefix}*** (${keyInfo.length} chars)`
  return <DebugRow label={label} value={value} mono />
}
