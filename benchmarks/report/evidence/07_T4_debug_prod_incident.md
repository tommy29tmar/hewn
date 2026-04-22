# Evidence — T4 / `debug-prod-incident` (5-turn cumulative)

## `baseline` — cumulative output_tokens=3104, cumulative wall=58658ms

### Turn 1

**user:**

```text
Production is throwing 500s on POST /api/orders since 14:23 UTC. Logs show 'TypeError: Cannot read properties of undefined (reading items)' in createOrder handler. Last deploy was 14:18 UTC. What do I check first?
```

**assistant:**

_output_tokens=553_

```text
Check in this order:

1. **Diff the deploy.** `git log 14:18..HEAD -- **/createOrder*` (or whatever the handler file is). The error started 5 min after deploy — assume causation until proven otherwise. Look for changes to request body parsing, destructuring of `req.body.items`, or middleware order.

2. **Grab a failing request payload.** From logs, find what the client is actually sending. The error says `items` is on `undefined` — so something one level up is missing. Likely `req.body` itself (body-parser misconfig, wrong Content-Type) or a nested field like `req.body.order.items` where `order` is now undefined.

3. **Check the stack trace line.** Pinpoint exactly which expression threw. `req.body.items` vs `order.items` vs `cart.items` are very different root causes.

4. **Decide: rollback or forward-fix.** If the diff is non-trivial and you can't fix in <5 min, roll back the 14:18 deploy now and debug after. 500s on order creation = revenue loss.

Most likely culprit given the symptom: a refactor that changed the request shape (e.g., moved `items` under a new key) without updating the handler, or a middleware change that stopped populating `req.body`.
```

### Turn 2

**user:**

```text
Rolled back to previous deploy and 500s stopped. Now I need to find what changed. The PR that shipped at 14:18 was a refactor of cart serialization. Here's the diff for the suspected file: function buildCart(cart) { return { id: cart.id, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. Original was: function buildCart(cart) { return { id: cart.id, items: cart.items, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. What broke?
```

**assistant:**

_output_tokens=196_

```text
The refactor dropped `items` from `buildCart`'s return value. Downstream `createOrder` still does `builtCart.items.reduce(...)` or `builtCart.items.map(...)` — and now `builtCart.items` is `undefined`, hence the TypeError.

Fix: either add `items: cart.items` back to the return, or update `createOrder` (and any other consumer of `buildCart`) to read items from the source `cart` instead of the built object.

Before re-deploying, grep for `.items` on every `buildCart(...)` callsite — there may be more than one consumer affected.
```

### Turn 3

**user:**

```text
Right, items field was dropped. Downstream order service expects items. Fix: re-add items in buildCart. But I want to add a regression test so this can't happen again. What's the right test shape? We use Jest.
```

**assistant:**

_output_tokens=746_

```text
Two tests, different layers:

**1. Contract test on `buildCart`** — pins the return shape so dropping a field fails loudly:

```js
test('buildCart returns id, items, and total', () => {
  const cart = { id: 'c1', items: [{ price: 10, qty: 2 }, { price: 5, qty: 1 }] };
  expect(buildCart(cart)).toEqual({
    id: 'c1',
    items: cart.items,
    total: 25,
  });
});
```

Use `toEqual` (not `toMatchObject`) so extra or missing fields both fail. This is the test that would have caught the regression.

**2. Integration test on `createOrder`** — exercises the actual failure path:

```js
test('createOrder succeeds for a valid cart', async () => {
  const res = await createOrder({ cart: { id: 'c1', items: [{ price: 10, qty: 1 }] }, userId: 'u1' });
  expect(res.status).toBe(201);
  expect(res.body.items).toHaveLength(1);
});
```

This catches the *class* of bug (handler crashes on a realistic payload), not just this specific field drop.

Skip snapshot tests here — they encourage rubber-stamping when the shape changes intentionally. Explicit `toEqual` forces a real decision.

If `buildCart` has multiple consumers, also worth a quick `expect(typeof buildCart(cart).items).toBe('object')`-style smoke check at each callsite, but the contract test above is the load-bearing one.
```

### Turn 4

**user:**

