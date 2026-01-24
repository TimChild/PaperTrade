# Task 167: Highlight New Transactions

**Agent**: frontend-swe  
**Priority**: HIGH (UX Polish - Phase 4a)  
**Estimated Effort**: 30 minutes

## Objective

Add a brief pulse animation to newly added transaction rows in the transaction history table, making it easy for users to find their just-executed trade.

## User Value

**Problem**: After executing a trade, hard to spot the new transaction in a long history list.
**Solution**: 3-second pulse animation highlights the new row.
**Benefit**: Immediate visual confirmation - "There's my trade!"

## Implementation

### CSS Animation

**Create animation** (`frontend/src/styles/animations.css` or inline):
```css
@keyframes pulse-highlight {
  0%, 100% {
    background-color: transparent;
  }
  50% {
    background-color: hsl(var(--primary) / 0.1);
  }
}

.highlight-new {
  animation: pulse-highlight 3s ease-in-out;
}
```

### Component Logic

**File**: `frontend/src/components/features/portfolio/TransactionHistory.tsx`

**Approach 1: Track Last Transaction ID**
```tsx
const [lastTransactionId, setLastTransactionId] = useState<string | null>(null);

useEffect(() => {
  if (transactions && transactions.length > 0) {
    const newestTransaction = transactions[0]; // Assuming sorted by date DESC
    
    // If this is a new transaction (not the one we last saw)
    if (newestTransaction.id !== lastTransactionId) {
      setLastTransactionId(newestTransaction.id);
      
      // Remove highlight after 3 seconds
      const timer = setTimeout(() => {
        setLastTransactionId(null);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }
}, [transactions]);

// In table row render
<tr 
  className={transaction.id === lastTransactionId ? 'highlight-new' : ''}
  data-testid={`transaction-${transaction.id}`}
>
  {/* cells */}
</tr>
```

**Approach 2: Use Query Invalidation Context** (Preferred)
```tsx
// When trade is executed, optimistically update query with highlight flag
const { mutate: executeTrade } = useMutation({
  mutationFn: tradeApi.execute,
  onSuccess: (newTransaction) => {
    queryClient.setQueryData(['transactions', portfolioId], (old) => ({
      ...old,
      transactions: [
        { ...newTransaction, isNew: true }, // Flag as new
        ...old.transactions
      ]
    }));
    
    // Remove flag after 3 seconds
    setTimeout(() => {
      queryClient.setQueryData(['transactions', portfolioId], (old) => ({
        ...old,
        transactions: old.transactions.map(t => 
          t.id === newTransaction.id ? { ...t, isNew: false } : t
        )
      }));
    }, 3000);
  }
});

// In table row render
<tr className={transaction.isNew ? 'highlight-new' : ''}>
```

## Quality Standards

- ✅ Complete TypeScript types (no `any`)
- ✅ Accessible (doesn't rely solely on color/animation)
- ✅ Performance: No unnecessary re-renders
- ✅ Cleanup: Clear timers on unmount
- ✅ Tests: Verify highlight appears and disappears

## UI/UX Requirements

**Animation**:
- Duration: 3 seconds total
- Easing: `ease-in-out`
- Color: Primary color at 10% opacity (`hsl(var(--primary) / 0.1)`)
- Type: Gentle pulse (background color fade in/out)

**Timing**:
- Start immediately when row appears
- Auto-remove after 3 seconds
- Only highlight truly NEW transactions (not on page refresh)

**Accessibility**:
- Add `aria-live="polite"` to transaction container
- Include screen reader announcement: "New transaction added"
- Don't rely solely on animation - keep visual hierarchy clear

**Edge Cases**:
- Multiple rapid trades → highlight each one sequentially
- Page navigation away/back → don't re-highlight old transactions
- Transaction deleted/undone → remove highlight if present

## Testing

**Unit Tests**:
```tsx
test('highlights new transaction for 3 seconds', async () => {
  const { rerender } = render(<TransactionHistory portfolioId="123" />);
  
  // Initial state - no highlight
  expect(screen.queryByClassName('highlight-new')).not.toBeInTheDocument();
  
  // Add new transaction
  // ... trigger trade execution
  
  // Should be highlighted
  const newRow = await screen.findByTestId('transaction-abc');
  expect(newRow).toHaveClass('highlight-new');
  
  // After 3 seconds, should NOT be highlighted
  await waitFor(() => {
    expect(newRow).not.toHaveClass('highlight-new');
  }, { timeout: 3500 });
});

test('does not highlight on initial page load', () => {
  render(<TransactionHistory portfolioId="123" />);
  
  const rows = screen.getAllByRole('row');
  rows.forEach(row => {
    expect(row).not.toHaveClass('highlight-new');
  });
});
```

**Manual Testing**:
1. View transaction history (empty or with existing transactions)
2. Execute a trade
3. Verify new transaction appears at top with pulse animation
4. Wait 3 seconds - animation should stop
5. Refresh page - no transactions should be highlighted
6. Execute multiple trades rapidly - each should pulse in sequence

## Success Criteria

1. New transactions pulse for 3 seconds
2. Animation stops automatically
3. Only highlights truly new transactions (not on page load)
4. No memory leaks (timers cleared properly)
5. Accessible (screen reader announcement)
6. Mobile responsive (animation works on all screen sizes)
7. All tests passing (234+ frontend tests)

## Files to Create/Modify

- `frontend/src/components/features/portfolio/TransactionHistory.tsx` - Add highlight logic
- `frontend/src/styles/animations.css` - **CREATE** or add to existing styles
- `frontend/src/components/features/portfolio/__tests__/TransactionHistory.test.tsx` - Add tests

## Alternative Approaches

**Simple CSS-only** (no state management):
- Add `data-timestamp` to each row
- Use CSS `:first-child:not([data-timestamp="loaded"])` selector
- Simpler but less control over when highlighting occurs

**React Query optimistic updates** (preferred):
- Leverage TanStack Query's optimistic update feature
- Automatically highlight newly added items
- Clean integration with existing data flow

## References

- MDN CSS Animations: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations
- React Query Optimistic Updates: https://tanstack.com/query/latest/docs/react/guides/optimistic-updates
- Accessibility guidelines for animations: https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions
- UX Polish Phase Plan: `docs/planning/ux-polish-phase-plan.md`
