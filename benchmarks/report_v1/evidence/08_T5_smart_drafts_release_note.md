# Evidence — T5 / `smart-drafts-release-note`

## Prompt

```text
"
```

## `baseline`

output_tokens (anthropic) = **18**, output_tokens (tiktoken) = 13, input_tokens = 6, cache_creation = 15805, cache_read = 16796, latency wall = 2011ms (median across runs: 1680ms)

```text
I see an empty message. What would you like help with?
```

## `terse`

output_tokens (anthropic) = **12**, output_tokens (tiktoken) = 8, input_tokens = 6, cache_creation = 10478, cache_read = 13741, latency wall = 1287ms (median across runs: 3024ms)

```text
What would you like me to do?
```

## `caveman_full`

output_tokens (anthropic) = **12**, output_tokens (tiktoken) = 6, input_tokens = 6, cache_creation = 0, cache_read = 25664, latency wall = 1674ms (median across runs: 1779ms)

```text
Empty input. What need?
```

## `caveman_full_plus_ultra_directive`

output_tokens (anthropic) = **15**, output_tokens (tiktoken) = 6, input_tokens = 6, cache_creation = 10477, cache_read = 15201, latency wall = 1676ms (median across runs: 1629ms)

```text
Empty prompt. Need task.
```

## `hewn_prompt_only`

output_tokens (anthropic) = **18**, output_tokens (tiktoken) = 11, input_tokens = 6, cache_creation = 0, cache_read = 32601, latency wall = 1756ms (median across runs: 2207ms)

```text
I'm ready. What would you like me to do?
```

## `hewn_full`

output_tokens (anthropic) = **74**, output_tokens (tiktoken) = 7, input_tokens = 6, cache_creation = 0, cache_read = 34084, latency wall = 2902ms (median across runs: 2711ms)

```text
empty prompt — what you need?
```
