# React Patterns Audit & Refactoring

**Status**: Backlog
**Priority**: Low (Tech Debt / Quality)
**Estimated Effort**: 2-3 days spread across multiple PRs
**Created**: 2026-01-08

## Context

During PR #90, we identified and fixed an anti-pattern where `useEffect` was used to synchronize props to local state. This required ESLint suppressions and caused race conditions in E2E tests. The proper solution was using React's `key` prop pattern to remount components with fresh state.

This audit will systematically review the codebase for similar anti-patterns and refactor to idiomatic React patterns.

## Objectives

1. **Remove all unnecessary ESLint suppressions** - Each suppression should be justified or eliminated
2. **Eliminate useEffect anti-patterns** - Particularly setState-in-effect
3. **Apply proper React patterns** - key prop, controlled components, derived state
4. **Improve test reliability** - Reduce race conditions and timing dependencies
5. **Document patterns** - Create examples for future reference

## Phase 1: Discovery & Assessment

### Tasks

**1. Audit ESLint Suppressions**
```bash
# Find all React hooks suppressions
grep -r "eslint-disable.*react-hooks" frontend/src/

# Find all exhaustive-deps suppressions
grep -r "exhaustive-deps" frontend/src/
```

For each suppression:
- Document why it exists
- Determine if it's necessary
- Identify refactoring opportunities

**2. Identify useEffect Patterns**
Search for these anti-patterns:

```tsx
// Anti-pattern 1: setState in effect
useEffect(() => {
  if (someProp) {
    setState(someProp)
  }
}, [someProp])

// Anti-pattern 2: Effect with no cleanup/subscription
useEffect(() => {
  doSomething()
}, [dependency])

// Anti-pattern 3: Missing dependencies
useEffect(() => {
  // Uses values not in dependency array
}, [])
```

**3. Review Component State Patterns**

Audit for:
- Components with complex state logic that should use `useReducer`
- Props that could be derived instead of stored in state
- Parent-child state synchronization issues
- Form components that might benefit from libraries (React Hook Form)

### Deliverable

Create `docs/technical/react-patterns-audit-findings.md` with:
- List of all ESLint suppressions with justification status
- Categorized list of anti-patterns found
- Priority ranking for refactoring
- Estimated effort per fix

## Phase 2: High-Priority Refactoring

### Criteria for High Priority

1. **ESLint suppressions without clear justification**
2. **setState-in-effect patterns** (performance + test reliability issues)
3. **Race conditions in tests** (flaky E2E/integration tests)
4. **Components that re-render excessively** (measurable performance impact)

### Refactoring Patterns

#### Pattern 1: Key Prop for Component Reset

**When to use**: Need to "reset" a component to initial state

**Before**:
```tsx
function Parent() {
  const [resetData, setResetData] = useState(null)

  return <Form resetData={resetData} />
}

function Form({ resetData }) {
  const [value, setValue] = useState('')

  useEffect(() => {
    if (resetData) {
      setValue(resetData.value)  // ❌ Anti-pattern
    }
  }, [resetData])
}
```

**After**:
```tsx
function Parent() {
  const [formKey, setFormKey] = useState(0)
  const [initialValue, setInitialValue] = useState('')

  const handleReset = (newValue) => {
    setInitialValue(newValue)
    setFormKey(prev => prev + 1)  // ✅ Trigger remount
  }

  return <Form key={formKey} initialValue={initialValue} />
}

function Form({ initialValue }) {
  const [value, setValue] = useState(initialValue)  // ✅ Initialize from prop
  // No useEffect needed
}
```

#### Pattern 2: Fully Controlled Components

**When to use**: Parent needs continuous control over child state

**Before**:
```tsx
function Parent() {
  return <Input onChange={handleChange} />
}

function Input({ onChange }) {
  const [value, setValue] = useState('')

  const handleChange = (e) => {
    setValue(e.target.value)
    onChange?.(e.target.value)  // ❌ Duplicate state
  }
}
```

**After**:
```tsx
function Parent() {
  const [value, setValue] = useState('')
  return <Input value={value} onChange={setValue} />  // ✅ Single source of truth
}

function Input({ value, onChange }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
```

#### Pattern 3: Derived State with useMemo

**When to use**: Value can be computed from props/state

**Before**:
```tsx
function Component({ items, filter }) {
  const [filteredItems, setFilteredItems] = useState([])

  useEffect(() => {
    setFilteredItems(items.filter(filter))  // ❌ Unnecessary state
  }, [items, filter])
}
```

**After**:
```tsx
function Component({ items, filter }) {
  const filteredItems = useMemo(
    () => items.filter(filter),  // ✅ Derived, not stored
    [items, filter]
  )
}
```

#### Pattern 4: useReducer for Complex State

**When to use**: Multiple related state values, complex update logic

**Before**:
```tsx
function Form() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Many setState calls scattered throughout
}
```

