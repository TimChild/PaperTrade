# Visual Design & Skinning Phase - Strategic Plan

**Date**: January 9, 2026  
**Author**: Architect Agent  
**Status**: Proposed for Review  
**Related Task**: Task 088

---

## Executive Summary

**Recommended Approach**: Incremental, token-first design system using **shadcn/ui** with **CVA** for variant management, implemented in parallel with feature development.

**Key Decisions**:
1. **Adopt shadcn/ui** (not a dependency, copy-paste components) for accessible, customizable primitives
2. **CSS Custom Properties** for design tokens with Tailwind config fallbacks for maximum flexibility
3. **Incremental Migration** - new features use new system, old components migrate opportunistically
4. **Design Exploration via Code Prototyping** using isolated component development
5. **No Big-Bang Refactor** - parallel systems temporarily coexist with feature flags

**Timeline**: 8-12 days total effort, parallelizable into 3-4 agent-days with proper task distribution.

**Trade-offs Accepted**:
- Temporary style inconsistency during migration (mitigated by feature-based rollout)
- Initial learning curve for shadcn/ui patterns (offset by excellent documentation)
- Manual component copying vs. package dependency (gain: full control, lose: automatic updates)

---

## 1. Critical Analysis of Initial Plan

### 1.1 Strengths

| Aspect | Why It Works |
|--------|-------------|
| **Step 1: Design Exploration** | Correctly identifies need to establish visual direction before implementation |
| **Step 2: Design Tokens** | Token-first approach is industry best practice (Design Tokens Community Group standard) |
| **Step 3: Component Primitives** | Recognizes shadcn/ui as excellent choice for accessible, customizable components |
| **Step 5: Polish & Validation** | Includes accessibility and performance validation |
| **Recommended Tooling** | shadcn/ui + CVA is a proven, modern stack that aligns with existing Tailwind usage |

### 1.2 Weaknesses & Gaps

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| **No Migration Strategy Detail** | Risk of breaking existing tests/features | Add incremental migration plan with feature flags |
| **Design Exploration Too Vague** | Could waste time on wrong tools | Specify code prototyping approach instead of mockups |
| **No Runtime Theming Consideration** | May need to rebuild for theme changes | Add CSS custom properties strategy |
| **Sequential Phasing Assumption** | Slower delivery, blocks parallel work | Identify parallelizable tasks |
| **Missing Component Inventory** | Could duplicate work or miss components | Add comprehensive component audit |
| **No Design System Governance** | System will drift over time | Add governance and maintenance plan |
| **Underestimates Test Impact** | UI changes could break 489+ tests | Add test migration strategy |
| **No Bundle Size Analysis** | Could bloat bundle unknowingly | Add performance budget and monitoring |

### 1.3 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Breaking E2E Tests** | High | High | Feature flags + parallel components during migration |
| **Design Decision Paralysis** | Medium | High | Use constraint-based design (1 palette, 1 typography scale) |
| **Scope Creep** | High | Medium | Lock scope to existing UI, no new features |
| **Inconsistent Application** | Medium | High | Automated linting (eslint-plugin-tailwindcss) |
| **Accessibility Regression** | Low | High | Maintain test coverage, use shadcn/ui's built-in a11y |
| **Performance Degradation** | Low | Medium | Bundle size monitoring, lighthouse CI |
| **Developer Confusion** | Medium | Medium | Clear documentation + example components |

---

## 2. Research Findings

### 2.1 Design System Approaches Comparison

#### Option A: shadcn/ui (RECOMMENDED)

**What It Is**: Not a component library - it's a CLI that copies accessible, customizable components into your codebase.

**Pros**:
- ✅ Full ownership - components live in your repo, fully customizable
- ✅ Built on Radix UI primitives (best-in-class accessibility)
- ✅ Tailwind-first styling (aligns with our existing approach)
- ✅ TypeScript-native with excellent type safety
- ✅ No runtime dependency = zero bundle cost for unused components
- ✅ CVA integration for variant management
- ✅ Active community + excellent documentation
- ✅ Supports React 19 (our current version)

**Cons**:
- ❌ No automatic updates (must manually copy new versions)
- ❌ Initial setup time (~1-2 hours)
- ❌ Need to manage component versioning ourselves

**Bundle Impact**: Only pay for what you use (~5-15KB per component with Radix primitives)

**Verdict**: **Best choice** for PaperTrade - gives us control while leveraging battle-tested patterns.

#### Option B: Headless UI (Tailwind's Official Library)

