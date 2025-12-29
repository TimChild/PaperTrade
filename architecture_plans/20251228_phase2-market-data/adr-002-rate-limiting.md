# ADR 002: Rate Limiting Implementation

**Status**: Approved  
**Date**: 2025-12-28  
**Deciders**: Architecture Team  
**Context**: Phase 2 Market Data Integration

## Context

Alpha Vantage API enforces strict rate limits:
- **Free Tier**: 5 API calls per minute, 500 calls per day
- **Premium Tier**: 75 calls per minute, 100,000 calls per day (when we upgrade)

### Problem Statement

Without rate limiting, our application could:
1. **Exhaust daily quota quickly** (500 calls = 100 users each viewing a 5-stock portfolio)
2. **Get throttled by API** (429 Too Many Requests errors)
3. **Degrade user experience** (failed requests, error messages)
4. **Waste retries** (hitting API after quota exhausted)

### Requirements

- ✅ **Prevent quota exhaustion**: Stay within both per-minute and per-day limits
- ✅ **Configurable limits**: Easy to upgrade to premium tier
- ✅ **Graceful degradation**: Serve cached data when rate-limited
- ✅ **Observable**: Log near-limit warnings
- ✅ **Thread-safe**: Handle concurrent requests
- ✅ **Persistent**: Token counts survive application restarts

## Decision

Implement a **Token Bucket Algorithm** with **dual time windows** (minute + day) and **Redis-backed persistence**.

### Algorithm: Token Bucket

**Concept**: Tokens replenish at fixed intervals. Each API call consumes one token.

#### Per-Minute Bucket

| Property | Value |
|----------|-------|
| **Capacity** | 5 tokens (free tier), configurable |
| **Refill Rate** | Full refill every 60 seconds |
| **Refill Strategy** | Reset to capacity at minute boundary |

#### Per-Day Bucket

| Property | Value |
|----------|-------|
| **Capacity** | 500 tokens (free tier), configurable |
| **Refill Rate** | Full refill every 24 hours |
| **Refill Strategy** | Reset to capacity at midnight UTC |

### Implementation Strategy

**RateLimiter Interface**:

Provides methods:
- `can_make_request()` → Boolean (check if tokens available in BOTH buckets)
- `consume_token()` → None (decrement both buckets)
- `wait_time()` → timedelta (how long until next token available)
- `get_status()` → Dict (current token counts for observability)

**Storage**: Redis

Keys:
- `papertrade:ratelimit:minute:{YYYY-MM-DD-HH-MM}` → Integer (tokens remaining this minute)
- `papertrade:ratelimit:day:{YYYY-MM-DD}` → Integer (tokens remaining today)

TTL:
- Minute keys: 120 seconds (2 minutes, buffer for clock skew)
- Day keys: 48 hours (2 days, buffer for timezone edge cases)

**Logic**:

```
can_make_request():
  minute_key = generate_minute_key(now)
  day_key = generate_day_key(now)
  
  minute_tokens = redis.get(minute_key) OR capacity_per_minute
  day_tokens = redis.get(day_key) OR capacity_per_day
  
  return (minute_tokens > 0) AND (day_tokens > 0)

consume_token():
  minute_key = generate_minute_key(now)
  day_key = generate_day_key(now)
  
  redis.decr(minute_key)
  redis.decr(day_key)
  
  redis.expire(minute_key, 120)  # Ensure TTL set
  redis.expire(day_key, 48*3600)
```

### Integration with AlphaVantageAdapter

**Before API Call**:
```
if not rate_limiter.can_make_request():
    # Check for cached/stale data
    if cached_data_available:
        return cached_data_with_warning("Rate limited, serving cached price")
    else:
        raise MarketDataUnavailableError(
            f"Rate limit exceeded. Retry after {rate_limiter.wait_time()}"
        )

# Make API call
response = await http_client.get(url)

# After successful call
rate_limiter.consume_token()
```

## Alternatives Considered

### Alternative 1: In-Memory Token Bucket

**Implementation**: Python dict with threading.Lock

**Pros**:
- Simple, no external dependencies
- Fast (in-process)

