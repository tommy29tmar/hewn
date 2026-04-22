# Evidence — T1a / `explain-db-pool`

## Prompt

```text
Explain database connection pooling.
```

## `baseline`

output_tokens (anthropic) = **701**, output_tokens (tiktoken) = 429, input_tokens = 6, cache_creation = 11723, cache_read = 16796, latency wall = 13640ms (median across runs: 13640ms)

```text
Database connection pooling keeps a set of open database connections in memory and hands them out to application code on demand, instead of opening a new TCP+auth handshake per query.

**Why it exists**
- Opening a connection is expensive: TCP handshake, TLS, auth, session setup — often 10–100ms.
- Databases cap concurrent connections (Postgres defaults to ~100); unbounded clients exhaust them.
- Each backend connection costs memory (Postgres: ~10MB/conn).

**How it works**
1. Pool initializes with `min` idle connections.
2. App calls `pool.acquire()` → returns an idle connection, or opens a new one up to `max`, or waits if at cap.
3. App runs queries, calls `release()` → connection returns to pool (reset, not closed).
4. Idle connections past a timeout are closed down to `min`.

**Key knobs**
- `max` — hard cap. Must be ≤ DB's limit, divided across app instances.
- `min` — warm connections always ready.
- `acquireTimeout` — how long to wait for a free connection before erroring.
- `idleTimeout` — when to close unused connections.
- `maxLifetime` — recycle connections periodically (avoids stale state, load-balancer drift).

**Two layers**
- **In-process pool** (HikariCP, pgx, SQLAlchemy) — per app instance.
- **External pooler** (PgBouncer, RDS Proxy) — shared across instances. Use when you have many app replicas overwhelming the DB.

**Common pitfalls**
- Pool smaller than concurrency → requests queue/timeout.
- Pool larger than DB cap × replicas → DB rejects connections.
- Transaction-mode poolers (PgBouncer) break session features: `SET`, prepared statements, `LISTEN`.
- Leaked connections (missing `release()` in error paths) slowly drain the pool.

**Sizing heuristic**: `connections = ((core_count * 2) + effective_spindle_count)` per DB, then divide across app instances. In practice, measure under load.
```

## `terse`

output_tokens (anthropic) = **643**, output_tokens (tiktoken) = 394, input_tokens = 6, cache_creation = 6550, cache_read = 13741, latency wall = 12259ms (median across runs: 12259ms)

```text
Database connection pooling maintains a cache of open database connections that can be reused across requests, instead of opening and closing one per query.

**Why it matters**
- Opening a connection is expensive: TCP handshake, TLS, auth, session setup — often 10–100ms.
- Databases cap concurrent connections (Postgres default: 100). Uncapped clients exhaust them.
- Reusing warm connections slashes latency and CPU on both ends.

**How it works**
1. Pool pre-opens N connections at startup (or lazily).
2. App requests a connection → pool hands out an idle one.
3. App runs query, returns connection to pool (doesn't close it).
4. If all are busy, requester waits or the pool opens more (up to `max`).
5. Idle connections beyond `min` are closed after a timeout.

**Key knobs**
- `min` / `max` size — floor and ceiling.
- Acquire timeout — how long to wait for a free connection.
- Idle timeout — when to reap unused ones.
- Max lifetime — recycle connections to avoid stale state / memory bloat.
- Validation query — detect dead connections before handing them out.

**Where the pool lives**
- **In-process** (HikariCP, pgx, SQLAlchemy): fast, but each app instance has its own pool. 20 instances × 50 conns = 1000 DB connections.
- **Sidecar/proxy** (PgBouncer, RDS Proxy): shared across instances, essential at scale. Modes: session, transaction, statement — transaction pooling is most common but breaks features like prepared statements and `SET LOCAL`.

**Common pitfalls**
- Leaked connections (forgetting to release) → pool exhaustion → hangs.
- Long-held transactions blocking the pool.
- Pool max > DB max_connections → connection refused.
- Serverless functions each creating a pool → DB melts. Use a proxy.
```

## `caveman_full`

output_tokens (anthropic) = **168**, output_tokens (tiktoken) = 96, input_tokens = 6, cache_creation = 6550, cache_read = 15186, latency wall = 4659ms (median across runs: 4659ms)

```text
Pool reuse open DB connections. No new connect per request. Skip TCP + auth handshake overhead.

Flow: app borrow conn from pool → query → return to pool. Idle conns stay warm.

Key knobs: max size (cap concurrent), min idle (pre-warm), timeout (wait limit), max lifetime (recycle stale).

Win: fast under load, bounded DB load, no connect storm. Risk: pool too small → queue stalls. Too big → DB overwhelm.
```
