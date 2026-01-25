# Design System Tokens

## Overview

All design tokens are centralized in `frontend/tailwind.config.ts` and should be used via Tailwind utility classes. This document provides a comprehensive reference for all available design tokens with usage guidelines and examples.

## Colors

### Primary (Brand)

**Purpose**: Main brand color for primary actions, links, and interactive elements.

| Token | Tailwind Class | Hex | Usage |
|-------|----------------|-----|-------|
| primary | `bg-primary`, `text-primary`, `border-primary` | #2563eb (blue-600) | Primary buttons, links |
| primary-hover | `bg-primary-hover`, `text-primary-hover` | #1d4ed8 (blue-700) | Hover state |
| primary-light | `bg-primary-light`, `text-primary-light` | #3b82f6 (blue-500) | Lighter variant |
| primary-dark | `bg-primary-dark`, `text-primary-dark` | #1e40af (blue-800) | Darker variant |

**Example**:
```tsx
<button className="bg-primary hover:bg-primary-hover text-white px-6 py-3 rounded-button">
  Buy Stock
</button>
```

### Semantic Colors (Financial)

**Purpose**: Represent gains/losses and positive/negative values in financial data.

| Token | Tailwind Class | Hex | Usage |
|-------|----------------|-----|-------|
| positive | `text-positive`, `bg-positive` | #16a34a (green-600) | Gains, positive values |
| positive-light | `text-positive-light` | #22c55e (green-500) | Lighter variant |
| positive-dark | `text-positive-dark` | #15803d (green-700) | Darker variant |
| negative | `text-negative`, `bg-negative` | #dc2626 (red-600) | Losses, negative values |
| negative-light | `text-negative-light` | #ef4444 (red-500) | Lighter variant |
| negative-dark | `text-negative-dark` | #b91c1c (red-700) | Darker variant |

**Example**:
```tsx
const dailyChange = portfolio.dailyChange;
const changeClass = dailyChange >= 0 ? 'text-positive' : 'text-negative';

<p className={cn('text-value-secondary', changeClass)}>
  {formatCurrency(dailyChange)}
</p>
```

### Background Colors

**Purpose**: Page and component backgrounds that support light/dark mode via CSS variables.

| Token | Tailwind Class | Light Mode | Dark Mode | Usage |
|-------|----------------|------------|-----------|-------|
| background-primary | `bg-background-primary` | #f9fafb (gray-50) | #0f172a (slate-900) | Page background |
| background-secondary | `bg-background-secondary` | #ffffff (white) | #1e293b (slate-800) | Card background |

**Example**:
```tsx
<div className="bg-background-primary min-h-screen">
  <div className="bg-background-secondary rounded-card p-card-padding">
    {/* Card content */}
  </div>
</div>
```

### Text Colors

**Purpose**: Text hierarchy that supports light/dark mode via CSS variables.

| Token | Tailwind Class | Light Mode | Dark Mode | Usage |
|-------|----------------|------------|-----------|-------|
| foreground-primary | `text-foreground-primary` | #111827 (gray-900) | #f3f4f6 (gray-100) | Headlines, values |
| foreground-secondary | `text-foreground-secondary` | #6b7280 (gray-600) | #9ca3af (gray-400) | Body text, labels |
| foreground-tertiary | `text-foreground-tertiary` | #9ca3af (gray-500) | #6b7280 (gray-500) | Secondary labels |

**Example**:
```tsx
<div>
  <h2 className="text-heading-lg text-foreground-primary">
    Portfolio Name
  </h2>
  <p className="text-sm text-foreground-secondary">
    Last updated: 2 hours ago
  </p>
</div>
```

## Typography

### Font Sizes

All typography tokens include font size, line height, and font weight.

| Token | Tailwind Class | Size | Line Height | Weight | Usage |
|-------|----------------|------|-------------|--------|-------|
| heading-xl | `text-heading-xl` | 3rem (48px) | 1 | 300 (light) | Page titles |
| heading-lg | `text-heading-lg` | 1.5rem (24px) | 2rem | 600 (semibold) | Section titles, portfolio names |
| heading-md | `text-heading-md` | 1.25rem (20px) | 1.75rem | 400 (normal) | Subtitles |
| value-primary | `text-value-primary` | 2.25rem (36px) | 2.5rem | 700 (bold) | Primary values (total portfolio value) |
| value-secondary | `text-value-secondary` | 1.25rem (20px) | 1.75rem | 600 (semibold) | Secondary values (cash, daily change) |

**Example**:
```tsx
<div className="bg-background-secondary rounded-card p-card-padding">
  <h2 className="text-heading-lg text-foreground-primary mb-4">
    {portfolio.name}
  </h2>
  <p className="text-value-primary text-foreground-primary">
    {formatCurrency(portfolio.totalValue)}
  </p>
  <p className={cn(
    'text-value-secondary',
    dailyChange >= 0 ? 'text-positive' : 'text-negative'
  )}>
    {formatCurrency(dailyChange)}
  </p>
</div>
```

## Spacing

### Custom Spacing Tokens

| Token | Tailwind Class | Value | Usage |
|-------|----------------|-------|-------|
| container-padding-x | `px-container-padding-x` | 1.5rem (24px) | Page horizontal padding |
| container-padding-y | `py-container-padding-y` | 3rem (48px) | Page vertical padding |
| card-padding | `p-card-padding` | 2rem (32px) | Card internal padding |
| card-gap | `gap-card-gap` | 2rem (32px) | Grid gap between cards |