```text
Test added and passes. Now reviewing the rest of that PR. There's also a change to the inventory check: it now uses Promise.all over an array of SKU lookups instead of a sequential loop. Is that safe under our DB connection pool of 20 max?
```

**assistant:**

_output_tokens=908_

```text
Unbounded `Promise.all` against a shared pool is a load-time footgun, not a correctness bug. Here's the math:

- Sequential: 1 connection per request, regardless of cart size.
- `Promise.all`: up to N connections per request, where N = items in cart.

Pool of 20: a single 30-item cart queues 10 of its own queries. Five concurrent orders with 10 items each = 50 queries fighting for 20 slots, **plus** every other endpoint (reads, health checks, auth lookups) gets queued behind them. P50 likely drops, P99 and tail latency get worse under load, and you can cascade into request timeouts that look unrelated.

Three options, in order of preference:

1. **Batch into one query.** `SELECT * FROM inventory WHERE sku IN (...)`. One connection, one round trip, strictly better than both the loop and `Promise.all`. This is almost always the right answer for "N lookups by ID."

2. **Bounded concurrency** if batching isn't possible (different tables, different shards, etc.). Use `p-limit` with a cap of ~5:
   ```js
   const limit = pLimit(5);
   await Promise.all(skus.map(sku => limit(() => lookup(sku))));
   ```

3. **Keep the sequential loop** if cart sizes are small (<5) and latency isn't a concern. Boring and safe.

What I'd ask the PR author: what's the P99 cart size? If it's >10, ship option 1 before this hits production again.
```

### Turn 5

**user:**

```text
OK so the parallel call could exhaust the pool if a single order has many SKUs. Average order has 3 SKUs, max we've seen is 47. Recommend a fix that's safer but doesn't slow down the common case.
```

**assistant:**

_output_tokens=701_

```text
Replace the fan-out with a single batched query:

```js
const rows = await db.query(
  'SELECT sku, qty FROM inventory WHERE sku = ANY($1)',
  [skus]
);
const bySku = new Map(rows.map(r => [r.sku, r]));
const results = skus.map(sku => bySku.get(sku));
```

One connection, one round trip. The 3-SKU case goes from ~3 round trips (sequential) or ~3 parallel queries to **1**. The 47-SKU case goes from "starves the pool" to the same single query. Common case gets faster, worst case stops being dangerous.

Two things to check before shipping:

1. **Missing SKUs.** `ANY` returns only matching rows. Iterate the original `skus` array (as above) so you preserve order and surface missing SKUs as `undefined` — don't iterate `rows`, or you'll silently drop unknowns.

2. **Query plan.** Make sure `inventory.sku` is indexed. With an index, `= ANY($1)` is fine up to thousands of values. Without one, you've turned N indexed lookups into one seq scan — worse.

Fallback if batching genuinely isn't possible (cross-shard, per-SKU app logic, etc.): `p-limit(5)`. But for "lookup inventory by SKU," batching is almost certainly the right call.
```

---

## `terse` — cumulative output_tokens=2333, cumulative wall=48056ms

### Turn 1

**user:**

```text
Production is throwing 500s on POST /api/orders since 14:23 UTC. Logs show 'TypeError: Cannot read properties of undefined (reading items)' in createOrder handler. Last deploy was 14:18 UTC. What do I check first?
```

**assistant:**

_output_tokens=401_

```text
Roll back the 14:18 deploy, then investigate.

First checks, in order:

1. **Diff the deploy** — `git log 14:18..HEAD` on the release branch, focus on `createOrder` and anything touching the request body shape (validation, middleware, schema).
2. **Request payload** — grab a failing request from logs. Is `req.body` undefined (missing `express.json()` / body-parser) or is `req.body.items` undefined (client contract change)?
3. **Client contract** — did the payload key rename (e.g. `items` → `lineItems`, or nested under `order.items`)? Check frontend/mobile deploys in the same window.
4. **Middleware order** — if body-parser or an auth middleware was reordered, `req.body` can be undefined.
5. **Stack trace line** — exact file:line of the throw tells you whether it's `req.body.items`, `order.items`, or a downstream destructure.

Fastest triage: one failing request + the deploy diff. That pair usually identifies it in under 5 minutes.

If rollback isn't instant, hotfix: `const items = req.body?.items ?? []` with a 400 if empty — but only after you know which `.items` is undefined.
```

