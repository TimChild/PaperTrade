# Design Exploration Guide

## Purpose

This guide provides specific methodology for Phase 1 (Design Exploration & Direction) to ensure we create effective, user-centered designs efficiently without getting stuck in analysis paralysis.

---

## Design Exploration Methodology

### Recommended Approach: **Code-First Prototyping**

**Why code prototypes instead of Figma/Sketch?**

| Factor | Code Prototypes | Figma Mockups | Verdict |
|--------|----------------|---------------|---------|
| **Speed** | Fast (use existing components) | Slower (design from scratch) | ✅ Code |
| **Real data** | Uses actual API (real portfolios) | Mock data (feels fake) | ✅ Code |
| **Interactivity** | Fully functional (click, navigate) | Static or limited prototypes | ✅ Code |
| **Technical feasibility** | Validated immediately | May design impossible things | ✅ Code |
| **Team expertise** | Team knows React/Tailwind | No dedicated designer | ✅ Code |
| **Handoff** | No handoff (code IS deliverable) | Design → code translation delay | ✅ Code |
| **Iteration speed** | Instant (change code, refresh) | Slower (update mockup, export) | ✅ Code |

**Decision**: Use code-first prototyping for PaperTrade design exploration.

---

## Tools & Setup

### Primary Tool: React + Tailwind (Code Prototypes)

**Setup**:
```bash
# Create prototype directory
mkdir -p frontend/src/pages/__prototypes__

# Create prototype components
touch frontend/src/pages/__prototypes__/DashboardVariantA.tsx
touch frontend/src/pages/__prototypes__/DashboardVariantB.tsx
```

**Add prototype routes**:
```typescript
// frontend/src/App.tsx
{import.meta.env.DEV && (
  <>
    <Route path="/prototypes/dashboard-a" element={<DashboardVariantA />} />
    <Route path="/prototypes/dashboard-b" element={<DashboardVariantB />} />
  </>
)}
```

**Benefits**:
- Only visible in development mode
- Full access to real data (portfolios, prices)
- Hot reload for instant iteration

---

### Secondary Tool: AI-Assisted Mockups (Optional)

If you want quick visual mockups before coding:

**Option 1: ChatGPT + DALL-E**
- Describe desired design in words
- Generate visual mockup
- Use as inspiration for code prototype

**Option 2: v0.dev (Vercel)**
- AI generates React + Tailwind components
- Copy/paste into prototype
- Refine from there

**Option 3: Excalidraw (Wireframes)**
- Quick hand-drawn wireframes
- Lo-fi sketches for layout exploration
- Then implement in code

**Recommendation**: Skip AI mockups for MVP (code prototypes are faster). Use if stakeholders need visuals before approving implementation.

---

## Screen Prioritization

### Which Screens to Design First?

**Criteria**:
1. **User visibility**: Which screens do users see most?
2. **Complexity**: Which screens have most design challenges?
3. **Representative**: Which screens showcase full design system?

### Recommended Screens (2 screens for prototyping)

#### Screen 1: **Dashboard** (Highest Priority)

**Why Dashboard first?**
- First screen users see (highest visibility)
- Sets design direction for entire app
- Contains key components: cards, buttons, layout
- Relatively simple (good starting point)

**What to explore**:
- Portfolio card design (size, spacing, information density)
- Page layout (header, grid, spacing)
- Empty state design
- Call-to-action prominence (Create Portfolio button)

**Design variants**:
- **Variant A**: Modern minimal (lots of whitespace, fewer cards per row)
- **Variant B**: Data dense (more cards visible, compact spacing)

---

#### Screen 2: **Portfolio Detail** (Second Priority)

**Why Portfolio Detail second?**
- Core functionality (users spend most time here)
- Contains most complex components (table, chart, form)
- Representative of entire design system
- High design challenge (lots of data to display)

**What to explore**:
- Holdings table design (columns, styling, responsiveness)
- Chart integration (colors, theming, size)
- Trade form design (form layout, validation, button prominence)
- Transaction list design (table vs. list, density)

**Design variants**:
- Apply chosen direction from Dashboard
- Focus on data visualization (table, charts)

---

### Screens to Skip (For Now)