**Pros**:
- ✅ Official Tailwind Labs project
- ✅ Fully headless (bring your own styles)
- ✅ Excellent accessibility
- ✅ Smaller bundle size than Radix UI

**Cons**:
- ❌ Fewer components than shadcn/ui
- ❌ More manual styling work required
- ❌ Less community momentum than Radix
- ❌ No built-in variant management

**Verdict**: Good, but **shadcn/ui offers more value** with similar philosophy.

#### Option C: Radix UI Directly

**Pros**:
- ✅ Most comprehensive primitive set
- ✅ Industry-leading accessibility
- ✅ Unstyled by design

**Cons**:
- ❌ Steeper learning curve
- ❌ Must style everything from scratch
- ❌ No Tailwind-first examples

**Verdict**: **Too low-level** for our timeline - shadcn/ui already wraps this well.

#### Option D: Build from Scratch

**Pros**:
- ✅ Ultimate control
- ✅ Minimal dependencies

**Cons**:
- ❌ 2-4 weeks of work
- ❌ Accessibility risks (easy to get wrong)
- ❌ Ongoing maintenance burden
- ❌ Not a product differentiator

**Verdict**: **Violates "Buy vs Build" principles** - authentication taught us to buy commodity features.

### 2.2 Variant Management

**CVA (class-variance-authority) - RECOMMENDED**

**Why CVA**:
- ✅ Type-safe variant composition
- ✅ Automatic className merging with cn() utility
- ✅ Default shadcn/ui choice (convention)
- ✅ Tiny bundle cost (~1KB)
- ✅ Excellent DX with IntelliSense

### 2.3 Design Token Management

**Strategy**: CSS Custom Properties + Tailwind Config (Hybrid)

| Token Type | Storage | Reasoning |
|------------|---------|-----------|
| Colors | CSS vars + Tailwind | Runtime theming + IntelliSense |
| Typography | Tailwind config | Rarely changes at runtime |
| Spacing | Tailwind defaults | Industry-standard scale |
| Shadows | Tailwind config | Static design elements |

### 2.4 Performance Considerations

**Bundle Size Budget**:
- Current: ~150KB gzipped
- Target After Design System: <220KB gzipped
- Monitoring: vite-plugin-bundle-analyzer

### 2.5 Financial UI Best Practices

