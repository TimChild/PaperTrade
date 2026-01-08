# Task 078: Add Portfolio Deletion

**Agent**: backend-swe  
**Priority**: Medium  
**Estimated Effort**: 2-3 hours  

## Problem

Users can create portfolios but cannot delete them. There's no UI option to remove unwanted portfolios from the dashboard.

## Requirements

Implement full delete functionality for portfolios:

### Backend

1. **Delete Portfolio Use Case**
   - Create `DeletePortfolioUseCase` in application layer
   - Validate portfolio exists and belongs to user (when auth implemented)
   - Delete related data (holdings, transactions, snapshots) in correct order
   - Return success/failure status

2. **DELETE API Endpoint**
   - Add `DELETE /api/v1/portfolios/{portfolio_id}` route
   - Return 204 No Content on success
   - Return 404 if portfolio not found
   - Return 403 if user doesn't own portfolio (future auth)

3. **Database Cascade**
   - Ensure foreign key constraints handle cascading deletes
   - Or explicitly delete: snapshots → holdings → transactions → portfolio

### Frontend

1. **Delete Button UI**
   - Add "Delete Portfolio" button to portfolio settings/header
   - Use destructive styling (red, danger variant)
   - Position: Portfolio detail page header or settings dropdown

2. **Confirmation Dialog**
   - Show confirmation modal before deletion
   - Display warning: "This action cannot be undone"
   - Show portfolio name in confirmation
   - Require explicit "Delete" button click (not just "OK")

3. **Delete Mutation**
   - Create `useDeletePortfolio` mutation hook
   - Invalidate portfolio list query after success
   - Redirect to dashboard after deletion
   - Show success toast notification

4. **Error Handling**
   - Display error message if deletion fails
   - Handle network errors gracefully
   - Allow retry on failure

## Implementation Notes

### Domain Layer

```python
# backend/src/domain/use_cases/delete_portfolio.py
class DeletePortfolioUseCase:
    def __init__(self, portfolio_repo: PortfolioRepository):
        self._portfolio_repo = portfolio_repo
    
    def execute(self, portfolio_id: str) -> None:
        """Delete portfolio and all related data."""
        portfolio = self._portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        
        self._portfolio_repo.delete(portfolio_id)
```

### API Route

```python
@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(portfolio_id: str) -> None:
    """Delete a portfolio."""
    use_case = DeletePortfolioUseCase(portfolio_repo)
    use_case.execute(portfolio_id)
```

### Frontend Hook

```typescript
export function useDeletePortfolio() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (portfolioId: string) =>
      api.delete(`/portfolios/${portfolioId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      toast.success('Portfolio deleted successfully');
      navigate('/dashboard');
    },
    onError: (error) => {
      toast.error('Failed to delete portfolio');
    },
  });
}
```

## Testing

### Backend Tests

1. **Unit Tests**
   - Test delete use case with valid portfolio
   - Test delete with non-existent portfolio (404)
   - Test cascade deletion of related data

2. **Integration Tests**
   - Create portfolio → delete → verify gone
   - Verify holdings/transactions also deleted
   - Verify API returns 204 on success

### Frontend Tests

1. **Component Tests**
   - Test delete button renders
   - Test confirmation dialog appears
   - Test dialog cancellation
   - Test successful deletion flow

2. **E2E Tests**
   - Create portfolio → open detail → delete → verify dashboard
   - Test confirmation dialog workflow
   - Test error handling

## Acceptance Criteria

- [ ] Backend DELETE endpoint implemented
- [ ] Use case handles deletion and cascade
- [ ] Frontend delete button added to portfolio page
- [ ] Confirmation dialog requires explicit confirmation
- [ ] Success redirects to dashboard with toast
- [ ] Error shows helpful message
- [ ] All related data (holdings, transactions, snapshots) deleted
- [ ] All tests pass
- [ ] Cannot delete already-deleted portfolio (404)

## Future Enhancements (Out of Scope)

- Soft delete (archive) instead of hard delete
- Restore deleted portfolios
- Prevent deletion if portfolio has recent activity

## Related

- Found during manual UI testing session (2026-01-07)
- Basic CRUD operation, should be straightforward
- Complements portfolio creation (task 029)
