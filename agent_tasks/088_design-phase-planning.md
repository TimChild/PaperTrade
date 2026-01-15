# Task 088: Visual Design & Skinning Phase - Strategic Planning

**Agent**: architect
**Priority**: HIGH
**Type**: Planning & Research
**Estimated Effort**: 2-3 hours research + planning

## Context

Zebu Phase 3c (Analytics) is complete with all core functionality working. Before deployment to first customers, we need to elevate the visual design from its current barebones state to a polished, professional appearance.

**Current State**:
- ✅ All features working: portfolios, trading, real-time prices, charts, analytics
- ✅ 489+ tests passing, 85% coverage
- ✅ Clean Architecture maintained throughout
- ⚠️ Visual design is barebones - default Tailwind styling with minimal customization
- ⚠️ No consistent design system or component primitives
- ⚠️ Significant Tailwind class duplication across components

**Technology Stack**:
- Frontend: React 18 + TypeScript + Vite
- Styling: Tailwind CSS 3.4
- UI State: Zustand
- Data Fetching: TanStack Query
- Charts: Recharts

## Objective

**Research, evaluate, and produce a detailed strategic plan** for implementing visual design and skinning across Zebu. This plan should be:
- **Maintainable**: Easy to update/tweak in the future
- **Idiomatic**: Follow React/Tailwind best practices
- **Scalable**: Support future features without massive refactoring
- **Accessible**: WCAG 2.1 AA compliance
- **Performant**: Minimal impact on bundle size and runtime performance

## Initial Plan (For Critical Evaluation)

An initial 5-step plan has been drafted:

### Step 1: Design Exploration & Direction (1-2 days)
- Create 2-3 design mockups for key screens
- Define design direction (modern/minimal vs. rich/detailed)
- Establish visual hierarchy principles
- Choose color palette + typography

### Step 2: Design System Foundation (1-2 days)
- Design tokens (colors, typography, spacing, shadows, etc.)
- Extend `tailwind.config.ts` with custom theme
- CSS variables for runtime theming
- Documentation

### Step 3: Component Primitives Refactor (2-3 days)
- Extract reusable styled components (Button, Card, Input, etc.)
- Recommended tooling: shadcn/ui + CVA (class-variance-authority)
- Create component library in `frontend/src/components/ui/`

### Step 4: Systematic Skinning (2-3 days)
- Apply design system screen-by-screen
- Replace inline Tailwind classes with primitives
- Ensure consistency and accessibility

### Step 5: Polish & Validation (1 day)
- Cross-browser testing, responsive verification
- Performance check, accessibility audit

**Recommended Tooling**:
- shadcn/ui (Tailwind + Radix UI, copy-paste components)
- CVA (class-variance-authority) for variant management
- tailwind-merge + clsx for dynamic classes

## Your Task

### 1. Critical Evaluation
Analyze the initial plan above and identify:
- **Strengths**: What parts are well-considered?
- **Weaknesses**: What's missing or potentially problematic?
- **Risks**: What could go wrong with this approach?
- **Alternatives**: Are there better approaches we should consider?

### 2. Deep Research
Investigate and compare:

**Design System Approaches**:
- shadcn/ui vs. Headless UI vs. Radix UI primitives directly
- CVA vs. tailwind-variants vs. vanilla Tailwind
- When to use component libraries vs. build from scratch
- Dark mode implementation strategies (CSS vars, Tailwind dark:, system)

**Design Token Management**:
- CSS custom properties vs. Tailwind config
- Runtime theming considerations
- Type-safe design tokens in TypeScript

**Component Architecture**:
- Atomic design methodology applicability
- Compound components pattern for complex UI
- Composition vs. configuration for variants
- Accessibility patterns (focus management, ARIA, keyboard nav)

**Performance Considerations**:
- Tailwind purging and bundle size impact
- CSS-in-JS vs. utility-first trade-offs
- Runtime vs. build-time styling decisions

**Financial UI Best Practices**:
- Color psychology for positive/negative values
- Data visualization standards
- Table design for financial data
- Mobile-first considerations for trading apps

### 3. Alternative Approaches
Propose at least one alternative implementation strategy that differs meaningfully from the initial plan. Consider:
- Different sequencing of steps
- Alternative tooling choices
- Different scope/phasing
- Novel approaches to the problem

### 4. Detailed Implementation Plan
Produce a refined plan that includes:

**For Each Phase/Step**:
- Clear objective and success criteria
- Specific deliverables (with file paths where applicable)
- Estimated effort (hours or days)
- Dependencies on other steps
- Risk mitigation strategies

**Task Breakdown**:
- Break down work into agent-sized tasks (~1-2 days each)
- Identify which tasks can run in parallel
- Specify which agent types are appropriate (architect, frontend-swe)
- Define clear acceptance criteria for each task

**Tooling Decisions**:
- Justify specific tool/library choices with pros/cons
- Consider long-term maintenance implications
- Address learning curve for future developers

**Quality Assurance**:
- How will we validate design consistency?
- What testing strategy (visual regression, accessibility, E2E)?
- How will we prevent design system drift over time?

### 5. Migration Strategy
Since we have a working app with existing components:
- How do we migrate incrementally without breaking features?
- Feature flags, parallel components, or big-bang approach?
- How do we maintain E2E tests during the transition?
- Rollback strategy if design changes cause issues?

### 6. Design Exploration Guidance
Provide specific guidance for Step 1 (Design Exploration):
- What tools should we use for mockups? (Figma, Excalidraw, AI-assisted, code prototypes?)
- Which screens are most critical to design first?
- How many variants should we explore? (2-3 seems right, but why?)
- What questions should the designs answer?
- How do we evaluate design options objectively?

## Deliverables

Create a comprehensive planning document that includes:

1. **Executive Summary** (1-2 paragraphs)
   - Recommended approach and rationale
   - Key decisions and trade-offs

2. **Critical Analysis**
   - Evaluation of initial plan
   - Identified gaps, risks, and alternatives

3. **Research Findings**
   - Tooling comparison with recommendations
   - Best practices for financial UI design
   - Performance and accessibility considerations

4. **Refined Implementation Plan**
   - Step-by-step phases with details
   - Task breakdown with agent assignments
   - Timeline estimate
   - Parallel work opportunities

5. **Migration Strategy**
   - Incremental rollout plan
   - Testing and validation approach
   - Rollback procedures

6. **Design Exploration Guide**
   - Tools and methodology
   - Evaluation criteria
   - Questions to answer through design

## Success Criteria

- [ ] Comprehensive analysis of initial plan (strengths, weaknesses, risks)
- [ ] Research-backed tooling recommendations with clear rationale
- [ ] At least one alternative approach proposed and evaluated
- [ ] Detailed implementation plan broken into agent-sized tasks
- [ ] Clear migration strategy for existing components
- [ ] Specific guidance for design exploration phase
- [ ] All recommendations consider maintainability, accessibility, and performance
- [ ] Plan is actionable - we can start executing immediately after review

## References

- Current frontend structure: `frontend/src/`
- Existing Tailwind config: `frontend/tailwind.config.ts`
- Component examples: `frontend/src/components/portfolio/`, `frontend/src/components/trade/`
- Architecture principles: `.github/copilot-instructions.md`
- Quality standards: `agent_tasks/reusable/quality-and-tooling.md`

## Notes

- Two agents will work on this task independently to produce diverse perspectives
- Focus on strategic planning and research, not implementation
- The goal is to validate/improve the initial plan, not necessarily to agree with it
- Be critical and thorough - we want to get this right before investing implementation time
- Consider that this will be shown to real users for the first time after implementation
