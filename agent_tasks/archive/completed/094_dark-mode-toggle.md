# Task 094: Implement Dark Mode Toggle with Theme Persistence

**Status**: Not Started
**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: Medium
**Dependencies**: Task 090 (Design tokens with CSS variables)

## Context

We've established our design system with light and dark color tokens defined in CSS variables. Now we need to implement a user-facing dark mode toggle that:
1. Allows users to switch between light/dark themes
2. Persists their choice across sessions
3. Respects system preferences by default
4. Provides smooth visual transitions

Reference: Variant B (Data Dense) dark color scheme from [DashboardVariantB.tsx](../frontend/src/pages/__prototypes__/DashboardVariantB.tsx)

## Goals

Create a complete dark mode implementation that:
- Detects system color scheme preference on first visit
- Provides manual toggle control
- Persists user choice in localStorage
- Works seamlessly across all migrated components
- Includes smooth transitions between themes

## Success Criteria

- [ ] Theme toggle component created with 3 states: light, dark, system
- [ ] Theme preference persists in localStorage
- [ ] System preference detected and respected
- [ ] Smooth transitions when switching themes
- [ ] All 185 tests remain passing
- [ ] Dark mode works across Dashboard and Portfolio Detail screens
- [ ] Toggle accessible via keyboard (WCAG 2.1 AA)

## Implementation Plan

### 1. Theme Context & Hook (45 min)

Create `src/contexts/ThemeContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

type ThemeContextType = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  effectiveTheme: 'light' | 'dark'; // Resolved theme (system → light/dark)
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Load from localStorage or default to 'system'
    const stored = localStorage.getItem('theme') as Theme | null;
    return stored || 'system';
  });

  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    // Resolve effective theme
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      setEffectiveTheme(mediaQuery.matches ? 'dark' : 'light');

      // Listen for system theme changes
      const listener = (e: MediaQueryListEvent) => {
        setEffectiveTheme(e.matches ? 'dark' : 'light');
      };
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    } else {
      setEffectiveTheme(theme);
    }
  }, [theme]);

  useEffect(() => {
    // Apply theme to document
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(effectiveTheme);
  }, [effectiveTheme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, effectiveTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### 2. Theme Toggle Component (30 min)

Create `src/components/ui/theme-toggle.tsx`:

```tsx
import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from './button';

const themes = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'dark', icon: Moon, label: 'Dark' },
  { value: 'system', icon: Monitor, label: 'System' },
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-background p-1">
      {themes.map(({ value, icon: Icon, label }) => (
        <Button
          key={value}
          variant={theme === value ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setTheme(value)}
          aria-label={`Switch to ${label} theme`}
          className="h-8 w-8 p-0"
        >
          <Icon className="h-4 w-4" />
        </Button>
      ))}
    </div>
  );
}
```

### 3. Install lucide-react Icons (5 min)

```bash
npm install lucide-react
```

### 4. Integrate ThemeProvider (15 min)

Update `src/App.tsx`:

```tsx
import { ThemeProvider } from '@/contexts/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        {/* existing app content */}
      </AuthProvider>
    </ThemeProvider>
  );
}
```

### 5. Add Toggle to Navigation (15 min)

Add `<ThemeToggle />` to header/navigation:
- Dashboard: Top-right corner near user menu (future)
- For now: Add to Dashboard page header

Update `src/pages/Dashboard.tsx`:

```tsx
import { ThemeToggle } from '@/components/ui/theme-toggle';

export function Dashboard() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-screen-2xl mx-auto px-content-padding py-content-padding">
        {/* Header */}
        <div className="flex items-center justify-between mb-card-gap">
          <h1 className="text-heading-xl">My Portfolios</h1>
          <ThemeToggle />
        </div>
        {/* rest of dashboard */}
      </div>
    </div>
  );
}
```

### 6. Enhance Dark Mode Colors (30 min)

Review and refine dark mode colors in `src/index.css` based on Variant B:

```css
.dark {
  /* Background hierarchy */
  --background: 222 16% 8%;        /* Deep charcoal #13151a */
  --foreground: 210 20% 98%;       /* Off-white text */
  --muted: 222 16% 12%;            /* Slightly lighter bg */
  --muted-foreground: 215 16% 65%; /* Muted text */

  /* Interactive elements */
  --primary: 212 100% 48%;         /* Bright blue #0078f2 */
  --primary-foreground: 0 0% 100%; /* White on primary */
  --accent: 222 16% 16%;           /* Hover backgrounds */

  /* Borders & separators */
  --border: 222 16% 20%;           /* Subtle borders */
  --card: 222 16% 10%;             /* Card backgrounds */

  /* Semantic colors */
  --positive: 142 71% 45%;         /* Green for gains */
  --negative: 0 84% 60%;           /* Red for losses */
  --destructive: 0 84% 60%;        /* Error/destructive actions */
}
```

### 7. Add Transition Styles (10 min)

Update `src/index.css` to add smooth theme transitions:

```css
* {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* Disable transitions for theme toggle to prevent flash */
.theme-transition-disable * {
  transition: none !important;
}
```

### 8. Testing (30 min)

**Unit Tests**: Create `src/contexts/__tests__/ThemeContext.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../ThemeContext';

function TestComponent() {
  const { theme, setTheme, effectiveTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="effective-theme">{effectiveTheme}</span>
      <button onClick={() => setTheme('dark')}>Dark</button>
      <button onClick={() => setTheme('light')}>Light</button>
      <button onClick={() => setTheme('system')}>System</button>
    </div>
  );
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to system theme', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme')).toHaveTextContent('system');
  });

  it('persists theme choice to localStorage', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText('Dark'));
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('applies dark class to document', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText('Dark'));
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
```

**Manual Testing**:
1. Toggle between light/dark/system modes
2. Refresh page - verify preference persists
3. Change system theme - verify 'system' mode follows
4. Test all screens (Dashboard, Portfolio Detail)
5. Verify smooth transitions
6. Keyboard navigation (Tab to toggle, Enter to activate)

## Files to Create

1. `frontend/src/contexts/ThemeContext.tsx` - Theme state management
2. `frontend/src/contexts/__tests__/ThemeContext.test.tsx` - Theme context tests
3. `frontend/src/components/ui/theme-toggle.tsx` - Toggle UI component

## Files to Modify

1. `frontend/package.json` - Add lucide-react dependency
2. `frontend/src/App.tsx` - Wrap with ThemeProvider
3. `frontend/src/pages/Dashboard.tsx` - Add ThemeToggle to header
4. `frontend/src/index.css` - Refine dark colors, add transitions

## Expected Outcomes

After completion:
- Users can switch themes via UI toggle
- Theme preference persists across sessions
- System preference respected by default
- Smooth visual transitions between themes
- All 185+ tests passing (new tests added)
- WCAG 2.1 AA accessible

## Next Steps

After this task, proceed to:
- **Task 095**: Final QA, accessibility audit, performance validation, visual polish

## References

- Variant B Prototype: `frontend/src/pages/__prototypes__/DashboardVariantB.tsx`
- shadcn/ui Dark Mode: https://ui.shadcn.com/docs/dark-mode
- Design Tokens: `frontend/src/index.css` (CSS variables)
