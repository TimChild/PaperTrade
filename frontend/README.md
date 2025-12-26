# PaperTrade Frontend

Modern React frontend for the PaperTrade stock market emulation platform.

## Tech Stack

- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **Tailwind CSS** - Utility-first styling
- **Vitest** - Unit testing framework
- **Testing Library** - Component testing utilities

## Getting Started

### Prerequisites

- Node.js 20+
- npm 10+

### Installation

```bash
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at [http://localhost:5173](http://localhost:5173)

### Building

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run typecheck` - Type check with TypeScript
- `npm test` - Run tests once
- `npm run test:watch` - Run tests in watch mode
- `npm run test:ui` - Run tests with UI

## Project Structure

```
src/
├── components/
│   ├── ui/              # Base UI components
│   └── *.tsx            # Feature components
├── hooks/               # Custom React hooks
├── services/            # API client services
├── stores/              # Zustand stores
├── types/               # TypeScript type definitions
├── utils/               # Utility functions
├── pages/               # Page components
├── App.tsx              # Root component
├── main.tsx             # Application entry point
└── index.css            # Global styles
```

## Backend Connection

The frontend connects to the backend API at `http://localhost:8000`. The Vite dev server proxies `/api` requests to the backend.

To verify the connection, check the System Status section on the home page, which displays the health check status.

## Code Style

- **TypeScript strict mode** - All code must be type-safe
- **ESLint** - Linting with React and TypeScript rules
- **Prettier** - Code formatting (see `.prettierrc`)
- **Path aliases** - Use `@/` to import from `src/`

Example:
```typescript
import { HealthCheck } from '@/components/HealthCheck'
import { useHealthCheck } from '@/hooks/useHealthCheck'
import type { HealthResponse } from '@/types/api'
```

## Testing

Tests are colocated with components using the `.test.tsx` suffix.

```typescript
// Component
src/components/Button.tsx

// Test
src/components/Button.test.tsx
```

Run tests:
```bash
npm test
```

## Contributing

See the main repository README and `.github/copilot-instructions.md` for contribution guidelines.

