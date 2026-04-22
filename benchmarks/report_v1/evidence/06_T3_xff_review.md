# Evidence — T3 / `rate-limit-xff-review`

## Prompt

```text
[handbook ~4668 tokens prefixed]

[Task]
"
```

## `baseline`

output_tokens (anthropic) = **146**, output_tokens (tiktoken) = 54, input_tokens = 6, cache_creation = 0, cache_read = 39804, latency wall = 4864ms (median across runs: 4864ms)

```text
The task field is empty — what would you like me to do with the Atlas API handbook? Common asks I can handle: review a specific file/PR against these rules, write code following these standards, audit existing code for violations, or answer questions about the spec.
```

## `terse`

output_tokens (anthropic) = **100**, output_tokens (tiktoken) = 21, input_tokens = 6, cache_creation = 0, cache_read = 31422, latency wall = 2675ms (median across runs: 2556ms)

```text
No task specified after `[Task]`. What would you like me to do with the Atlas API handbook?
```

## `caveman_full`

output_tokens (anthropic) = **72**, output_tokens (tiktoken) = 14, input_tokens = 6, cache_creation = 17681, cache_read = 15186, latency wall = 2968ms (median across runs: 2968ms)

```text
No task given. Empty brackets. What you want done with handbook?
```

## `caveman_full_plus_ultra_directive`

output_tokens (anthropic) = **54**, output_tokens (tiktoken) = 7, input_tokens = 6, cache_creation = 0, cache_read = 32881, latency wall = 2645ms (median across runs: 2645ms)

```text
No task given. What want?
```

## `hewn_prompt_only`

output_tokens (anthropic) = **252**, output_tokens (tiktoken) = 70, input_tokens = 6, cache_creation = 23008, cache_read = 16796, latency wall = 5879ms (median across runs: 5879ms)

```text
The `[Task]` section is empty — there's no instruction after the handbook. What would you like me to do with the Atlas API handbook? Some options:

- Review a specific change or PR against these standards
- Audit the codebase for compliance with Section 2 rules
- Draft code for one of the pipeline middlewares
- Something else
```

## `hewn_full`

output_tokens (anthropic) = **5180**, output_tokens (tiktoken) = 1247, input_tokens = 6, cache_creation = 24429, cache_read = 16805, latency wall = 84026ms (median across runs: 84026ms)

```text
[Task] section is empty — no explicit question. Proceeding with top findings on the handbook itself since classification is prose-findings. Flag if you wanted something else.

1. multi.exec() destructure silently breaks rate limiter — Section 4 code snippet
Evidence: `const [count] = await multi.exec()` with ioredis; exec returns `[[null, 1], [null, 1]]`, so `count` is the array `[null, 1]`, not the integer. `count > limit` compares array to number → NaN → always false → limiter never trips.
Fix: destructure inner tuple — `const [[, count]] = await multi.exec()` — and assert error is null; or switch to `redis.call('INCR'...)` + separate `EXPIRE`. Add regression test that returns >limit and asserts 429.

2. Region prefix missing from key format despite 2025-12 RCA — Section 4 key `rl:{ip}:{route_prefix}:{minute_bucket}` vs Section 10 "region prefix in key, regression test added"
Evidence: documented key shape contradicts the RCA action item; either the handbook is stale or the fix regressed.
Fix: reconcile — if fix shipped, update key format to `rl:{region}:{ip}:{route_prefix}:{minute_bucket}`; if not, reopen incident.

3. Fixed-window masquerading as sliding window; retry_after allows burst-wait-burst — Section 4 bucket = `Math.floor(Date.now() / 60000)`
Evidence: minute_bucket is a wall-clock bucket, not sliding. A client at limit at 59.9s waits 0.1s (`secondsUntilNextBucket()` returns ~1) and gets a full fresh bucket — effectively 2× limit across bucket boundary.
Fix: true sliding window via sorted set (ZADD + ZREMRANGEBYSCORE + ZCARD) or token bucket; at minimum, compute retry_after against effective window, not bucket edge.

4. JWKS stale-while-revalidate can serve poisoned keys indefinitely — Section 2 rule 4 and Section 5
Evidence: 2025-06 SEV1 was wrong-key poisoning; current policy is 15-min refresh + 16-min soft TTL + SWR, with no hard TTL cap. A persistent upstream JWKS failure keeps a bad key live forever while returning stale.
Fix: add hard TTL (e.g. 2×refresh); on JWKS sanity-check failure, do not promote — keep prior good set and alert; ensure Section 10 RCA action "JWKS sanity-check on every refresh" is enforced in code, not just doc.

5. `no-unbounded-redis-key` lint rule is syntactic and easily bypassed — Section 11
Evidence: rule requires "same async function as a matching redis.expire call". Satisfied by any literal `redis.expire(...)` in the function, even on a different key or in dead/conditional code. 2025-11 SEV2 class of bugs still possible.
Fix: type-level affordance (wrap `incr` in helper that forces `{ ttlSeconds }`); ban raw `redis.incr` in edge code; lint on the helper instead.

6. JWT 30s post-expiry grace is an exploit window for stolen tokens — Section 5
Evidence: `skewMs = 30000` applied to `exp` means a revoked/stolen token remains valid 30s past real expiry across the entire fleet.
Fix: apply skew only to `nbf` (clock-drift direction that matters); reject on strict `exp`. If skew on exp is required, cap tightly (≤5s) and document the risk explicitly.

7. CODEOWNERS gate omits pipeline order and lint plugin — Section 6
Evidence: approval required on `auth_jwt.ts`, `rate_limit.ts`, `header_sanitize.ts`, `trusted_proxies.json`, but not `src/edge/pipeline.ts` (Section 3 states ordering is a security invariant) nor `tools/eslint-plugin-atlas/` (contains `no-direct-xff-read`, `no-jwt-none-allowed`).
Fix: extend CODEOWNERS to `src/edge/pipeline.ts` and `tools/eslint-plugin-atlas/**`.

8. `no-direct-xff-read` rule scope too narrow — Section 11
Evidence: forbids `req.headers['x-forwarded-for']` string literally. A dev writing `req.headers["X-Forwarded-For"]`, destructuring `const { "x-forwarded-for": xff } = req.headers`, or reading via computed key escapes the rule. 2025-09 SEV1 regression path still open.
Fix: broaden to AST match on any property access whose key (case-insensitive) equals `x-forwarded-for` on a `req.headers`-typed node; add integration test that spoofs XFF and asserts `trustedClientIp` ignores it.

9. API-key LRU cache has no revocation invalidation path — Section 5
Evidence: "30-second LRU cache of last-100k keys". Revoked/leaked partner key remains accepted up to 30s post-revoke with no documented bust mechanism.
Fix: subscribe to `auth-svc` revocation pub/sub (Redis channel) and punch holes in the LRU on revoke events; keep 30s as a fallback TTL, not the only barrier.

10. Section 3 pipeline has no explicit XFF normalization step — middleware list at `src/edge/pipeline.ts`
Evidence: Section 2 rule 2 is a hard invariant but pipeline lists only `header_sanitize` and `rate_limit`; Section 4 invokes `trustedClientIp(req)` but its trust source and when XFF is rewritten vs stripped is undocumented.
Fix: document (and verify in code) that `header_sanitize` canonicalizes XFF against `config/trusted_proxies.json` and overwrites a derived `req.trustedIp`; forbid any other IP reads.
```
