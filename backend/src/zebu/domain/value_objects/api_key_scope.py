"""API key scope value object.

Defines the permission scopes an API key can carry. Scopes are coarse-grained
capability flags — keys carry one or more scopes, and individual endpoints
can require specific scopes via the ``require_scope`` dependency.
"""

from enum import StrEnum


class ApiKeyScope(StrEnum):
    """Permission scopes for API keys.

    A key carries one or more scopes. Endpoints can require a specific scope
    via the ``require_scope`` dependency. The Clerk Bearer auth path is
    treated as full-trust (all scopes implicitly granted) since it represents
    a human authenticated through the UI.

    Attributes:
        READ: Read-only access (list, get). Default minimum scope.
        TRADE: Write access to trading operations (deposit, withdraw, buy,
            sell, create strategies, run backtests, activate strategies).
        ADMIN: Administrative access (snapshot backfill, price refresh).
            Even with this scope, an API key cannot mint or revoke other
            API keys — that path is Clerk-gated only.
    """

    READ = "read"
    TRADE = "trade"
    ADMIN = "admin"