- **Portfolio Analytics**: Can use same patterns as Portfolio Detail (charts, metrics)
- **Debug Page**: Low priority, minimal design needed
- **Trade Page** (if separate): Can reuse Trade Form from Portfolio Detail

**Rationale**: 2 screens are enough to establish design direction. Other screens will follow the same patterns.

---

## Design Variants: How Many?

### Recommended: **2 Variants**

**Why 2, not 3+?**
- 2 variants force clear comparison (A vs. B)
- 3+ variants create decision fatigue
- Empirical research: 2 options yield faster, better decisions than 3+ (Paradox of Choice)

**What to vary between variants**:

| Design Aspect | Variant A (Modern Minimal) | Variant B (Data Dense) |
|---------------|---------------------------|------------------------|
| **Spacing** | Generous (p-8, gap-6) | Compact (p-4, gap-3) |
| **Card Size** | Larger (min-h-48) | Smaller (min-h-32) |
| **Typography** | Larger (text-2xl headings) | Smaller (text-xl headings) |
| **Cards per Row** | 2-3 (more whitespace) | 3-4 (less whitespace) |
| **Info Density** | Show only critical data | Show more data per card |
| **Visual Weight** | Lighter borders, shadows | Heavier borders, shadows |

**Goal**: Create clear contrast between variants (not subtle differences).

---

## Evaluation Criteria

### How to Evaluate Designs Objectively?

**Problem**: Design decisions are often subjective ("I like this better").

**Solution**: Define objective criteria before creating designs.

### Evaluation Scorecard

Rate each design on a scale of 1-5 for each criterion:

| Criterion | Weight | Variant A Score | Variant B Score | Explanation |
|-----------|--------|-----------------|-----------------|-------------|
| **Readability** | 3x | ? | ? | Can user quickly find critical info (portfolio value, daily change)? |
| **Data Density** | 2x | ? | ? | How much info visible without scrolling? |
| **Visual Hierarchy** | 3x | ? | ? | Is most important info most prominent? |
| **Aesthetic Appeal** | 1x | ? | ? | Does it feel professional and polished? |
| **Consistency** | 2x | ? | ? | Can this style scale to all screens? |
| **Accessibility** | 3x | ? | ? | Sufficient color contrast? Clear focus states? |
| **Mobile Friendly** | 2x | ? | ? | Works on small screens (375px width)? |

**Weighted Total**: Sum of (Score × Weight) for each variant

**Decision**: Choose variant with higher weighted total (or hybrid approach).

---

### Specific Questions to Answer Through Design

#### Dashboard Questions

1. **Information Architecture**:
   - Should portfolios be cards or list items?
   - How many portfolios visible without scrolling? (3? 6? 9?)
   - Where to place Create Portfolio button? (header, empty state, both?)

2. **Data Presentation**:
   - What info on portfolio card? (name, value, daily change, cash balance, holdings count?)
   - Prominent metric: Total Value or Daily Change?
   - Show percentage gain/loss or just dollar amount?

3. **Visual Design**:
   - Card elevation: flat, subtle shadow, or prominent shadow?
   - Card hover state: scale, shadow, border color?
   - Empty state: icon, illustration, or text only?

4. **Responsive Design**:
   - Mobile: 1 column, 2 columns?
   - Tablet: 2 columns, 3 columns?
   - Desktop: 3 columns, 4 columns?

---

#### Portfolio Detail Questions

1. **Layout**:
   - Holdings table: full width or in card?
   - Chart placement: above table, side-by-side, separate tab?
   - Trade form: modal, slide-over, or inline?

2. **Table Design**:
   - Columns: Symbol, Quantity, Avg Cost, Current Price, Market Value, Gain/Loss, Actions?
   - Table header: sticky (stays visible when scrolling)?
   - Row hover: highlight row, show action buttons?

3. **Chart Design**:
   - Chart height: 300px, 400px, full-height?
   - Chart colors: use design system colors or default Recharts?
   - Tooltip style: match design system or default?

4. **Form Design**:
   - Trade form: compact (all fields visible) or wizard (step-by-step)?
   - Submit button: always visible (sticky) or in form?
   - Validation errors: inline or summary at top?

---

## Prototyping Process (Step-by-Step)

### Day 1: Dashboard Prototyping

