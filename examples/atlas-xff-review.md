# Long-prompt example — Atlas API security review

Illustrative Atlas side-by-side example from an earlier benchmark
iteration. Use it as a qualitative prompt-shape example for the kind of
long-context, constrained task where token burn matters; use the
current benchmark report for aggregate numbers.

This is not Hewn's main launch proof. The current benchmark says
single-shot long-context compression is where Caveman wins on tokens;
Hewn's strongest public case is multi-turn Claude Code sessions.

## Historical result

| Mode | Output tokens | Latency |
| --- | ---: | ---: |
| Verbose Claude | 523 | 11.5s |
| Caveman Ultra-style | 512 | 11.2s |
| **Hewn** | **167** | **4.5s** |

(`Caveman Ultra-style` is our directive-based approximation, not
Caveman's official `/caveman ultra` skill — see
[benchmarks/report/REPORT.md](../benchmarks/report/REPORT.md) honesty
box for details.)

## Prompt excerpt

```text
Project handbook: Atlas API service
- Public edge must never trust client-supplied identity headers.
- Security-sensitive fixes should prefer narrow patches over broad rewrites.
- Review findings should be short but concrete: finding, exploit path,
  mitigation, verification, and main risks.
- Preserve exact literals such as "X-Forwarded-For", "Redis", "401",
  "next(err)", and "PostgreSQL".

[Task]
[capsule micro review]
anchors: "X-Forwarded-For" | "Redis"
diff: + const key=`rl:${req.headers['x-forwarded-for']||req.ip}`;
        await redis.incr(key);
ctx: public_api_gateway rate limiter
deliver: risk mitigation verify
```

## Verbose Claude

```text
finding: `X-Forwarded-For` trusted without proxy validation => spoofable
rate-limit key

exploit:
- attacker sends `X-Forwarded-For: <random>` per request -> distinct keys
  -> limiter bypassed
- attacker pins victim IP -> exhausts victim's bucket -> DoS / lockout

mitigation:
- derive client IP from trusted proxy chain only
- never read raw `x-forwarded-for` at public boundary
- key on validated IP; fall back to `req.socket.remoteAddress`
- also add `INCR` + `EXPIRE` atomically

verify:
- spoof test: 100 req with rotating `X-Forwarded-For`
- victim-pin test: forged XFF=victim.ip
- TTL test: `TTL rl:<ip>` returns >0 after first hit
- proxy-off test: with `trust proxy=false`, XFF ignored entirely

risks:
- misconfigured proxy may still reflect XFF
- IPv6 + CGNAT shared buckets
- Redis key without `EXPIRE` = unbounded memory growth
```

## Caveman Ultra-style

```text
risk: spoof `X-Forwarded-For` -> bypass per-IP limit
risk: multi-hop XFF -> only first/last hop parsed, wrong client
risk: no TTL on key -> counter never resets, permanent lockout
risk: no limit check -> `incr` without threshold compare
risk: missing IP -> key `rl:undefined` -> shared bucket all anon
risk: Redis failure -> no fallback -> limiter fails open or crashes
risk: IPv6 normalization absent -> same client, multiple keys

mitigation: trust XFF only from signed gateway contract; else use `req.ip`
mitigation: parse XFF as left-most untrusted, right-most trusted hop
mitigation: `redis.expire(key, windowSec)` on first `incr`
mitigation: compare count vs limit -> `429` when exceeded
mitigation: reject/normalize when IP absent
mitigation: wrap Redis in try/catch
mitigation: normalize IPv6

verify: spoofed `X-Forwarded-For` from public edge -> limited by real IP
verify: exact-threshold request -> allowed; threshold+1 -> `429`
verify: key TTL present after first hit
verify: missing IP -> rejected or isolated bucket
verify: Redis down -> documented behavior
```

## Hewn

```text
@hewn v0 hybrid
G: fix(rl_spoof)
C: trust_boundary ∧ "X-Forwarded-For" ∧ "Redis"
P: drop("X-Forwarded-For") ∧ bind(req.ip) ∧ expire(key)
V: test(spoof_header) ∧ test(missing_ip) ∧ test(incr_ttl)
A: ! header_spoof ∧ ! key_unbounded ∧ ? proxy_chain
```

Same risk, mitigation, and verification. Hewn compresses the answer and
GCs the context: keep what changes the fix, drop what only burns tokens.
