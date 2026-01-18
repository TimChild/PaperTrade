import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { setAuthTokenGetter } from '@/services/api/client'

/**
 * AuthProvider component that sets up the authentication token getter
 * for API requests. This should be rendered inside ClerkProvider.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth()

  useEffect(() => {
    // Only set up token getter once Clerk is loaded
    if (!isLoaded) {
      console.log('[AuthProvider] Waiting for Clerk to load...')
      return
    }

    console.log(`[AuthProvider] Clerk loaded. isSignedIn: ${isSignedIn}`)

    // Set up the token getter for API requests
    setAuthTokenGetter(async () => {
      try {
        if (!isLoaded) {
          console.warn('[AuthProvider] Clerk not loaded yet, cannot get token')
          return null
        }

        const token = await getToken()
        if (!token) {
          console.warn('[AuthProvider] No token available from Clerk')
        }
        return token
      } catch (error) {
        console.error('[AuthProvider] Failed to get Clerk token:', error)
        return null
      }
    })

    // Cleanup on unmount
    return () => {
      setAuthTokenGetter(async () => null)
    }
  }, [getToken, isLoaded, isSignedIn])

  return <>{children}</>
}
