# Architecture Plan: Visual Design & Skinning Phase

**Date**: January 9, 2026
**Status**: Proposed
**Priority**: HIGH
**Type**: Strategic Planning + Implementation

---

## Quick Navigation

📄 **Start Here**: [Executive Summary](./executive-summary.md)
🔍 **Critical Analysis**: [Critical Analysis of Initial Plan](./critical-analysis.md)
📚 **Research**: [Research Findings](./research-findings.md)
📋 **Implementation**: [Detailed Implementation Plan](./implementation-plan.md)
🚀 **Migration**: [Migration Strategy](./migration-strategy.md)
🎨 **Design Process**: [Design Exploration Guide](./design-exploration-guide.md)

---

## Context

PaperTrade has completed Phase 3c (Analytics) with all core functionality working:
- ✅ 489+ tests passing, 85% coverage
- ✅ All features: portfolios, trading, real-time prices, charts, analytics
- ✅ Clean Architecture maintained

However, visual design is barebones - default Tailwind styling with minimal customization. Before deployment to first customers, we need professional visual polish.

---

## Objective

Create a comprehensive strategic plan for implementing visual design and skinning across PaperTrade that is:
- **Maintainable**: Easy to update/tweak in the future
- **Idiomatic**: Follow React/Tailwind best practices
- **Scalable**: Support future features without refactoring
- **Accessible**: WCAG 2.1 AA compliance
- **Performant**: Minimal bundle size impact

---

## Recommended Approach (TL;DR)

**Adopt a hybrid component system using shadcn/ui primitives with custom extensions**, implemented through an incremental, screen-by-screen migration strategy with feature flags.

**Key Decisions**:
1. **Component System**: shadcn/ui (copy-paste model, zero dependencies)
2. **Variant Management**: CVA (class-variance-authority)
3. **Design Tokens**: Tailwind Config (static) + CSS Variables (dynamic)
4. **Migration**: Incremental with feature flags (instant rollback)
5. **Design Exploration**: Code-first prototyping (not Figma)

**Timeline**: 12-15 working days
**Bundle Impact**: +15-20KB (well within budget)
**Risk Level**: Low (incremental migration, instant rollback)

---

## Document Overview

### 1. Executive Summary
**[Read Full Document →](./executive-summary.md)**

High-level overview of recommended approach, key decisions, timeline estimate, and success metrics.

**Key Points**:
- Recommended component system (shadcn/ui)
- Design token strategy (Tailwind + CSS vars)
- Migration approach (feature flags)
- Timeline: 12-15 days
- Risk mitigation strategies

---

### 2. Critical Analysis
**[Read Full Document →](./critical-analysis.md)**

Thorough evaluation of the initial 5-step plan, identifying strengths, weaknesses, risks, and gaps.

**Key Points**:
- Initial plan strengths (logical sequencing, appropriate tooling)
- Identified weaknesses (vague design exploration, missing migration strategy)
- Risk analysis (design takes too long, E2E test breakage, bundle bloat)
- Alternative approaches considered and rejected

---

### 3. Research Findings
**[Read Full Document →](./research-findings.md)**

Deep research into design system approaches, tooling, accessibility, performance, and financial UI best practices.

**Topics Covered**:
- Component system comparison (shadcn/ui vs. Headless UI vs. Radix UI)
- Variant management (CVA vs. tailwind-variants)
- Dark mode strategies (CSS vars vs. Tailwind dark:)
- Design token management
- Financial UI best practices (color psychology, data viz, tables)
- Performance considerations (bundle size, Tailwind purging)
- Accessibility patterns (focus management, ARIA, keyboard nav)
- Testing strategy (E2E, accessibility, visual regression)

---

### 4. Implementation Plan
**[Read Full Document →](./implementation-plan.md)**

Detailed, step-by-step plan breaking work into 5 phases with 18 specific tasks, agent assignments, and quality gates.

**Phases**:
1. **Design Exploration** (3 days): Prototype 2 design variants, choose direction
2. **Design System Foundation** (2 days): Implement design tokens in Tailwind config
3. **Component Primitives** (4 days): Build 16 reusable components in 4 tiers
4. **Screen Migration** (4-5 days): Migrate 4 screens with feature flags
5. **Polish & Validation** (2 days): Cross-browser testing, a11y audit, performance