**Example**:
```tsx
// Page layout with consistent padding
<main className="px-container-padding-x py-container-padding-y">
  <h1 className="text-heading-xl mb-8">Dashboard</h1>

  {/* Card grid */}
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-card-gap">
    <div className="bg-background-secondary rounded-card p-card-padding">
      {/* Card content */}
    </div>
  </div>
</main>
```

## Shadows

### Elevation Tokens

| Token | Tailwind Class | CSS Value | Usage |
|-------|----------------|-----------|-------|
| card | `shadow-card` | 0 10px 15px -3px rgba(0,0,0,0.1) | Card resting state |
| card-hover | `shadow-card-hover` | 0 20px 25px -5px rgba(0,0,0,0.1) | Card hover state |

**Example**:
```tsx
<div className="bg-background-secondary rounded-card shadow-card hover:shadow-card-hover transition-shadow p-card-padding">
  {/* Interactive card with elevation change on hover */}
</div>
```

## Border Radius

### Radius Tokens

| Token | Tailwind Class | Value | Usage |
|-------|----------------|-------|-------|
| card | `rounded-card` | 1rem (16px) | Cards |
| button | `rounded-button` | 0.75rem (12px) | Buttons |
| input | `rounded-input` | 0.5rem (8px) | Form inputs |

**Example**:
```tsx
// Card
<div className="rounded-card bg-background-secondary">...</div>

// Button
<button className="rounded-button bg-primary">...</button>

// Input
<input className="rounded-input border border-gray-300" />
```

## Complete Component Examples

### Portfolio Card

```tsx
import { cn } from '@/utils/cn';
import { formatCurrency } from '@/utils/formatters';

interface PortfolioCardProps {
  portfolio: Portfolio;
  onClick?: () => void;
}

export function PortfolioCard({ portfolio, onClick }: PortfolioCardProps) {
  const dailyChange = portfolio.dailyChange;
  const isPositive = dailyChange >= 0;

  return (
    <div
      className={cn(
        'bg-background-secondary',
        'rounded-card',
        'shadow-card hover:shadow-card-hover',
        'p-card-padding',
        'transition-shadow',
        'cursor-pointer'
      )}
      onClick={onClick}
    >
      <h2 className="text-heading-lg text-foreground-primary mb-4">
        {portfolio.name}
      </h2>

      <p className="text-value-primary text-foreground-primary mb-2">
        {formatCurrency(portfolio.totalValue)}
      </p>

      <p className={cn(
        'text-value-secondary',
        isPositive ? 'text-positive' : 'text-negative'
      )}>
        {isPositive ? '+' : ''}{formatCurrency(dailyChange)}
      </p>

      <p className="text-sm text-foreground-tertiary mt-2">
        Cash: {formatCurrency(portfolio.cash)}
      </p>
    </div>
  );
}
```

### Primary Button

```tsx
import { cn } from '@/utils/cn';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

export function Button({ variant = 'primary', className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'rounded-button px-6 py-3',
        'transition-colors',
        'font-semibold',
        variant === 'primary' && 'bg-primary hover:bg-primary-hover text-white',
        variant === 'secondary' && 'bg-gray-200 hover:bg-gray-300 text-gray-900',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

## Migration Guide

### From Hardcoded Values to Design Tokens

**Before**:
```tsx
<div className="bg-white shadow-lg rounded-2xl p-8">
  <h2 className="text-2xl font-semibold text-gray-900">
    My Portfolio
  </h2>
  <p className="text-4xl font-bold text-gray-900">
    $10,234.56
  </p>
  <p className="text-xl font-semibold text-green-600">
    +$123.45
  </p>
</div>
```

**After**:
```tsx
<div className="bg-background-secondary shadow-card rounded-card p-card-padding">
  <h2 className="text-heading-lg text-foreground-primary">
    My Portfolio
  </h2>
  <p className="text-value-primary text-foreground-primary">
    $10,234.56
  </p>
  <p className="text-value-secondary text-positive">
    +$123.45
  </p>
</div>
```

### Benefits

- **Consistency**: All components use the same color values
- **Maintainability**: Change once in config, apply everywhere
- **Dark Mode**: Automatic support via CSS variables
- **Type Safety**: TypeScript types for token names
- **Autocomplete**: Tailwind IntelliSense shows custom tokens

## Dark Mode Support

To enable dark mode, add the `dark` class to the `<html>` or `<body>` element:

```tsx
// Toggle dark mode
document.documentElement.classList.toggle('dark');

// Set based on system preference
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.documentElement.classList.add('dark');
}
```

All background and text colors using CSS variables will automatically adapt to the dark theme.

## Notes

### Why RGB Format for CSS Variables?

Tailwind's opacity modifiers (`bg-primary/50`) require RGB values. By using `rgb(var(--color) / <alpha-value>)`, we enable runtime theming with opacity support.

**Example**:
```tsx
// Works with opacity modifiers
<div className="bg-background-primary/80">
  {/* 80% opacity background */}
</div>
```

### Why Not Use Tailwind's Built-in Colors?

We extend built-in colors (gray-50, blue-600) with semantic names (background-primary, primary) for:
- Better developer experience
- Design system governance
- Clear intent in code
- Easier theme switching

## Related Documentation

- Tailwind Config: `frontend/tailwind.config.ts`
- CSS Variables: `frontend/src/index.css`
- Type Definitions: `frontend/src/types/design-system.ts`
- Design Decisions: `docs/architecture/20260109_design-system-skinning/design-decisions.md`