**Cons**:
- ❌ Not shared across processes/servers (multi-instance deployment fails)
- ❌ Lost on application restart (could accidentally exhaust quota)
- ❌ No observability (can't inspect token counts externally)

**Decision**: **Rejected** - Doesn't scale, loses state

### Alternative 2: Database-Backed Rate Limiter

**Implementation**: PostgreSQL table with token counts

**Pros**:
- Persistent across restarts
- Shared across instances

**Cons**:
- ❌ Slower than Redis (50-100ms per check)
- ❌ Higher database load (every API call = 2 queries)
- ❌ Row locking contention under high concurrency

**Decision**: **Rejected** - Performance penalty too high

### Alternative 3: API Gateway Rate Limiting (AWS API Gateway)

**Implementation**: Use AWS API Gateway in front of Alpha Vantage

**Pros**:
- Offloads rate limiting to infrastructure
- Highly scalable

**Cons**:
- ❌ Alpha Vantage is external API (can't put behind our gateway)
- ❌ Adds cost and complexity
- ❌ Less control over fallback behavior

**Decision**: **Rejected** - Not applicable (external API)

### Alternative 4: Sliding Window Algorithm

**Implementation**: Track timestamps of last N requests

**Pros**:
- More accurate than fixed windows
- Prevents burst at window boundaries

**Cons**:
- ❌ More complex implementation
- ❌ Higher memory usage (store all timestamps)
- ❌ Token bucket is sufficient for our use case

**Decision**: **Rejected** - Unnecessary complexity

### Alternative 5: Leaky Bucket Algorithm

**Implementation**: Fixed processing rate, queue excess requests

**Pros**:
- Smooths out traffic spikes
- Predictable throughput

**Cons**:
- ❌ Requires request queue management
- ❌ Adds latency (queued requests wait)
- ❌ Token bucket refill matches API's reset behavior better

**Decision**: **Rejected** - Token bucket better matches API semantics

## Rationale for Chosen Approach

### Why Token Bucket?

1. **Matches API Behavior**: Alpha Vantage resets quotas at fixed intervals (minute/day)
2. **Simple Mental Model**: Tokens = API calls remaining
3. **Fast Checks**: Redis GET is <5ms
4. **Bursty Traffic Friendly**: Can use full capacity in burst if tokens available
5. **Industry Standard**: Used by AWS, Google, Stripe, etc.

### Why Redis?

1. **Performance**: <5ms latency for INCR/DECR operations
2. **Atomic Operations**: INCR/DECR are atomic (no race conditions)
3. **TTL Support**: Automatic cleanup of old keys
4. **Shared State**: All application instances see same token counts
5. **Observable**: Can inspect keys with redis-cli

### Why Dual Time Windows?

Alpha Vantage enforces BOTH limits simultaneously:
- Can't make 6th request in a minute (even if daily quota available)
- Can't make 501st request in a day (even if minute quota available)

We must check both buckets before making request.

## Edge Cases & Handling

### Edge Case 1: Clock Skew Across Instances

**Problem**: Two servers with clocks 30 seconds apart generate different minute keys

**Solution**: Use UTC for all timestamps, tolerate minor skew (Redis key overlap for 1 minute)

**Impact**: Might allow 6 requests instead of 5 in rare cases (acceptable)

### Edge Case 2: Redis Unavailable

**Problem**: Can't check token counts

**Options**:
1. **Fail Open**: Allow request (risk quota exhaustion)
2. **Fail Closed**: Block all requests (no API calls)
3. **Best Effort**: Use in-memory fallback with warning

**Decision**: **Fail Closed with Cache Fallback**
- Don't make API call if Redis down
- Serve cached/stale data if available
- Raise MarketDataUnavailableError if no cache

**Rationale**: Protect quota over availability (we have cache layers)

### Edge Case 3: Application Restart Mid-Minute

**Problem**: Redis says 3 tokens used, app restarts, forgets it made calls

**Solution**: Redis persists state independently of app lifecycle

**Result**: No issue (Redis is source of truth)

### Edge Case 4: Multiple Requests Simultaneously

**Problem**: 5 requests check `can_make_request()` at same time, all see 5 tokens

**Solution**: Use Redis transactions or Lua scripts for atomic check-and-decrement

**Implementation**:
```lua
-- Redis Lua script (executed atomically)
local minute_key = KEYS[1]
local day_key = KEYS[2]
local minute_cap = tonumber(ARGV[1])
local day_cap = tonumber(ARGV[2])

local minute_tokens = tonumber(redis.call('GET', minute_key) or minute_cap)
local day_tokens = tonumber(redis.call('GET', day_key) or day_cap)

if minute_tokens > 0 and day_tokens > 0 then
    redis.call('DECR', minute_key)
    redis.call('DECR', day_key)
    redis.call('EXPIRE', minute_key, 120)
    redis.call('EXPIRE', day_key, 172800)
    return 1  -- Success
else
    return 0  -- Rate limited
end
```

### Edge Case 5: Timezone Confusion

**Problem**: "Daily" limit - midnight in which timezone?

**Decision**: Always use **UTC**
- Day key: `papertrade:ratelimit:day:2025-12-28` (UTC date)
- Resets at 00:00:00 UTC (consistent, unambiguous)

**Alpha Vantage**: Also uses UTC (confirmed in API docs)

## Configuration

### Config File (backend/config.toml)

```toml
[market_data.rate_limit]
# Alpha Vantage tier (free or premium)
tier = "free"

# Free tier limits
free_calls_per_minute = 5
free_calls_per_day = 500

# Premium tier limits (when upgraded)
premium_calls_per_minute = 75
premium_calls_per_day = 100000

# Current active limits (based on tier)
calls_per_minute = "${free_calls_per_minute}"
calls_per_day = "${free_calls_per_day}"

# Redis configuration
redis_url = "redis://localhost:6379"
key_prefix = "papertrade:ratelimit"

# Safety margins (reserve N tokens for critical operations)
minute_reserve = 1  # Keep 1 token for emergency refreshes
day_reserve = 50    # Keep 50 tokens buffer
```

### Upgrading Tiers

To upgrade to premium:
1. Change `tier = "premium"` in config.toml
2. Restart application
3. RateLimiter reads new limits
4. Existing Redis keys expire naturally (within 48 hours)

No code changes required.

## Monitoring & Alerts

### Metrics to Track

| Metric | Target | Alert Threshold | Action |
|--------|--------|-----------------|--------|
| Minute tokens remaining | >1 | ≤0 | Check for traffic spike |
| Day tokens remaining | >50 | ≤100 | Consider premium upgrade |
| Rate limit blocks/hour | <5 | >20 | Increase cache TTL |
| API calls/hour | <20 | >40 | Check for cache miss issues |

### Logs to Emit

**INFO Level**:
- Token consumed (DEBUG level for detailed tracking)
- Daily reset occurred (informational)

**WARNING Level**:
- Tokens running low (minute < 2, day < 100)
- Request blocked due to rate limit
- Redis unavailable (failing closed)

**ERROR Level**:
- Rate limiter malfunction (negative tokens, missing keys)
- Redis connection failures (persistent)

### Dashboard Metrics

Create Grafana dashboard showing:
- Token count over time (minute + day buckets)
- API calls per hour
- Cache hit rate (correlated with rate limiting)
- Time until next refill

## Testing Strategy

### Unit Tests

Test RateLimiter class with:
- Token consumption (decrement counters)
- Refill logic (new minute/day resets)
- Dual-bucket enforcement (both must have tokens)
- Thread safety (concurrent requests)

Use **fakeredis** for tests (in-memory Redis mock).

### Integration Tests

Test with real Redis (test container):
- Tokens persist across app restarts
- TTL expires old keys
- Lua script atomicity

### Load Tests

Simulate high traffic:
- 100 concurrent requests (verify no race conditions)
- Burst traffic (verify tokens consumed correctly)
- Sustained load (verify refill works)

### Chaos Tests

Test failure modes:
- Redis down (verify fail-closed behavior)
- Clock skew (verify tolerance)
- Config change (verify smooth transition)

## Consequences

### Positive

- ✅ **Quota Protection**: Cannot exceed Alpha Vantage limits
- ✅ **Graceful Degradation**: Serve cached data when rate-limited
- ✅ **Observable**: Can inspect token counts in Redis
- ✅ **Configurable**: Easy to upgrade to premium tier
- ✅ **Scalable**: Works with multiple application instances
- ✅ **Persistent**: Survives application restarts

### Negative

- ⚠️ **Redis Dependency**: Adds infrastructure complexity
- ⚠️ **Failure Mode**: Redis down = no API calls (acceptable with caching)
- ⚠️ **Clock Sensitivity**: Minor clock skew could allow extra requests

### Neutral

- 🔄 **Complexity**: Token bucket is more complex than naive counting
- 🔄 **Testing**: Need to test time-based behavior (use freezegun)

## Migration & Rollback

### Migration Plan

1. Deploy RateLimiter with high limits (testing)
2. Monitor token consumption for 1 week
3. Lower limits to actual Alpha Vantage limits
4. Enable alerts for low tokens

### Rollback Plan

If RateLimiter causes issues:
1. Disable rate checking (allow all requests)
2. Rely on Alpha Vantage's server-side rate limiting (429 errors)
3. Serve cached data on 429 errors
4. Fix RateLimiter and redeploy

## Future Enhancements

### Phase 3+

- **Multi-Provider Support**: Different rate limiters per provider
- **Smart Throttling**: Slow down requests as tokens run low
- **Priority Queuing**: Critical requests bypass rate limit
- **Distributed Rate Limiting**: Use Redis cluster for horizontal scaling

## References

- [Token Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- [Redis Rate Limiting Pattern](https://redis.io/docs/manual/patterns/rate-limiter/)
- [Alpha Vantage Support - Rate Limits](https://www.alphavantage.co/support/#support)
- [Stripe Rate Limiting](https://stripe.com/docs/rate-limits)
- [AWS API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