#### Step 1: Setup (30 minutes)
```bash
# Create prototype files
touch frontend/src/pages/__prototypes__/DashboardVariantA.tsx
touch frontend/src/pages/__prototypes__/DashboardVariantB.tsx

# Add routes (development only)
# Update App.tsx with prototype routes
```

#### Step 2: Build Variant A - Modern Minimal (2 hours)
- Copy existing Dashboard.tsx as starting point
- Increase spacing (p-8 instead of p-4)
- Larger cards (min-h-48)
- Fewer cards per row (max-w-md cards)
- Generous whitespace
- Subtle shadows

**Example**:
```typescript
<div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
  <Link className="block rounded-lg border bg-white p-8 shadow-sm hover:shadow-md">
    <h3 className="text-2xl font-semibold">{portfolio.name}</h3>
    <p className="mt-4 text-3xl font-bold">{formatCurrency(portfolio.totalValue)}</p>
    <p className="mt-2 text-sm text-gray-600">Daily Change</p>
    <p className="text-lg font-medium text-positive">+$125.00</p>
  </Link>
</div>
```

#### Step 3: Build Variant B - Data Dense (2 hours)
- Copy existing Dashboard.tsx
- Reduce spacing (p-4 instead of p-6)
- Smaller cards (min-h-32)
- More cards per row (grid-cols-4)
- Less whitespace
- More info per card (cash balance, holdings count)

**Example**:
```typescript
<div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
  <Link className="block rounded-lg border bg-white p-4 shadow-sm hover:shadow-md">
    <h3 className="text-lg font-semibold">{portfolio.name}</h3>
    <div className="mt-2 flex justify-between">
      <div>
        <p className="text-xs text-gray-600">Value</p>
        <p className="text-xl font-bold">{formatCurrency(portfolio.totalValue)}</p>
      </div>
      <div className="text-right">
        <p className="text-xs text-gray-600">Daily</p>
        <p className="text-sm font-medium text-positive">+$125</p>
      </div>
    </div>
    <p className="mt-2 text-xs text-gray-600">Cash: {formatCurrency(portfolio.cashBalance)}</p>
  </Link>
</div>
```

#### Step 4: Screenshot & Compare (30 minutes)
- Take screenshots of both variants (full page)
- Screenshot at different widths (375px, 768px, 1024px, 1440px)
- Place side-by-side for comparison
- Share with stakeholders (if applicable)

#### Step 5: Evaluate & Choose (1 hour)
- Fill out evaluation scorecard
- Discuss with team (if applicable)
- Choose winner (or hybrid approach)
- Document decision in `design-decisions.md`

**Total Day 1**: ~6 hours

---

### Day 2: Portfolio Detail Prototyping

#### Step 1: Apply Chosen Direction (3 hours)
- Take winner from Dashboard (or hybrid)
- Apply same spacing, typography, card style to Portfolio Detail
- Focus on layout (table, chart, form placement)

#### Step 2: Table Design (2 hours)
- Experiment with column widths
- Try different header styles (sticky, bold, background color)
- Test zebra striping vs. row hover
- Ensure mobile responsiveness (horizontal scroll or hide columns)

#### Step 3: Chart Integration (1 hour)
- Configure Recharts with design system colors
- Experiment with chart height
- Test tooltip styling

**Total Day 2**: ~6 hours

---

### Day 3: Refinement & Documentation

#### Step 1: Mobile Testing (1 hour)
- Test both prototypes at 375px width
- Ensure all info accessible (no horizontal scroll for critical content)
- Test interactions (tapping cards, buttons)

#### Step 2: Extract Design Tokens (2 hours)
- Document colors (HSL values)
- Document typography scale (font sizes, weights)
- Document spacing scale (padding, margin)
- Document shadows, borders, radii

#### Step 3: Document Decision (1 hour)
- Write `design-decisions.md`
- Include screenshots
- Explain rationale for chosen direction
- List open questions (if any)

**Total Day 3**: ~4 hours

---

## Stakeholder Feedback

### When to Get Feedback?

**Checkpoint 1**: After Day 1 (Dashboard variants ready)
- Show both variants side-by-side
- Get initial reactions
- Don't commit to design yet (iterate if needed)

**Checkpoint 2**: After Day 2 (Portfolio Detail ready)
- Show full design direction applied to 2 screens
- Get final approval before proceeding to implementation