**Color Psychology**:
- Positive Values: Green (#10b981) ✅ Already configured
- Negative Values: Red (#ef4444) ✅ Already configured
- Never rely on color alone - use icons/labels

**Table Design**:
- Right-align numeric columns
- Monospace fonts for decimals
- Sticky headers for long tables
- Hover states for row highlighting

---

## 3. Alternative Approaches

### Alternative A: Design Tokens First, Components Later
**Verdict**: Marginally better for exploratory projects, initial plan is acceptable.

### Alternative B: Storybook-Driven Development
**Verdict**: Not worth it for our scale - 489+ tests already provide coverage.

### Alternative C: Tailwind UI Pro (00)
**Verdict**: Consider for inspiration only, not direct implementation.

### Alternative D: Incremental Theming Without New Components
**Verdict**: Too conservative - missed opportunity for accessibility improvements.

---

## 4. Detailed Implementation Plan

### Phase 1: Foundation & Direction (2 days)

**Task 1.1: Design Exploration** (1 day)
- Create 2 design prototypes: Modern Minimal vs Rich Financial
- Prototype in /tmp/design-explorations/
- Key screens: Dashboard, Portfolio Detail

**Task 1.2: Design Tokens** (1 day)
- Extend color palette (primary, warning)
- Typography scale
- Update tailwind.config.ts + index.css

**Success Criteria**:
- [ ] Two design directions prototyped
- [ ] Design direction chosen with rationale
- [ ] All tokens defined and documented

### Phase 2: Component Primitives (3 days)

**Task 2.1: shadcn/ui Setup** (0.5 day)
- Install shadcn/ui CLI
- Configure components.json
- Set up cn() utility

**Task 2.2: Core Primitives** (1.5 days)

Components to build:
- Button (variants: primary, secondary, destructive, ghost)
- Card (variants: default, elevated, interactive)
- Input (with validation states)
- Select, Dialog, Badge, Separator, Skeleton

**Task 2.3: Documentation** (0.5 day)
- Create frontend/src/components/ui/README.md

**Task 2.4: Testing** (0.5 day)
- Unit tests for all primitives
- Accessibility testing

**Success Criteria**:
- [ ] 8-10 primitive components implemented
- [ ] All tests passing
- [ ] Documentation complete

### Phase 3: Systematic Skinning (4 days)

**Migration Strategy**: Feature-based rollout with feature flags

**Task 3.1: Dashboard** (1 day)
- Migrate PortfolioCard
- Use new Button, Dialog primitives
- Feature flag: VITE_NEW_DESIGN

**Task 3.2: Portfolio Detail** (1.5 days)
- Migrate HoldingsTable, TradeForm
- Update charts with new tokens

**Task 3.3: Analytics** (1 day)
- Migrate MetricsCards
- Update chart styling

**Task 3.4: Layout** (0.5 day)
- Consistent spacing/navigation

**Success Criteria**:
- [ ] All screens migrated
- [ ] 489+ tests still passing
- [ ] No accessibility regressions

### Phase 4: Polish & Validation (1 day)

**Task 4.1: Cross-Browser Testing** (0.25 day)
**Task 4.2: Accessibility Audit** (0.25 day) - axe DevTools
**Task 4.3: Performance Validation** (0.25 day) - Bundle size check
**Task 4.4: Documentation** (0.25 day) - Update PROGRESS.md

---

## 5. Migration Strategy

### Feature Flag Pattern

Environment variable: VITE_NEW_DESIGN=true

Component versioning:
- Component.v1.tsx - Original
- Component.v2.tsx - New design
- Component.tsx - Exports based on flag

### Rollback Strategy

1. Feature flag rollback (immediate)
2. Git revert if needed
3. Partial rollback (screen-by-screen)

---

## 6. Design Exploration Guidance

### Tools: Code Prototyping (Recommended)

**Why Code Over Mockups**:
- Faster iteration
- Real interactions
- Accurate spacing
- Can copy-paste to implementation

### Screen Priority

1. Dashboard (first impression)
2. Portfolio Detail (most complex)
3. Analytics (newest feature)

### Design Variants

**Variant 1: Modern Minimal**
- Generous whitespace
- Subtle shadows
- Minimal borders
- Sans-serif only
- Inspiration: Linear, Stripe

**Variant 2: Rich Financial**
- Higher density
- Stronger shadows
- More borders
- Serif headings
- Inspiration: Bloomberg Terminal (lighter)

### Evaluation Criteria

| Criterion | Weight |
|-----------|--------|
| Professional Appearance | 3x |
| Clarity | 3x |
| Accessibility | 2x |
| Implementation Complexity | 2x |
| Scalability | 2x |
| Mobile-Friendliness | 2x |

---

## 7. Quality Assurance

### Tools
- eslint-plugin-tailwindcss (enforce consistency)
- axe DevTools (accessibility)
- vite-plugin-bundle-analyzer (performance)

### Testing Strategy
- E2E tests after each screen migration
- Accessibility audit after Phase 3
- Manual cross-browser testing

### Prevent Design Drift
- Single source of truth: tailwind.config.ts + components/ui/
- Code review enforcement
- Linting for arbitrary values
- Monthly audits

---

## 8. Success Metrics

**Quantitative**:
- ✅ 489+ tests passing
- ✅ Bundle size <220KB
- ✅ Lighthouse accessibility ≥90
- ✅ Zero critical a11y issues

**Qualitative**:
- ✅ Professional appearance
- ✅ Visual consistency
- ✅ Improved user confidence

---

## 9. Next Steps

**Task Files to Create**:
- 089_design-exploration-and-tokens.md (Phase 1)
- 090_shadcn-ui-setup.md (Phase 2.1)
- 091_core-component-primitives.md (Phase 2.2-2.4)
- 092_dashboard-migration.md (Phase 3.1)
- 093_portfolio-detail-migration.md (Phase 3.2-3.3)
- 094_polish-and-validation.md (Phase 4)

---

## Appendices

### Appendix A: Component Inventory

| Component | Location | Priority |
|-----------|----------|----------|
| PortfolioCard | features/portfolio/ | High |
| HoldingsTable | features/portfolio/ | High |
| TradeForm | features/portfolio/ | High |
| MetricsCards | features/analytics/ | Medium |
| Charts | features/ | Medium |

**Total**: 14 components to migrate

### Appendix B: Color Palette

**Current**: positive (green), negative (red) ✅

**Add**: primary (blue), warning (amber)

### Appendix C: Typography Scale

| Element | Class | Size | Weight |
|---------|-------|------|--------|
| H1 | text-4xl | 36px | 700 |
| H2 | text-2xl | 24px | 600 |
| Body | text-base | 16px | 400 |
| Numbers | font-mono | - | 500 |

---

**Document Version**: 1.0  
**Date**: 2026-01-09  
**Status**: Ready for Review

---

**End of Strategic Plan**
