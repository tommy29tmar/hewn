# Evidence — T1b / `tcp-vs-udp`

## Prompt

```text
What's the difference between TCP and UDP?
```

## `baseline`

output_tokens (anthropic) = **181**, output_tokens (tiktoken) = 98, input_tokens = 6, cache_creation = 11727, cache_read = 16796, latency wall = 4988ms (median across runs: 4344ms)

```text
TCP is connection-oriented: it establishes a session (3-way handshake), guarantees delivery, preserves order, and handles retransmission and flow/congestion control. Used for HTTP, SSH, file transfer.

UDP is connectionless: fire-and-forget datagrams, no handshake, no delivery guarantee, no ordering, minimal overhead. Used for DNS, video/voice streaming, games — where low latency beats reliability.

Key tradeoff: TCP = reliable but slower, UDP = fast but lossy.
```

## `terse`

output_tokens (anthropic) = **171**, output_tokens (tiktoken) = 91, input_tokens = 6, cache_creation = 6554, cache_read = 13741, latency wall = 4170ms (median across runs: 3690ms)

```text
TCP is connection-oriented, reliable, and ordered — it establishes a handshake, retransmits lost packets, and guarantees delivery in sequence. Used for web, email, file transfer.

UDP is connectionless, unreliable, and unordered — it fires packets without handshakes, acknowledgments, or retries. Lower latency and overhead. Used for video/voice streaming, gaming, DNS.

Key tradeoff: TCP trades speed for reliability; UDP trades reliability for speed.
```

## `caveman_full`

output_tokens (anthropic) = **125**, output_tokens (tiktoken) = 73, input_tokens = 6, cache_creation = 6554, cache_read = 15186, latency wall = 3003ms (median across runs: 3450ms)

```text
TCP = reliable, ordered, connection-based. Handshake, retransmit lost packets, flow+congestion control. Slower, heavier.

UDP = fire-and-forget. No handshake, no retransmit, no ordering. Fast, light, lossy.

Use TCP: web, SSH, file transfer. Use UDP: video/voice, games, DNS.
```

## `caveman_full_plus_ultra_directive`

output_tokens (anthropic) = **95**, output_tokens (tiktoken) = 51, input_tokens = 6, cache_creation = 0, cache_read = 21754, latency wall = 4312ms (median across runs: 3712ms)

```text
TCP = connection, reliable, ordered, slow. Handshake, ack, retransmit. Web/SSH/email.

UDP = no connection, no guarantee, fast. Fire-forget. DNS/video/games.

TCP care packet arrive. UDP care speed.
```

## `hewn_prompt_only`

output_tokens (anthropic) = **180**, output_tokens (tiktoken) = 102, input_tokens = 6, cache_creation = 11727, cache_read = 16796, latency wall = 4058ms (median across runs: 4058ms)

```text
**TCP** — connection-oriented, reliable. Handshake, ordered delivery, retransmission, flow/congestion control. Used for HTTP, SSH, email.

**UDP** — connectionless, best-effort. No handshake, no ordering, no retransmission. Lower latency, smaller header. Used for DNS, video/voice, games, QUIC.

Tradeoff: TCP guarantees delivery at the cost of latency and overhead; UDP is fast and cheap but the application must handle loss/ordering if it cares.
```

## `hewn_full`

output_tokens (anthropic) = **173**, output_tokens (tiktoken) = 98, input_tokens = 6, cache_creation = 13201, cache_read = 16805, latency wall = 6055ms (median across runs: 6055ms)

```text
TCP connection-oriented, handshake first, reliable delivery, ordered bytes, retransmits lost packets, flow/congestion control. Heavier.
UDP fire-and-forget, no handshake, no guarantees on delivery or order, no retransmit. Lighter, lower latency.
Use TCP when you need correctness: web, SSH, file transfer, DB.
Use UDP when you need speed and can tolerate loss: DNS, video/voice, games, QUIC (builds its own reliability on top).
```
