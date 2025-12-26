# Task 002: Setup Frontend Project Scaffolding

## Objective
Create the initial frontend project structure with React, Vite, TypeScript, and proper tooling configuration.

## Context
This is Phase 0 work - establishing the foundation before implementing features. The frontend should follow the patterns outlined in `project_strategy.md` and `.github/agents/frontend-swe.md`.

## Requirements

### Project Structure
Create the following directory structure using Vite:
```
frontend/
├── src/
│   ├── components/
│   │   └── ui/              # Base UI components
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API client services
│   ├── stores/              # Zustand stores (if needed)
│   ├── types/               # TypeScript types
│   ├── utils/               # Utility functions
│   ├── pages/               # Page components
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── tests/
│   └── setup.ts
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── eslint.config.js
└── README.md
```

### Package Configuration
- Use Vite as build tool
- React 18+
- TypeScript (strict mode)
- Dependencies:
  - react, react-dom
  - @tanstack/react-query
  - zustand
  - axios (or fetch wrapper)
- Dev dependencies:
  - typescript
  - @types/react, @types/react-dom
  - vite, @vitejs/plugin-react
  - tailwindcss, postcss, autoprefixer
  - eslint, eslint-plugin-react-hooks, @typescript-eslint/*
  - prettier
  - vitest, @testing-library/react, @testing-library/jest-dom

### TypeScript Configuration
- Strict mode enabled
- Path aliases (e.g., `@/` for `src/`)
- Proper JSX configuration for React

### ESLint Configuration
- Use flat config format (eslint.config.js)
- TypeScript support
- React hooks rules
- Import sorting

### Tailwind CSS Setup
- Basic configuration
- Include common utility classes

### Initial App Structure
Create a minimal React application with:
- Basic App component with routing placeholder
- Health check component that calls backend `/health` endpoint
- Proper error boundary
- TanStack Query provider setup

### Basic Tests
- Test that App renders without crashing
- Test health check component (mocked API)

## Success Criteria
- [ ] `npm install` works from frontend directory
- [ ] `npm run dev` starts development server
- [ ] `npm run build` creates production build
- [ ] `npm run lint` passes with no errors
- [ ] `npm run typecheck` passes with no errors
- [ ] `npm run test` runs and passes
- [ ] Can connect to backend health endpoint (when both running)

## References
- See `.github/agents/frontend-swe.md` for coding standards
- See `project_strategy.md` for architecture decisions
- See `.github/copilot-instructions.md` for general guidelines

## Notes
- Keep it minimal - we're just scaffolding, not implementing features yet
- Focus on getting the structure and tooling right
- Ensure the frontend can communicate with the backend API
- Use modern React patterns (hooks, functional components)
