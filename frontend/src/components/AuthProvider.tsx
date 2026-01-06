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
    // Set up the token getter for API requests
    setAuthTokenGetter(async () => {
      try {
        return await getToken()
      } catch (error) {
        console.error('Failed to get Clerk token:', error)
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