### Turn 2

**user:**

```text
Rolled back to previous deploy and 500s stopped. Now I need to find what changed. The PR that shipped at 14:18 was a refactor of cart serialization. Here's the diff for the suspected file: function buildCart(cart) { return { id: cart.id, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. Original was: function buildCart(cart) { return { id: cart.id, items: cart.items, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. What broke?
```

**assistant:**

_output_tokens=190_

```text
The refactor dropped `items` from the returned cart object.

`createOrder` almost certainly does something like `buildCart(cart).items.reduce(...)` or destructures `{ items }` from the result downstream. Now `buildCart(...).items` is `undefined` → `Cannot read properties of undefined (reading items)` when the next layer reads `.items` off it.

Fix: put `items: cart.items` back in the return, or update every `buildCart` consumer to read `items` from the source cart instead. Grep for `buildCart(` and check each call site before re-shipping.
```

### Turn 3

**user:**

```text
Right, items field was dropped. Downstream order service expects items. Fix: re-add items in buildCart. But I want to add a regression test so this can't happen again. What's the right test shape? We use Jest.
```

**assistant:**

_output_tokens=477_

```text
Test the contract, not the implementation.

```js
describe('buildCart', () => {
  const cart = {
    id: 'c1',
    items: [{ id: 'i1', price: 10, qty: 2 }, { id: 'i2', price: 5, qty: 1 }],
  };

  it('returns id, items, and total', () => {
    expect(buildCart(cart)).toEqual({
      id: 'c1',
      items: cart.items,
      total: 25,
    });
  });

  it('preserves items for downstream consumers', () => {
    expect(buildCart(cart).items).toBe(cart.items);
  });
});
```

Key choices:

- **`toEqual` on the whole object** — locks the shape. Any future drop of a field fails loudly. This is the one that would have caught your bug.
- **Separate `items` assertion** — documents intent ("downstream depends on this") so a future refactorer sees *why* it's there, not just *that* it's there.
- **`.toBe(cart.items)`** (reference equality) if you want to assert no copy; use `.toEqual` if a copy is acceptable. Pick based on whether downstream mutates.

Optional: add an integration test at the `createOrder` boundary with a minimal cart → asserts 200 + order persisted. That catches contract drift between `buildCart` and its consumers, which is the actual class of bug. Unit test alone won't catch a rename if both sides change together.
```

### Turn 4

**user:**

```text
Test added and passes. Now reviewing the rest of that PR. There's also a change to the inventory check: it now uses Promise.all over an array of SKU lookups instead of a sequential loop. Is that safe under our DB connection pool of 20 max?
```

**assistant:**

_output_tokens=648_

```text
Depends on cart size and what else shares the pool.

The risk: `Promise.all` fires all N lookups concurrently. If a cart has 50 SKUs, you request 50 connections. Pool caps at 20, so 30 queries queue. That's fine in isolation — they just wait — but under load it starves other handlers (checkout, auth, anything) of connections, and you get cascading timeouts that look like a DB outage but are actually pool exhaustion.

Checks:

1. **Max cart size** — what's p99 items per cart? If it's 5, non-issue. If it's 200, you've built a pool bomb.
2. **Concurrent request load** — 10 concurrent orders × 50 SKUs = 500 queued queries against a 20-conn pool. Every other endpoint stalls.
3. **Query shape** — N individual `SELECT ... WHERE sku = ?` is the wrong primitive regardless. One `SELECT ... WHERE sku IN (...)` is one connection, one round trip, and doesn't touch the pool question.

Recommendations, in order of preference:

1. **Batch into one query** — `WHERE sku IN (:skus)`. Eliminates the concurrency question entirely. This is almost always the right answer for inventory lookups.
2. **If batching isn't possible**, bound concurrency: `p-limit` or similar, cap at something like 5. Keeps pool headroom for other traffic.
3. **Raw `Promise.all` is only safe** when N is small and bounded (schema-enforced, e.g. max 10 items per cart) *and* you've measured pool pressure under peak load.

Sequential was slow but safe. Unbounded `Promise.all` is fast but a latent incident. Batched query is both.
```

### Turn 5

**user:**

```text
OK so the parallel call could exhaust the pool if a single order has many SKUs. Average order has 3 SKUs, max we've seen is 47. Recommend a fix that's safer but doesn't slow down the common case.
```

**assistant:**

_output_tokens=617_

```text
Batch it. One `WHERE sku IN (...)` query.

```js
async function checkInventory(skus) {
  if (skus.length === 0) return new Map();
  const rows = await db.query(
    'SELECT sku, stock FROM inventory WHERE sku = ANY($1)',
    [skus]
  );
  return new Map(rows.map(r => [r.sku, r.stock]));
}
```

Why this beats bounded concurrency:

- **Common case (3 SKUs)**: 1 query vs 3. Faster than the original parallel version, not slower.
- **Worst case (47 SKUs)**: 1 query vs 47. Uses one connection, not 20+. Pool is untouched.
- **No tuning knob** — no `p-limit` concurrency value to second-guess. The pool question disappears.
- **DB-side efficiency** — one round trip, one query plan, index hit once.

Caveats to check before shipping:

1. **Driver syntax** — `ANY($1)` is Postgres. MySQL uses `IN (?)` with array expansion via the driver. Match your stack.
2. **SKU list size limit** — Postgres handles thousands fine, but if SKUs can somehow be unbounded (they can't here — 47 max), chunk at 1000.
3. **Return shape** — callers probably expect per-SKU results in order. Return a `Map` (as above) and let callers look up by SKU, or re-sort to match input order if the existing contract requires an array.
4. **Missing SKUs** — decide explicitly: does a missing row mean "0 stock" or "invalid SKU"? The old sequential code may have thrown on missing; the batched version silently omits. Preserve the existing behavior or the order service may accept invalid SKUs.

Add a test with a cart containing one known-missing SKU to lock that behavior.
```

---

## `caveman_full` — cumulative output_tokens=1059, cumulative wall=29035ms

### Turn 1

**user:**

```text
Production is throwing 500s on POST /api/orders since 14:23 UTC. Logs show 'TypeError: Cannot read properties of undefined (reading items)' in createOrder handler. Last deploy was 14:18 UTC. What do I check first?
```

**assistant:**

_output_tokens=182_

```text
Rollback now. 5min gap → deploy caused.

Then investigate:
1. `git diff <prev>..HEAD -- **/createOrder*` — find `req.body.items` access
2. Check req validation/middleware — body parser missing? schema changed?
3. Check client — did payload shape change? `items` moved/renamed?
4. Repro: curl POST with known-good payload vs prod payload

Most likely: handler reads `req.body.items` but body undefined (missing `express.json()`) or payload now `{order: {items}}`.
```

### Turn 2

**user:**

```text
Rolled back to previous deploy and 500s stopped. Now I need to find what changed. The PR that shipped at 14:18 was a refactor of cart serialization. Here's the diff for the suspected file: function buildCart(cart) { return { id: cart.id, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. Original was: function buildCart(cart) { return { id: cart.id, items: cart.items, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. What broke?
```

**assistant:**

_output_tokens=118_

```text
Refactor dropped `items` from output. Downstream `createOrder` reads `builtCart.items` → undefined → crash.

Fix: restore `items: cart.items` in returned object, or update consumer to use `cart.items` directly (source), not `buildCart()` result.

Grep `buildCart(` callers — any access `.items` on result broke.
```

### Turn 3

**user:**

```text
Right, items field was dropped. Downstream order service expects items. Fix: re-add items in buildCart. But I want to add a regression test so this can't happen again. What's the right test shape? We use Jest.
```

**assistant:**

_output_tokens=259_

```text
```js
describe('buildCart', () => {
  const cart = { id: 'c1', items: [{ price: 10, qty: 2 }, { price: 5, qty: 1 }] };

  it('preserves items in output', () => {
    expect(buildCart(cart).items).toEqual(cart.items);
  });

  it('computes total', () => {
    expect(buildCart(cart).total).toBe(25);
  });

  it('returns id', () => {
    expect(buildCart(cart).id).toBe('c1');
  });
});
```

Key test = first one. Contract: output shape includes `items`. Lock it.

Bonus: contract test at boundary — `createOrder` given `buildCart()` output succeeds. Catches future drops regardless of internal refactor.
```

### Turn 4

**user:**

```text
Test added and passes. Now reviewing the rest of that PR. There's also a change to the inventory check: it now uses Promise.all over an array of SKU lookups instead of a sequential loop. Is that safe under our DB connection pool of 20 max?
```

**assistant:**

_output_tokens=295_

```text
Depends on cart size.

- Cart ≤ ~15 SKUs: safe, faster.
- Cart > 20 SKUs: all lookups fire at once → pool saturates → other requests queue/timeout.
- Concurrent orders multiply: 5 orders × 10 SKUs = 50 in-flight → pool exhausted.

Check:
1. Max items per cart (business limit)?
2. Peak concurrent orders?
3. Pool acquire timeout — will requests fail or just slow?

Safer: `p-limit` with concurrency 5, or batch. Keeps parallelism win, caps pool pressure.

Also: single `WHERE sku IN (...)` query beats N parallel queries. One connection, one round-trip.
```

### Turn 5

**user:**

```text
OK so the parallel call could exhaust the pool if a single order has many SKUs. Average order has 3 SKUs, max we've seen is 47. Recommend a fix that's safer but doesn't slow down the common case.
```

**assistant:**

_output_tokens=205_

```text
Single `IN` query. Best for both cases.

```js
const rows = await db.query('SELECT * FROM inventory WHERE sku = ANY($1)', [skus]);
const bySku = new Map(rows.map(r => [r.sku, r]));
```

- 1 connection, 1 round-trip — regardless of 3 or 47 SKUs.
- Faster than parallel (no N handshakes).
- Zero pool pressure.

If ORM blocks raw `IN`: `p-limit(5)` fallback. Common case (3) still parallel, max case (47) caps at 5 concurrent.
```

---

## `hewn_prompt_only` — cumulative output_tokens=5268, cumulative wall=93762ms

### Turn 1

**user:**

```text
Production is throwing 500s on POST /api/orders since 14:23 UTC. Logs show 'TypeError: Cannot read properties of undefined (reading items)' in createOrder handler. Last deploy was 14:18 UTC. What do I check first?
```

**assistant:**

_output_tokens=609_

```text
Roll back the 14:18 deploy first, then investigate. Five minutes between deploy and errors is the strongest signal you have — restore service, diagnose after.

Once rolled back, check in this order:

1. **Diff the deploy** — `git log 14:18-deploy-sha...prev-deploy-sha -- **/createOrder*` and anything touching the order request shape. You're looking for a renamed/removed field on `req.body` or a changed middleware that used to populate `items`.
2. **Capture a failing request** — get the actual request body from logs/APM (Sentry, Datadog). `undefined.items` means the parent object is undefined — is it `req.body`, `req.body.cart`, `order`? The exact access path narrows it to one line.
3. **Check the client** — if mobile/web shipped around the same time, the payload shape may have changed and the server wasn't updated (or vice versa). Version skew is common with "deploy at 14:18, errors at 14:23" — matches the time for clients to pick up a new bundle.
4. **Middleware/parser** — did `body-parser`, auth middleware, or a validation layer change? A middleware that stopped attaching `items` to the request produces exactly this error.

If rollback fixes it: you have your culprit window. If rollback doesn't fix it: the trigger is upstream (client, CDN, feature flag flip, downstream service returning different shape) — widen the search.

What's the stack and where are logs? I can help narrow further with the actual error line or a diff.
```

### Turn 2

**user:**

```text
Rolled back to previous deploy and 500s stopped. Now I need to find what changed. The PR that shipped at 14:18 was a refactor of cart serialization. Here's the diff for the suspected file: function buildCart(cart) { return { id: cart.id, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. Original was: function buildCart(cart) { return { id: cart.id, items: cart.items, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. What broke?
```

**assistant:**

_output_tokens=560_

```text
The refactor dropped `items` from the returned object. Downstream code — almost certainly `createOrder` — is calling `buildCart(cart).items` (or receiving the result and then reading `.items`), and now gets `undefined.items` → the exact TypeError you're seeing.

The original shape was `{ id, items, total }`. The new shape is `{ id, total }`. `total` was computed from `cart.items` internally, so the function still "works" in isolation, but any caller that relied on `items` being passed through is broken.

Fix options:

1. **Restore the field** — add `items: cart.items` back. Safest, matches old contract, unblocks the handler. Ship this now.
2. **Fix the caller** — if the refactor's intent was to stop exposing `items` from `buildCart`, update `createOrder` to read items from the original `cart` (which it presumably already has) rather than from the `buildCart` result. Do this only if there's a deliberate reason to narrow the return shape.

To confirm before shipping: grep for `buildCart(` and for `.items` on whatever variable holds its return value. If any call site reads `.items` off the result, option 1 is correct. If the only consumer you can find is `createOrder` and it has `cart` in scope already, option 2 is cleaner.

Add a test that asserts the shape of `buildCart`'s return value so this regression can't recur silently.
```

### Turn 3

**user:**

```text
Right, items field was dropped. Downstream order service expects items. Fix: re-add items in buildCart. But I want to add a regression test so this can't happen again. What's the right test shape? We use Jest.
```

**assistant:**

_output_tokens=789_

```text
Lock down the *contract*, not the implementation. The bug was a shape regression, so assert the shape.

```js
describe('buildCart', () => {
  const cart = {
    id: 'c_1',
    items: [
      { price: 10, qty: 2 },
      { price: 5, qty: 1 },
    ],
  };

  it('preserves items in the returned cart', () => {
    // Regression: refactor dropped `items`, breaking createOrder (incident 2026-04-22)
    expect(buildCart(cart)).toHaveProperty('items', cart.items);
  });

  it('returns the expected shape', () => {
    expect(buildCart(cart)).toEqual({
      id: 'c_1',
      items: cart.items,
      total: 25,
    });
  });
});
```

Two tests, two jobs:

- **The regression test** — a single focused assertion named after the thing that broke. If someone drops `items` again, this fails with a message that points straight at the cause. The comment referencing the incident is the one case where a code comment earns its place: it explains *why* this seemingly redundant test exists so a future refactorer doesn't delete it.
- **The shape test** — `toEqual` with the full object locks the contract. Any added, removed, or renamed field fails loudly. This is the one that catches the *next* shape regression, not just this one.

Avoid:

- Asserting only `total` — that's what the broken version still computed correctly.
- `toMatchObject` for the shape test — it permits extra fields, which defeats the point.
- Snapshot tests here — they encourage "just update the snapshot" when something breaks, which is exactly the failure mode you're trying to prevent.

If `buildCart` has other call sites with different expectations, add a contract test per consumer (e.g., `describe('buildCart contract for order service')`) so the intent is documented.
```

### Turn 4

**user:**

```text
Test added and passes. Now reviewing the rest of that PR. There's also a change to the inventory check: it now uses Promise.all over an array of SKU lookups instead of a sequential loop. Is that safe under our DB connection pool of 20 max?
```

**assistant:**

_output_tokens=1526_

```text
Not obviously safe. The pool size isn't the only variable — you need to think about worst case, not typical case.

**The math that matters:**

- Sequential loop: 1 connection per in-flight request, for the duration of the request. Pool usage scales with *request concurrency*.
- `Promise.all`: up to N connections per in-flight request (N = SKUs in cart). Pool usage scales with *request concurrency × cart size*.

So: pool=20, pre-refactor you could handle ~20 concurrent order checks. Post-refactor, a single 20-SKU cart consumes the entire pool. Two concurrent 15-SKU carts (30 connections demanded) queue on the pool and can hit `acquire timeout`, and — worse — starve *every other query in the app* that shares the pool: health checks, auth, unrelated endpoints.

**What to check before concluding:**

1. **Max SKUs per cart** — is there a cap? Typical P99? If P99 is 3 and max is 8, the risk is smaller than if carts can have 100 items. If there's no hard cap, assume adversarial input.
2. **Pool is shared or dedicated?** — if the same pool serves the whole app, exhaustion cascades. If it's dedicated to order flow, blast radius is limited to orders.
3. **Pool `acquireTimeout` / `waitForConnections`** — what happens when exhausted? Queue silently (latency spike)? Throw (500s)? You probably want to know which before shipping.
4. **What else was in the pool's budget** — if the app was already running near pool capacity under load, this change pushes it over.

**The better fix, probably:**

The refactor is solving the wrong problem. If you're doing N SKU lookups, replace them with one query:

```sql
SELECT * FROM inventory WHERE sku IN (:skus)
```

One connection, one round trip, faster than either sequential or `Promise.all`, and pool-safe regardless of cart size. This is almost always the right answer for "fan out N lookups by ID."

If a batch query genuinely isn't possible (e.g., each lookup hits a different service), cap concurrency with `p-limit` or similar:

```js
const limit = pLimit(5);
await Promise.all(skus.map(sku => limit(() => lookup(sku))));
```

Pick the cap based on: `(pool_size − headroom_for_other_queries) / expected_concurrent_requests`. With pool=20, something like 3–5 is a reasonable starting point; measure under load.

**Short answer:** don't ship as-is unless cart size is bounded small and you've confirmed the pool has headroom. Push for the batch query first, fall back to bounded concurrency if you must.
```

### Turn 5

**user:**

```text
OK so the parallel call could exhaust the pool if a single order has many SKUs. Average order has 3 SKUs, max we've seen is 47. Recommend a fix that's safer but doesn't slow down the common case.
```

**assistant:**

_output_tokens=1784_

```text
**Primary recommendation: batch query.** One `SELECT ... WHERE sku IN (:skus)` replaces all N lookups. Common case goes from "3 parallel round trips + 3 connection acquires" to "1 round trip, 1 connection" — *faster* than the refactor, not slower. Worst case goes from "47 connections demanded" to "1 connection." Pool safety becomes trivial. If the inventory source is your own DB, this is the answer.

```js
const rows = await db.query('SELECT * FROM inventory WHERE sku = ANY($1)', [skus]);
const bySku = new Map(rows.map(r => [r.sku, r]));
const results = skus.map(sku => bySku.get(sku));
```

(Rebuild a `skus.map` result at the end if call sites depend on order, or if you need to detect missing SKUs as an error case.)

**Fallback: bounded concurrency, cap = 5.** Use this only if the lookup can't be batched (separate service per SKU, per-sku authorization, etc.). Common case of 3 SKUs is unaffected — all 3 fire in parallel, identical to the refactor. A 47-SKU cart runs ~10 sequential waves of 5, slower than broken `Promise.all` but bounded.

```js
import pLimit from 'p-limit';
const limit = pLimit(5);
const results = await Promise.all(skus.map(sku => limit(() => lookupSku(sku))));
```

Cap math: pool=20, leave ~10 for other queries in the app, allow 2 concurrent order checks → 5 per request. Adjust if your concurrency profile differs.

**Skip these:**

- *Conditional strategy* ("if `skus.length < 10`, `Promise.all`, else chunked") — adds a branch that's hard to reason about under load and only saves a few ms on the worst case.
- *Raising the pool size* — treats the symptom. You still have no bound on per-request parallelism.
- *Keeping the sequential loop* — 3 serial round trips in the common case is a real latency regression for no safety benefit once you have a proper fix.

If you go with the batch query, keep a regression test that asserts the inventory check issues one query, not N — mock the DB client and assert call count. That's the shape contract for "don't accidentally refactor back to fan-out."
```

---

## `hewn_full` — cumulative output_tokens=1218, cumulative wall=33536ms

### Turn 1

**user:**

```text
Production is throwing 500s on POST /api/orders since 14:23 UTC. Logs show 'TypeError: Cannot read properties of undefined (reading items)' in createOrder handler. Last deploy was 14:18 UTC. What do I check first?
```

**assistant:**

_output_tokens=207_

```text
rollback 14:18 deploy first — fastest path to green, investigate after

check diff between last-good and 14:18: focus on createOrder handler and request shape
"reading items" on undefined → req.body.items or order.items, likely body parsing or schema change
verify: did route change body validator? did client contract change (items moved, renamed, nested)?
check if middleware order changed (body-parser before handler?)
check if new field made items optional in types but handler still dereferences
repro locally with prod payload sample from logs before redeploying fix
if rollback not possible: add guard + 400 on missing items, ship hotfix, then root cause
```

### Turn 2

**user:**

```text
Rolled back to previous deploy and 500s stopped. Now I need to find what changed. The PR that shipped at 14:18 was a refactor of cart serialization. Here's the diff for the suspected file: function buildCart(cart) { return { id: cart.id, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. Original was: function buildCart(cart) { return { id: cart.id, items: cart.items, total: cart.items.reduce((s, i) => s + i.price * i.qty, 0) }; }. What broke?
```

**assistant:**

_output_tokens=184_

```text
@hewn v0 hybrid
G: identify_root_cause_of_createorder_500
C: buildcart_refactor_dropped_items_field ∧ downstream_handler_reads_order_items
P: restore_items_in_buildcart_return ∧ audit_consumers_of_buildcart
V: createorder_post_returns_200 ∧ order_items_defined_in_handler ∧ no_typeerror_in_logs
A: add_contract_test_for_buildcart_shape ∧ add_schema_assertion_on_items_presence
```

### Turn 3

**user:**

```text
Right, items field was dropped. Downstream order service expects items. Fix: re-add items in buildCart. But I want to add a regression test so this can't happen again. What's the right test shape? We use Jest.
```

**assistant:**

_output_tokens=294_

```text
@hewn v0 hybrid
G: prevent_buildcart_shape_regression_via_jest_test
C: buildcart_must_return_id_items_total ∧ items_must_preserve_input_array ∧ total_must_equal_sum_of_price_times_qty
P: write_jest_unit_test_for_buildcart ∧ assert_returned_keys_exact_set ∧ assert_items_deep_equal_input ∧ assert_total_computed_correctly ∧ add_empty_items_case ∧ add_single_item_case ∧ add_multi_item_case
V: test_fails_on_current_buggy_buildcart ∧ test_passes_after_items_restored ∧ ci_runs_test_on_every_pr
A: add_contract_test_between_buildcart_and_order_service ∧ add_type_or_schema_guard_on_buildcart_return
```

### Turn 4

**user:**

```text
Test added and passes. Now reviewing the rest of that PR. There's also a change to the inventory check: it now uses Promise.all over an array of SKU lookups instead of a sequential loop. Is that safe under our DB connection pool of 20 max?
```

**assistant:**

_output_tokens=288_

```text
depends on cart size and concurrent request volume
Promise.all fans out N lookups in parallel — each grabs a pool connection
cart with 30 SKUs × 10 concurrent requests = 300 connections wanted, pool caps at 20
rest queue on pool, latency spikes, potential timeouts, maybe pool exhaustion errors
safer: bounded concurrency (p-limit, 5-8 parallel) or batched IN query (one lookup for all SKUs)
batched IN query best — one connection, one round trip, scales with cart size
check: does SKU lookup hit same table? if yes, SELECT ... WHERE sku IN (...) kills this problem
also check: any retry logic? Promise.all fails fast on first rejection, sequential loop may have partial-success semantics the caller relied on
load test before shipping or gate behind cart-size cap
```

### Turn 5

**user:**

```text
OK so the parallel call could exhaust the pool if a single order has many SKUs. Average order has 3 SKUs, max we've seen is 47. Recommend a fix that's safer but doesn't slow down the common case.
```

**assistant:**

_output_tokens=245_

```text
batched IN query — one SELECT WHERE sku IN (...) regardless of cart size
one connection, one round trip, common case (3 SKUs) faster than sequential and same as parallel
47-SKU edge case also one connection instead of 47
preserves order-independent lookup, easy to map results back by sku key
watch: IN-list size limits (Postgres fine to thousands, MySQL default max_allowed_packet, SQLite 999)
cap at something sane (e.g. 500) and chunk if exceeded — future-proof
if batched query not feasible (different tables per SKU type, etc), fall back to p-limit with concurrency 5
keep Promise.all shape, swap inner work for batched fetch + in-memory lookup
```

---
