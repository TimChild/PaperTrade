# Design System Components

## Overview

This document describes the primitive UI components built with shadcn/ui and customized with our design tokens. All components are fully typed, accessible, and support dark mode.

## Installation

Components use the following dependencies:
- `@radix-ui/*` - Accessible component primitives
- `class-variance-authority` - Type-safe variant handling
- `tailwind-merge` - Intelligent CSS class merging
- `clsx` - Conditional class names

## Core Utilities

### cn() Helper

The `cn()` utility intelligently merges Tailwind CSS classes:

```tsx
import { cn } from '@/lib/utils'

// Merges classes and handles conflicts
cn('px-2 py-1', 'px-4') // → 'py-1 px-4' (px-4 overrides px-2)

// Supports conditional classes
cn('text-base', isError && 'text-red-600')

// Used throughout all components
<Button className={cn('w-full', className)} />
```

## Components

### Button

Primary interactive element for user actions.

**Variants**:
- `default` - Primary actions (uses `bg-primary` token)
- `secondary` - Secondary actions (gray background)
- `outline` - Tertiary actions (border only)
- `ghost` - Low emphasis actions (no background)
- `destructive` - Destructive actions (uses `bg-negative` token)

**Sizes**:
- `default` - Standard button (h-10)
- `sm` - Small button (h-9)
- `lg` - Large button (h-11)
- `icon` - Icon-only button (h-10 w-10)

**Examples**:
```tsx
import { Button } from '@/components/ui/button'

// Primary action
<Button>Create Portfolio</Button>

// Secondary action
<Button variant="secondary">Cancel</Button>

// Destructive action
<Button variant="destructive">Delete</Button>

// Small outline button
<Button variant="outline" size="sm">Edit</Button>

// Icon button
<Button variant="ghost" size="icon">
  <IconComponent />
</Button>
```

**Dark Mode**: Automatically adapts via Tailwind's dark mode classes.

---

### Card

Container component for grouped content with elevation.

**Variants**:
- `default` - Static content container
- `interactive` - Clickable card with hover effects

**Sub-components**:
- `Card` - Main container
- `CardHeader` - Header section
- `CardTitle` - Title (uses `text-heading-lg` token)
- `CardDescription` - Description text
- `CardContent` - Main content area
- `CardFooter` - Footer section

**Examples**:
```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'

// Static card
<Card>
  <CardHeader>
    <CardTitle>Portfolio Summary</CardTitle>
    <CardDescription>Your investment overview</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Total Value: $10,000</p>
  </CardContent>
</Card>

// Interactive card
<Card variant="interactive" onClick={handleClick}>
  <CardHeader>
    <CardTitle>Growth Portfolio</CardTitle>
  </CardHeader>
  <CardContent>
    <p>12 holdings • +5.2% today</p>
  </CardContent>
</Card>
```

**Dark Mode**: Uses `bg-background-secondary` token which adapts automatically.

---

### Input

Form input field with focus states and validation styling.

**Examples**:
```tsx
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Basic input
<div>
  <Label htmlFor="ticker">Stock Symbol</Label>
  <Input id="ticker" placeholder="AAPL" />
</div>

// With type
<Input type="number" placeholder="Quantity" />

// Disabled
<Input disabled placeholder="Not available" />
```

**Dark Mode**: Adapts background and border colors automatically.

---

### Label

Form label with proper accessibility attributes.

**Examples**:
```tsx
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input id="email" type="email" />
</div>
```

---

### Dialog

Modal dialog for focused interactions.

**Sub-components**:
- `Dialog` - Root component
- `DialogTrigger` - Opens dialog
- `DialogContent` - Main content container
- `DialogHeader` - Header section
- `DialogTitle` - Title (for accessibility)
- `DialogDescription` - Description (for accessibility)
- `DialogFooter` - Footer with actions
- `DialogClose` - Closes dialog

**Examples**:
```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

<Dialog>
  <DialogTrigger asChild>
    <Button>Delete Portfolio</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Are you sure?</DialogTitle>
      <DialogDescription>
        This action cannot be undone. This will permanently delete your portfolio.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button variant="destructive">Delete</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Dark Mode**: Uses `bg-background-secondary` and text tokens.

---

### Badge

Small status indicator or tag.

**Variants**:
- `default` - Primary badge (uses `bg-primary`)
- `secondary` - Gray badge
- `destructive` - Error/warning badge (uses `bg-negative`)
- `outline` - Outlined badge

**Examples**:
```tsx
import { Badge } from '@/components/ui/badge'

<Badge>Active</Badge>
<Badge variant="secondary">Pending</Badge>
<Badge variant="destructive">Error</Badge>
<Badge variant="outline">Draft</Badge>
```

---

### Separator

Visual divider between content sections.

**Orientations**:
- `horizontal` (default) - Horizontal line
- `vertical` - Vertical line

**Examples**:
```tsx
import { Separator } from '@/components/ui/separator'

// Horizontal separator
<div>
  <p>Section 1</p>
  <Separator className="my-4" />
  <p>Section 2</p>
</div>

// Vertical separator
<div className="flex h-5 items-center space-x-4">
  <span>Item 1</span>
  <Separator orientation="vertical" />
  <span>Item 2</span>
</div>
```

---

### Skeleton

Loading placeholder with pulse animation.

**Examples**:
```tsx
import { Skeleton } from '@/components/ui/skeleton'

// Loading card
<div className="space-y-2">
  <Skeleton className="h-4 w-[250px]" />
  <Skeleton className="h-4 w-[200px]" />
  <Skeleton className="h-12 w-full" />
</div>

// Loading avatar
<Skeleton className="h-12 w-12 rounded-full" />
```

---

## Design Token Integration

All components use our centralized design tokens from `tailwind.config.ts`:

**Colors**:
- `bg-primary`, `bg-primary-hover` - Brand colors
- `bg-positive`, `bg-negative` - Semantic colors
- `bg-background-primary`, `bg-background-secondary` - Backgrounds (dark mode aware)
- `text-foreground-primary`, `text-foreground-secondary` - Text (dark mode aware)

**Typography**:
- `text-heading-xl`, `text-heading-lg`, `text-heading-md` - Headings
- `text-value-primary`, `text-value-secondary` - Financial values

**Spacing**:
- `p-card-padding` (2rem/32px) - Card padding
- `gap-card-gap` (2rem/32px) - Card spacing

**Borders**:
- `rounded-card` (1rem/16px) - Cards
- `rounded-button` (0.75rem/12px) - Buttons, badges
- `rounded-input` (0.5rem/8px) - Inputs

**Shadows**:
- `shadow-card` - Default card elevation
- `shadow-card-hover` - Elevated card on hover

## Accessibility

All components follow WCAG 2.1 AA standards:

- Semantic HTML elements
- Proper ARIA attributes
- Keyboard navigation support
- Focus visible states
- Screen reader compatibility

## TypeScript Support

All components are fully typed:

```tsx
// Props are fully typed
<Button
  variant="default"  // ✓ Type-safe
  size="lg"          // ✓ Type-safe
  onClick={(e) => {  // ✓ e is typed as React.MouseEvent
    console.log(e)
  }}
>
  Click me
</Button>
```

## Next Steps

See individual component files in `frontend/src/components/ui/` for implementation details.

Refer to `docs/design-system/tokens.md` for the complete design token reference.
