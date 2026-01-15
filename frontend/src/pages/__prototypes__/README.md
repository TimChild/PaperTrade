# Dashboard Design Prototypes

This directory contains design exploration prototypes for the Zebu dashboard redesign.

## Accessing the Prototypes

**Note**: Prototypes are only available in development mode.

1. Start the development server:

   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to the prototype routes:
   - **Variant A (Modern Minimal)**: http://localhost:5173/prototypes/dashboard-a
   - **Variant B (Data Dense)**: http://localhost:5173/prototypes/dashboard-b

## Design Variants

### Variant A: Modern Minimal

- Apple-like minimalism
- Generous whitespace and padding
- Larger typography with clear hierarchy
- Elevated cards with subtle shadows
- Spacious grid (2 columns max)
- Calm, professional aesthetic

### Variant B: Data Dense

- Bloomberg Terminal-inspired
- Compact spacing, efficient use of space
- Smaller typography, more info visible
- Subtle borders, less shadow emphasis
- Tighter grid (3-4 columns)
- Information-focused aesthetic

## Purpose

These prototypes are for design exploration and stakeholder feedback. They help us:

- Evaluate different visual directions
- Test responsive behavior across breakpoints
- Prototype with real data and interactions
- Make informed design decisions before full implementation

## Next Steps

After stakeholder review:

1. Choose final direction (A, B, or hybrid)
2. Extract design tokens (colors, spacing, typography)
3. Document decision rationale
4. Proceed to Phase 2 implementation with shadcn/ui
