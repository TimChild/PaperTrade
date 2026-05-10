import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
// Self-hosted fonts (no external CDN). Fraunces variable for display, IBM
// Plex Sans variable for body, IBM Plex Mono for tabular financial numerics.
// See `frontend/src/styles/theme.css` for usage / token wiring.
import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/ibm-plex-sans/wght.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { AuthProvider } from './components/AuthProvider.tsx'

// Get Clerk publishable key from environment
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!CLERK_PUBLISHABLE_KEY) {
  console.error(
    'Missing Clerk publishable key. Please set VITE_CLERK_PUBLISHABLE_KEY in your .env file.'
  )
  // Render error message instead of crashing
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <div style={{ padding: '2rem', fontFamily: 'system-ui' }}>
        <h1>Configuration Error</h1>
        <p>
          Missing Clerk authentication key. Please configure
          VITE_CLERK_PUBLISHABLE_KEY environment variable.
        </p>
      </div>
    </StrictMode>
  )
} else {
  // Create a client
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  })

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ErrorBoundary>
        <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
          <AuthProvider>
            <QueryClientProvider client={queryClient}>
              <App />
            </QueryClientProvider>
          </AuthProvider>
        </ClerkProvider>
      </ErrorBoundary>
    </StrictMode>
  )
}