**After**:
```tsx
function Form() {
  const [state, dispatch] = useReducer(formReducer, initialState)

  // Single dispatch for all state updates
  // Centralized update logic
}
```

### Testing Strategy

For each refactoring:

1. **Unit tests pass** - Existing tests should still pass or require minimal updates
2. **E2E tests pass** - No flaky behavior introduced
3. **Manual testing** - Verify UX is identical
4. **Performance check** - React DevTools Profiler to verify no regression

### Deliverable

- PRs for each high-priority refactoring
- Updated tests where necessary
- Progress documentation in `agent_progress_docs/`

## Phase 3: Medium-Priority Improvements

### Opportunities

1. **Form State Management**
   - Evaluate React Hook Form or Formik for complex forms
   - Trade-off: Bundle size vs. built-in validation/handling

2. **Error Boundaries**
   - Audit error boundary placement
   - Ensure all async components are wrapped
   - Add fallback UI for graceful degradation

3. **Code Splitting**
   - Identify large components for lazy loading
   - Audit bundle size with `vite-bundle-visualizer`
   - Split routes and heavy features

4. **Prop Drilling**
   - Identify deeply nested prop passing
   - Consider Context API or composition patterns
   - Avoid premature optimization with global state

### Deliverable

- Technical proposal for each improvement
- Cost/benefit analysis
- Implementation plan if approved

## Phase 4: Documentation & Prevention

### Update Documentation

1. **Frontend Style Guide** - Add to `docs/frontend-style-guide.md`
   - Common patterns and their use cases
   - Anti-patterns to avoid
   - Decision tree for choosing patterns

2. **Code Review Checklist** - Add React patterns section
   - ESLint suppressions require justification
   - useEffect must have cleanup or external sync
   - State should be minimal and derived when possible

3. **Example Components** - Create reference implementations
   - `examples/FormComponent.tsx` - Form with validation
   - `examples/DataFetchingComponent.tsx` - TanStack Query patterns
   - `examples/ControlledComponent.tsx` - Parent/child state

### Prevent Future Anti-Patterns

1. **ESLint Configuration**
   - Review enabled rules
   - Consider stricter rules for hooks
   - Custom rules if needed

2. **PR Template Updates**
   - Add React patterns checklist
   - Require justification for suppressions

3. **Agent Instructions**
   - Already updated in `.github/agents/frontend-swe.md`
   - Monitor agent PR quality
   - Iterate on instructions as needed

### Deliverable

- Updated documentation
- PR template changes
- Post-mortem analysis of patterns found

## Success Criteria

### Quantitative

- [ ] Zero unjustified ESLint suppressions in `frontend/src/`
- [ ] <5 useEffect hooks with setState (down from current count)
- [ ] E2E test flakiness <2% (measure over 50 runs)
- [ ] No React DevTools warnings in console (development)
- [ ] Bundle size maintained or reduced

### Qualitative

- [ ] Code is more maintainable (fewer WTF moments in reviews)
- [ ] New developers can understand component patterns
- [ ] Tests are more reliable and faster
- [ ] Components follow consistent patterns

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Comprehensive test coverage before refactoring |
| Introducing new bugs | Medium | Small, focused PRs with thorough testing |
| Team velocity slowdown | Low | Spread work over time, low priority |
| Bikeshedding on patterns | Low | Reference React docs and industry best practices |
| Regression in UX | Medium | Manual testing + E2E tests + stakeholder review |

## Resources

- [React Docs: You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- [React Docs: Removing Effect Dependencies](https://react.dev/learn/removing-effect-dependencies)
- [Kent C. Dodds: Application State Management](https://kentcdodds.com/blog/application-state-management-with-react)
- [TkDodo: React Query Best Practices](https://tkdodo.eu/blog/practical-react-query)

## Related Documents

- `.github/agents/frontend-swe.md` - Agent instructions with React patterns guidance
- `docs/TESTING_CONVENTIONS.md` - Testing best practices
- `agent_progress_docs/2026-01-08_*_react-patterns-refactor.md` - Implementation progress

## Task Breakdown for Orchestrator

When ready to execute this audit:

1. **Create initial assessment task** → assign to `frontend-swe` agent
   - Run discovery scripts
   - Document findings
   - Prioritize refactoring targets

2. **Create refactoring tasks** → assign to `frontend-swe` agent (one PR each)
   - Fix specific anti-patterns
   - Include tests
   - Document changes

3. **Create documentation task** → assign to `frontend-swe` or `quality-infra` agent
   - Update style guide
   - Create examples
   - Update PR templates

4. **Review and iterate** → orchestrator validates quality
   - Check success criteria
   - Gather feedback
   - Decide on next steps

---

**Notes**: This is a quality improvement initiative, not a critical bug fix. Schedule during slower development periods or allocate 10-20% of sprint capacity to tech debt work.
