/**
 * Mock for @clerk/clerk-react
 */
import { vi } from 'vitest'

export const mockClerk = {
  useAuth: vi.fn(() => ({
    isSignedIn: true,
    isLoaded: true,
    userId: 'test-user-id',
    sessionId: 'test-session-id',
    getToken: vi.fn(async () => 'mock-clerk-token'),
  })),
  SignedIn: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SignedOut: () => null,
  SignInButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SignUpButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  UserButton: () => <div>UserButton</div>,
  ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}

// Mock module
vi.mock('@clerk/clerk-react', () => mockClerk)
