# Task 054: Clerk Frontend Integration

**Agent**: frontend-swe
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 1 day
**Dependencies**: Clerk account created, API keys available
**Priority**: HIGH

## Objective

Integrate Clerk authentication into the Zebu React frontend, replacing the current spoofable X-User-Id localStorage approach with proper authentication.

## Prerequisites

1. Clerk account created at https://clerk.com
2. `VITE_CLERK_PUBLISHABLE_KEY` available
3. Backend auth adapter ready (Task #053 backend portion)

## Official Clerk + React (Vite) Integration Guide

Reference: https://clerk.com/docs/react/getting-started/quickstart

### Step 1: Install Clerk React SDK

```bash
cd frontend
npm install @clerk/clerk-react@latest
```

### Step 2: Configure Environment Variables

Create or update `.env.local`:

```bash
VITE_CLERK_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

**Important**:
- The `VITE_` prefix is required for Vite to expose environment variables to client-side code
- `.env.local` is preferred for local development secrets
- Ensure `.gitignore` excludes `.env*` (should already be configured)

### Step 3: Wrap App with ClerkProvider

Update `frontend/src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { ClerkProvider } from "@clerk/clerk-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Clerk Publishable Key");
}

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ClerkProvider>
  </StrictMode>
);
```

### Step 4: Update App Component with Auth UI

Update `frontend/src/App.tsx` to use Clerk components:

```typescript
import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
} from "@clerk/clerk-react";

export default function App() {
  return (
    <>
      <header className="flex justify-between items-center p-4 border-b">
        <h1 className="text-xl font-bold">Zebu</h1>
        <SignedOut>
          <div className="flex gap-2">
            <SignInButton />
            <SignUpButton />
          </div>
        </SignedOut>
        <SignedIn>
          <UserButton />
        </SignedIn>
      </header>

      <main>
        <SignedOut>
          <div className="flex items-center justify-center min-h-[80vh]">
            <div className="text-center">
              <h2 className="text-2xl mb-4">Welcome to Zebu</h2>
              <p className="mb-4">Sign in to start trading</p>
              <SignInButton mode="modal" />
            </div>
          </div>
        </SignedOut>
        <SignedIn>
          {/* Existing trading dashboard components */}
          <TradingDashboard />
        </SignedIn>
      </main>
    </>
  );
}
```

### Step 5: Add Token to API Requests

Create `frontend/src/lib/useAuthenticatedApi.ts`:

```typescript
import { useAuth } from "@clerk/clerk-react";
import { useCallback } from "react";

export function useAuthenticatedFetch() {
  const { getToken } = useAuth();

  return useCallback(
    async (url: string, options: RequestInit = {}) => {
      const token = await getToken();
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
    },
    [getToken]
  );
}
```

Update existing API calls to use authenticated fetch or update axios instance:

```typescript
// frontend/src/lib/api.ts
import { useAuth } from "@clerk/clerk-react";
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
});

// Hook to get authenticated axios instance
export function useAuthenticatedApi() {
  const { getToken } = useAuth();

  // Add interceptor for auth token
  api.interceptors.request.use(async (config) => {
    const token = await getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return api;
}
```

## Implementation Checklist

### Remove Old Auth System

- [ ] Remove `useUserId` hook (if exists)
- [ ] Remove localStorage user ID storage
- [ ] Remove manual X-User-Id headers from API calls
- [ ] Remove any mock user ID generation

### Add Clerk Integration

- [ ] Install `@clerk/clerk-react@latest`
- [ ] Add `VITE_CLERK_PUBLISHABLE_KEY` to `.env.local`
- [ ] Add `VITE_CLERK_PUBLISHABLE_KEY` placeholder to `.env.example`
- [ ] Wrap app in `<ClerkProvider>` in `main.tsx`
- [ ] Add `<SignedIn>`, `<SignedOut>` guards to App
- [ ] Add `<SignInButton>`, `<SignUpButton>`, `<UserButton>` components
- [ ] Create authenticated API wrapper using `useAuth().getToken()`
- [ ] Update all API calls to include Bearer token

### Update Components

- [ ] Dashboard: Wrap in `<SignedIn>`
- [ ] Portfolio views: Ensure auth required
- [ ] Trade forms: Ensure auth required
- [ ] Header: Add `<UserButton>` for signed-in users

### Testing Considerations

- [ ] Mock Clerk in tests (see Clerk testing docs)
- [ ] Update E2E tests for auth flow
- [ ] Ensure tests can run without real Clerk keys

## Critical Rules (From Clerk Guidelines)

### ALWAYS DO

1. Use `@clerk/clerk-react@latest`
2. Use `VITE_CLERK_PUBLISHABLE_KEY` as environment variable name
3. Wrap entire app in `<ClerkProvider>` in `main.tsx`
4. Store real keys only in `.env.local`
5. Use placeholders in any committed files

### NEVER DO

1. Use `frontendApi` instead of `publishableKey`
2. Use older env var names like `REACT_APP_CLERK_FRONTEND_API`
3. Place `<ClerkProvider>` deeper in component tree
4. Commit real API keys to repository

## Success Criteria

- [ ] Users can sign up via Clerk UI
- [ ] Users can sign in via Clerk UI
- [ ] Users can sign out via UserButton
- [ ] All API calls include Clerk JWT token
- [ ] Unauthenticated users see sign-in prompt
- [ ] Authenticated users see trading dashboard
- [ ] No X-User-Id references remain in codebase
- [ ] `.env.example` updated with placeholder
- [ ] All existing tests pass (with mocked auth)

## References

- Clerk React Quickstart: https://clerk.com/docs/react/getting-started/quickstart
- Clerk React SDK: https://clerk.com/docs/references/react/overview
- Clerk Testing: https://clerk.com/docs/testing/overview
- Task #053: Backend auth adapter (ClerkAuthAdapter)