**Deliverables**: Each task has specific acceptance criteria, file paths, and validation steps.

---

### 5. Migration Strategy
**[Read Full Document →](./migration-strategy.md)**

Incremental rollout strategy using feature flags to enable safe, zero-downtime migration with instant rollback capability.

**Key Points**:
- Feature flag implementation (per-screen toggles)
- Screen-by-screen migration workflow
- E2E test continuity (maintain test ID stability)
- Rollback procedures (4 scenarios with timelines)
- Communication plan (internal team, external users)
- Parallel development strategy (bug fixes during migration)

---

### 6. Design Exploration Guide
**[Read Full Document →](./design-exploration-guide.md)**

Specific methodology for Phase 1, including tools, screen prioritization, evaluation criteria, and step-by-step prototyping process.

**Key Points**:
- Code-first prototyping (not Figma)
- Screen prioritization (Dashboard + Portfolio Detail)
- 2 design variants (Modern Minimal vs. Data Dense)
- Objective evaluation scorecard
- Questions to answer through design
- 3-day prototyping timeline with hourly breakdown

---

## Implementation Phases Summary

| Phase | Duration | Agent | Key Deliverable |
|-------|----------|-------|-----------------|
| **1. Design Exploration** | 3 days | Architect + Frontend SWE | Design direction chosen, prototypes complete |
| **2. Design System Foundation** | 2 days | Frontend SWE | Tailwind config extended, tokens documented |
| **3. Component Primitives** | 4 days | Frontend SWE | 16 components built (Button, Card, Input, etc.) |
| **4. Screen Migration** | 4-5 days | Frontend SWE | 4 screens migrated with feature flags |
| **5. Polish & Validation** | 2 days | Frontend SWE + QA | Production-ready, all tests pass |

**Total**: 15-17 days (some phases can overlap)

---

## Success Metrics

1. **Visual Consistency**: All screens use shared design tokens (0 hardcoded colors)
2. **Accessibility**: WCAG 2.1 AA compliance (automated + manual audit)
3. **Performance**: Bundle size increase <50KB, Lighthouse score ≥90
4. **Maintainability**: 80% reduction in Tailwind class duplication
5. **Test Coverage**: E2E tests pass throughout migration

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|------------|------------|
| Design exploration takes too long | Medium | Timebox to 3 days, limit to 2 variants |
| E2E tests break during migration | High | Feature flags for instant rollback per screen |
| Bundle size bloat | Low | Bundle analysis gates, tree-shaking |
| Accessibility regressions | Medium | Automated testing + manual WCAG audit |
| Design system drift (long-term) | High | ESLint rules, documentation, quarterly audits |

---

## Recommended Technology Stack

| Category | Technology | Rationale |
|----------|-----------|-----------|
| **Component System** | shadcn/ui | Copy-paste, zero dependencies, full customization |
| **Variant Management** | CVA | Type-safe, 1.3KB, industry standard |
| **Dark Mode** | Tailwind `dark:` | Simple, type-safe, build-time optimization |
| **Design Tokens** | Tailwind + CSS Vars | Hybrid: static in config, dynamic in CSS |
| **Accessibility** | Radix UI (via shadcn/ui) | WCAG 2.1 AA primitives |
| **Chart Theming** | Recharts custom config | Use design system colors |
| **Testing** | Playwright + axe-core | E2E + automated a11y |
| **Bundle Analysis** | rollup-plugin-visualizer | Monitor bundle size |

---

## Next Steps

1. **Review this architecture plan** with stakeholders
2. **Approve approach and timeline** (12-15 days)
3. **Begin Phase 1**: Design Exploration (Task 1.1)
4. **Schedule checkpoints**: After each phase for validation
5. **Execute implementation plan** following detailed tasks

---

## Questions & Feedback

For questions or suggestions about this architecture plan, please:
- Open a GitHub issue
- Comment on the PR
- Reach out to the architect agent

---

## Document Maintenance

**Last Updated**: January 9, 2026
**Next Review**: After Phase 1 completion (design direction chosen)
**Ownership**: Architect + Frontend SWE team

**Change Log**:
- 2026-01-09: Initial architecture plan created