### How to Present Designs?

**Option 1: Live Demo** (Recommended)
- Walk through prototypes in browser
- Show interactivity (clicking, navigating)
- Explain rationale for design choices

**Option 2: Screenshots + Document**
- Create slides with screenshots
- Annotate with design rationale
- Share via email/Slack for async feedback

**Option 3: Loom Video**
- Record screen walkthrough
- Narrate design decisions
- Share link for async review

---

## Common Pitfalls to Avoid

### Pitfall 1: Perfectionism
**Problem**: Spending too long tweaking minor details.

**Solution**: Timebox each variant (2 hours max). Designs don't need to be pixel-perfect at this stage.

---

### Pitfall 2: Analysis Paralysis
**Problem**: Can't decide between variants, keep iterating.

**Solution**: Use evaluation scorecard. If scores are tied, flip a coin (seriously). Indecision is worse than imperfect decision.

---

### Pitfall 3: Scope Creep
**Problem**: Start designing every screen, not just 2.

**Solution**: Stick to Dashboard + Portfolio Detail. Other screens will follow the same patterns.

---

### Pitfall 4: Over-Designing
**Problem**: Adding unnecessary features (animations, easter eggs, complex interactions).

**Solution**: Focus on core user tasks. Polish comes later (Phase 5).

---

### Pitfall 5: Ignoring Mobile
**Problem**: Designs look great on desktop, terrible on mobile.

**Solution**: Test every design at 375px width. Mobile-first approach.

---

## Design Direction Examples

### Example A: Modern Minimal (Airbnb-inspired)

**Characteristics**:
- Lots of whitespace
- Larger typography (text-2xl, text-3xl)
- Subtle shadows (shadow-sm, shadow-md)
- Rounded corners (rounded-lg, rounded-xl)
- Minimal borders (border-gray-200)
- Generous padding (p-8, p-10)

**Best for**:
- Users who value clarity over density
- Portfolios with few holdings (< 10)
- Desktop-first users

**Trade-offs**:
- Less data visible without scrolling
- More scrolling required

---

### Example B: Data Dense (Bloomberg Terminal-inspired)

**Characteristics**:
- Compact spacing (p-4, gap-3)
- Smaller typography (text-base, text-lg)
- Minimal whitespace
- More borders (borders separate sections)
- Tables over cards (more data per square inch)

**Best for**:
- Power users who want all info visible
- Portfolios with many holdings (10+)
- Desktop users with large monitors

**Trade-offs**:
- Can feel cramped
- Harder to scan quickly

---

## Decision Template

After evaluation, document decision:

```markdown
## Design Direction Decision

**Chosen Direction**: [Variant A / Variant B / Hybrid]

**Rationale**:
- [Reason 1]
- [Reason 2]
- [Reason 3]

**Scorecard Results**:
| Criterion | Variant A | Variant B | Winner |
|-----------|-----------|-----------|--------|
| Readability | 4 | 3 | A |
| Data Density | 3 | 5 | B |
| Visual Hierarchy | 5 | 3 | A |
| ... | ... | ... | ... |
| **Total** | **42** | **38** | **A** |

**Key Design Decisions**:
- Card spacing: 32px (gap-8)
- Typography scale: text-xl for card titles, text-3xl for primary values
- Cards per row: 3 on desktop (lg:grid-cols-3)
- Shadow: subtle (shadow-sm on default, shadow-md on hover)

**Next Steps**:
1. Extract design tokens (colors, typography, spacing)
2. Implement design system foundation (Phase 2)
3. Build component primitives (Phase 3)
```

---

## Summary

**Methodology**: Code-first prototyping
**Tools**: React + Tailwind (primary), optional AI mockups
**Screens**: Dashboard (priority 1), Portfolio Detail (priority 2)
**Variants**: 2 (Modern Minimal vs. Data Dense)
**Evaluation**: Objective scorecard with weighted criteria
**Timeline**: 3 days (Day 1: Dashboard variants, Day 2: Portfolio Detail, Day 3: Refinement)
**Checkpoints**: After Day 1 (initial feedback), After Day 2 (final approval)

**Key Principle**: Progress over perfection. Timebox exploration, use data to decide, move forward.
