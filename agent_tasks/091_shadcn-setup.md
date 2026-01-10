# Task 091: shadcn/ui Setup & Core Primitive Components

**Agent**: frontend-swe
**Priority**: HIGH
**Type**: Component Infrastructure
**Estimated Effort**: 1-2 days
**Phase**: Phase 3 - Component Primitives

## Context

Phase 2 (Design System Foundation) is complete:
- ✅ PR #109 merged - Tailwind config extended with design tokens
- ✅ CSS variables for light/dark mode theming
- ✅ TypeScript types for type-safe token usage
- ✅ Token documentation in `docs/design-system/tokens.md`

**Current State**:
- Design tokens are centralized and ready to use
- No primitive component library yet
- Components still use inline Tailwind classes inconsistently
- No shadcn/ui infrastructure installed

**Strategic Plan**: `architecture_plans/20260109_design-system-skinning/`
**This task is Phase 3, Tasks 2.2-2.3 (combined)**

## Objective

**Set up shadcn/ui infrastructure** and implement the first set of primitive components that will form the foundation of our design system. These components will use the design tokens from Phase 2 and provide a consistent, accessible UI across the application.

## Requirements

### 1. shadcn/ui Installation & Configuration

Install and configure shadcn/ui CLI with:
- TypeScript support
- Tailwind CSS integration
- CSS variables for theming
- Path aliases configured (@/components/ui/*)

### 2. Core Utility: cn() Helper

Implement the class names utility helper for intelligent Tailwind class merging:
- Install dependencies: `tailwind-merge` and `clsx`
- Create `frontend/src/lib/utils.ts` with `cn()` function
- Export for use across all components

### 3. Primitive Components Installation

Install these shadcn/ui components via CLI:
- **Button** - Primary UI actions
- **Card** - Content containers (portfolios, holdings)
- **Input** - Form fields (ticker, quantity, etc.)
- **Label** - Form labels
- **Dialog** - Modals (confirm delete, create portfolio)
- **Badge** - Status indicators
- **Separator** - Visual dividers
- **Skeleton** - Loading states

### 4. Button Variant Customization

Customize Button component to match our design tokens:
- Variants: `default` (primary), `secondary`, `outline`, `ghost`, `destructive`
- Sizes: `default`, `sm`, `lg`, `icon`
- Apply our custom tokens: `bg-primary`, `rounded-button`, `shadow-card-hover`
- Remove default shadcn colors, use our palette

### 5. Card Variant Customization

Customize Card component for portfolio displays:
- Base: `rounded-card`, `shadow-card`, `p-card-padding`
- Interactive variant: `hover:shadow-card-hover`, `cursor-pointer`
- Use our `bg-background-secondary` token for theming support

### 6. Component Documentation

Update `docs/design-system/` with:
- Component usage guide
- Variant examples
- Code snippets for common patterns
- Dark mode behavior notes

## Implementation Guidance

### Step 1: Install shadcn/ui CLI

```bash
cd frontend

# Initialize shadcn/ui
npx shadcn@latest init

# When prompted:
# - TypeScript: Yes
# - Style: Default
# - Base color: Neutral (we'll override with our tokens)
# - CSS variables: Yes (critical for dark mode)
# - Tailwind config: frontend/tailwind.config.ts
# - Components: frontend/src/components/ui
# - Utils: frontend/src/lib/utils.ts
# - React Server Components: No
# - Import alias: @/*
```

This creates:
- `components.json` - shadcn configuration
- `frontend/src/lib/utils.ts` - cn() helper function
- Path alias configuration in `tsconfig.json`

### Step 2: Install Core Components

```bash
cd frontend

# Install primitive components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add dialog
npx shadcn@latest add badge
npx shadcn@latest add separator
npx shadcn@latest add skeleton
```

Each command copies component source to `frontend/src/components/ui/`.

### Step 3: Customize Button Component

Update `frontend/src/components/ui/button.tsx` to use our design tokens:

```typescript
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-button text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-white hover:bg-primary-hover shadow-card hover:shadow-card-hover",
        secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700",
        outline: "border border-gray-300 bg-transparent hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800",
        ghost: "hover:bg-gray-100 dark:hover:bg-gray-800",
        destructive: "bg-negative text-white hover:bg-negative-dark",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-button px-3",
        lg: "h-11 rounded-button px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

### Step 4: Customize Card Component

Update `frontend/src/components/ui/card.tsx`:

```typescript
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const cardVariants = cva(
  "rounded-card bg-background-secondary text-foreground-primary shadow-card",
  {
    variants: {
      variant: {
        default: "",
        interactive: "transition-shadow hover:shadow-card-hover cursor-pointer",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, className }))}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("text-heading-lg", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-foreground-secondary", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, cardVariants }
```

### Step 5: Component Documentation

Create `docs/design-system/components.md`:

```markdown
# Design System Components

## Button

### Variants
- `default` - Primary actions (bg-primary)
- `secondary` - Secondary actions (gray background)
- `outline` - Tertiary actions (border only)
- `ghost` - Low emphasis actions (no background)
- `destructive` - Destructive actions (bg-negative)

### Examples
\`\`\`tsx
import { Button } from '@/components/ui/button'

<Button>Create Portfolio</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="destructive">Delete</Button>
\`\`\`

## Card

### Variants
- `default` - Static content container
- `interactive` - Clickable card (hover effects)

### Examples
\`\`\`tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

<Card variant="interactive" onClick={handleClick}>
  <CardHeader>
    <CardTitle>Portfolio Name</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Total Value: $10,000</p>
  </CardContent>
</Card>
\`\`\`
```

## Success Criteria

- [ ] shadcn/ui CLI installed and configured
  - [ ] `components.json` created
  - [ ] Path aliases working (@/components/ui/*)
  - [ ] `frontend/src/lib/utils.ts` with cn() function
- [ ] 8 primitive components installed
  - [ ] Button (customized with our tokens)
  - [ ] Card (customized with our tokens)
  - [ ] Input
  - [ ] Label
  - [ ] Dialog
  - [ ] Badge
  - [ ] Separator
  - [ ] Skeleton
- [ ] Button component customized
  - [ ] Uses `bg-primary`, `rounded-button` tokens
  - [ ] 5 variants: default, secondary, outline, ghost, destructive
  - [ ] 4 sizes: default, sm, lg, icon
  - [ ] Dark mode support via CSS variables
- [ ] Card component customized
  - [ ] Uses `rounded-card`, `shadow-card` tokens
  - [ ] Interactive variant with hover effects
  - [ ] Dark mode support
- [ ] Component documentation created
  - [ ] Usage examples
  - [ ] Variant showcase
  - [ ] Code snippets
- [ ] All existing tests pass
- [ ] TypeScript strict mode passes
- [ ] No breaking changes to existing components

## Quality Assurance

### Testing
```bash
# Run frontend tests
task test:frontend

# Type check
cd frontend && npm run type-check

# Lint
task lint:frontend

# Full quality check
task quality:frontend
```

### Manual Verification
- Import and test Button in a simple component
- Verify variants render correctly
- Test dark mode toggle (add `className="dark"` to body)
- Check Tailwind autocomplete suggests our custom tokens

### Expected File Structure
```
frontend/
├── components.json                  # shadcn config (new)
├── src/
│   ├── components/
│   │   └── ui/                      # shadcn components (new)
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       ├── dialog.tsx
│   │       ├── badge.tsx
│   │       ├── separator.tsx
│   │       └── skeleton.tsx
│   └── lib/
│       └── utils.ts                 # cn() helper (new)
├── tsconfig.json                    # Updated with path aliases
└── package.json                     # Updated with new dependencies
```

## References

- shadcn/ui docs: https://ui.shadcn.com/docs/installation/vite
- Design tokens: `docs/design-system/tokens.md`
- Tailwind config: `frontend/tailwind.config.ts`
- Implementation plan: `architecture_plans/20260109_design-system-skinning/implementation-plan.md`

## Notes

**Why customize shadcn components?**
shadcn components come with default Tailwind colors (blue-600, etc.). We replace these with our design tokens (primary, positive, negative) to ensure consistency with our design system.

**tsconfig.json path alias:**
shadcn requires `@/*` path alias. Ensure `tsconfig.json` has:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

**Vite config path alias:**
Also add to `vite.config.ts`:
```typescript
import path from "path"

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

## Next Steps

After this task:
- **Task 092**: Refactor existing components to use primitives (PortfolioCard, CreatePortfolioForm)
- **Task 093**: Implement dark mode toggle component with persistence
- **Task 094**: Systematic screen migration (Dashboard first)
