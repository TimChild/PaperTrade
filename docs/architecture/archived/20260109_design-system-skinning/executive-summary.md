# Executive Summary: Visual Design & Skinning Phase

## Recommended Approach

**Adopt a hybrid component system using shadcn/ui primitives with custom extensions**, implemented through an incremental, screen-by-screen migration strategy. This approach balances rapid implementation with long-term maintainability while minimizing risk to the production application.

## Key Decisions & Rationale

### 1. Component System: shadcn/ui + Custom Extensions
**Decision**: Use shadcn/ui as the foundation, not a complete replacement.

**Rationale**:
- **Copy-paste model** = Zero runtime dependencies, full code ownership
- **Tailwind-native** = Consistent with existing codebase patterns
- **Radix UI primitives** = Accessibility built-in (WCAG 2.1 AA compliant)
- **Customizable** = We control every line of code, no black boxes
- **Type-safe** = Full TypeScript integration

**Trade-off**: More initial setup than component library, but eliminates long-term dependency risks.

### 2. Design Token Strategy: Tailwind Config + CSS Variables
**Decision**: Extend Tailwind config for static tokens, CSS variables for runtime theming.

**Rationale**:
- **Static tokens** (spacing, typography, breakpoints) → Tailwind config (build-time optimization)
- **Dynamic tokens** (colors, theme switching) → CSS variables (runtime flexibility)
- **Performance**: Tailwind purges unused classes at build time
- **DX**: Type-safe tokens via TypeScript + autocomplete support

### 3. Migration Strategy: Incremental with Feature Flags
**Decision**: Migrate screen-by-screen with feature flag toggles, not big-bang.

**Rationale**:
- **Risk mitigation**: Rollback any screen independently if issues arise
- **Parallel work**: Design exploration can happen alongside component building
- **Testing continuity**: E2E tests continue running throughout migration
- **User impact**: Zero downtime, gradual rollout possible

### 4. Variant Management: CVA (class-variance-authority)
**Decision**: Use CVA for component variants, not custom abstractions.

**Rationale**:
- **Industry standard** for Tailwind variant management
- **Type-safe variants** with excellent TypeScript inference
- **Composable**: Easy to extend variants without breaking existing usage
- **Small bundle**: ~1KB, negligible performance impact

### 5. Design Exploration: Code-First Prototyping
**Decision**: Build interactive prototypes in code, not static mockups.

**Rationale**:
- **Faster iteration**: Changes are immediate, no design → code translation lag
- **Real constraints**: Discover technical limitations early
- **Component reuse**: Exploration work becomes production code
- **Team expertise**: Leverage existing React/Tailwind skills vs. learning Figma

## Timeline Estimate

**Total**: 12-15 working days across 3 agents (can run partially in parallel)

| Phase | Duration | Agent | Dependencies |
|-------|----------|-------|--------------|
| Design Exploration | 2-3 days | Architect + Frontend SWE | None |
| Design System Foundation | 2 days | Frontend SWE | Design direction finalized |
| Component Primitives | 3-4 days | Frontend SWE | Design tokens complete |
| Screen Migration (4 screens) | 4-5 days | Frontend SWE | Primitives complete |
| Polish & QA | 1-2 days | QA + Frontend SWE | Migration complete |

**Critical Path**: Design Exploration → Design System → Primitives → Migration → QA

**Parallelization Opportunity**: Component primitive building can start on confirmed designs while remaining explorations continue.

## Success Metrics

1. **Visual Consistency**: All screens use shared design tokens (0 hardcoded colors/spacing)
2. **Accessibility**: WCAG 2.1 AA compliance (automated + manual audit)
3. **Performance**: No bundle size increase >50KB, Lighthouse score ≥90
4. **Maintainability**: 80% reduction in Tailwind class duplication
5. **Test Coverage**: E2E tests pass throughout migration, no coverage loss

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Design changes break E2E tests | Feature flags allow rollback per screen |
| Bundle size bloat from Radix UI | Tree-shaking + bundle analysis gates |
| Accessibility regressions | Automated a11y testing in CI pipeline |
| Design system drift over time | Linting rules + component documentation |
| Learning curve for shadcn/ui | Document all customizations, maintain examples |

## Next Steps

1. **Immediate**: Review and approve this strategic plan
2. **Week 1**: Begin design exploration (Dashboard + Portfolio Detail screens)
3. **Week 2**: Implement design system foundation + component primitives
4. **Week 3-4**: Execute screen-by-screen migration
5. **Week 4**: QA, polish, and production deployment
