# Task 216 — FK fixture cleanup + repo IntegrityError catch-all fix

**Status**: In progress
**Branch**: `chore/216-fk-fixture-cleanup`
**Agent**: `backend-swe`

## Origin

PR #292 ([test(integration): real-DB MCP smoke flows with FK enforcement](https://github.com/TimChild/PaperTrade/pull/292)) added a sibling `test_engine_with_fks` fixture instead of flipping `test_engine` to FK-on globally, because attempting the global flip surfaced ~17 fixture violations plus one repo-level bug:

> The 17 pre-existing FK violations are a separate cleanup PR worth doing soon — they're real tests that would fail in production today but pass locally.

This task closes that gap so all backend tests run with FK enforcement, matching production Postgres.

## The repo bug

`backend/src/zebu/adapters/outbound/database/transaction_repository.py:160-165` and `:207-213`:

```python
try:
    await self._session.flush()
except IntegrityError as e:
    raise DuplicateTransactionError(...) from e
```

The catch is too broad. **Any** `IntegrityError` — FK violation, NOT NULL violation, CHECK constraint, etc. — is translated to `DuplicateTransactionError`. In production this misclassifies referential-integrity bugs as duplicate-ID conflicts.

Fix: narrow the catch to PK conflicts only (UNIQUE constraint on `transactions.id`). Re-raise FK / NOT-NULL violations as `IntegrityError` unchanged.

## The fixture bug

`backend/tests/conftest.py:47-79` (`test_engine`) currently does not set `PRAGMA foreign_keys=ON`. This means in-memory SQLite test runs accept rows whose FK references point to non-existent parent rows — exactly the class of bug PR #287 (FK ordering, backtest portfolio not saved before backtest_run) and the regressions covered by PR #291 surfaced.

The fix is two lines: copy the `event.listens_for` listener from the sibling `test_engine_with_fks` fixture into `test_engine`. The work is in cleaning up the ~17 violations the global flip surfaces.

## Phases (all in one PR)

### 1. Repo fix (narrow the catch)

In `transaction_repository.py`:

- Use a helper (e.g. `_is_pk_conflict`) to inspect `IntegrityError.orig`. Match SQLite's `UNIQUE constraint failed: transactions.id` and Postgres' equivalent (`UniqueViolation` on the PK).
- Translate to `DuplicateTransactionError` only when that check matches.
- Re-raise unchanged otherwise (FK / NOT NULL / CHECK).

Apply the same fix to both `save` and `save_all`.

### 2. Fixture flip + violation triage

- Copy the `event.listens_for(...)` listener from `test_engine_with_fks` into `test_engine`.
- Run `uv run pytest backend/tests/` and walk the failures.
- For each failure, decide: real test-setup bug (fix the fixture / test) or real production-code bug (HALT and report — do NOT silently downgrade FK enforcement back off).

The 17 violations are not pre-catalogued — discovery happens at run time.

### 3. Consolidation

- `test_engine_with_fks` becomes a trivial alias (or a thin re-export) — kept only for the import surface in `test_mcp_smoke_flows.py`.
- `test_engine`'s docstring updated to reflect production parity.

## Testing strategy

### Repo-layer tests (new)

Two unit tests in `backend/tests/unit/adapters/outbound/database/` (or wherever the existing `transaction_repository` tests live):

1. `test_save_propagates_fk_violation_as_integrity_error` — try to save a transaction whose `portfolio_id` references a non-existent portfolio. Expect `IntegrityError`, NOT `DuplicateTransactionError`.
2. `test_save_translates_pk_conflict_to_duplicate_transaction_error` — save the same transaction ID twice. Expect `DuplicateTransactionError`.

Both tests need FKs on. Use the new `test_engine` (post-flip) or `engine` from `tests/integration/conftest.py`.

### Existing tests

Must all pass with FKs on. That's the work of phase 2.

## Quality bar

- No `Any`, no type-checker suppressions added.
- Tests behavior-focused.
- Don't refactor unrelated fixtures while you're in there — one concern per PR.

## Success criteria

- `task ci` green locally.
- `test_engine` enforces FKs by default.
- `test_engine_with_fks` is a trivial alias (preserves the import in `test_mcp_smoke_flows.py`).
- `transaction_repository.save` / `save_all` re-raise non-PK `IntegrityError`s.
- New repo-layer unit tests cover both directions.
- PR body lists the count of fixture violations fixed and notes any production bugs discovered.

## References

- PR #287 — FK ordering bug that motivated FK enforcement in tests
- PR #292 — added `test_engine_with_fks`; this task closes the follow-up
- `backend/tests/conftest.py:47-117` — both fixtures
- `backend/src/zebu/adapters/outbound/database/transaction_repository.py:160-165, 207-213` — the catch-all
- `backend/tests/integration/test_mcp_smoke_flows.py` — uses `test_engine_with_fks` explicitly
