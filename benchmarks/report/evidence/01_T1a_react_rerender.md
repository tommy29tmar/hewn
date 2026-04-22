# Evidence — T1a / `react-rerender-parent`

## Prompt

```text
Why does my React component re-render every time the parent updates?
```

## `baseline`

output_tokens (anthropic) = **310**, output_tokens (tiktoken) = 181, input_tokens = 6, cache_creation = 11730, cache_read = 16796, latency wall = 7120ms (median across runs: 7120ms)

```text
Because by default React re-renders every child when a parent renders — props equality isn't checked.

Fixes, in order of likelihood:

1. **Wrap the child in `React.memo`** — skips re-render when props are shallow-equal.
2. **Stabilize prop references** — inline objects/arrays/functions (`{}`, `[]`, `() => ...`) are new every render, defeating `memo`. Use `useMemo` / `useCallback`, or lift them out.
3. **Check context** — any component consuming a context re-renders when the context value changes, even through `memo`.
4. **Children as props** — passing `<Child />` as JSX children from the parent creates a new element each render; move the child up or memoize it.

If you paste the component + how the parent uses it, I can point at the specific cause.
```

## `terse`

output_tokens (anthropic) = **228**, output_tokens (tiktoken) = 149, input_tokens = 6, cache_creation = 6557, cache_read = 13741, latency wall = 6776ms (median across runs: 6776ms)

```text
Because React re-renders all descendants of a component that renders, by default. Props don't need to change.

Fixes:
- Wrap the child in `React.memo(Child)` — skips re-render when props are shallow-equal.
- Stabilize props: `useMemo` for objects/arrays, `useCallback` for functions. A new `{}` or `() => {}` each parent render defeats `memo`.
- Lift children via the `children` prop or move state down, so the parent re-render doesn't touch the subtree.
- Avoid inline object/array literals in JSX passed as props.

If `memo` isn't helping, log the props in the child and diff them — usually one prop is a fresh reference each render.
```

## `caveman_full`

output_tokens (anthropic) = **133**, output_tokens (tiktoken) = 84, input_tokens = 6, cache_creation = 6557, cache_read = 15186, latency wall = 4634ms (median across runs: 4634ms)

```text
Parent re-render → child re-render default. Props new ref each time (inline obj/array/fn) → bust memo.

Fix:
- Wrap child: `React.memo(Child)`
- Stable props: `useMemo` for obj/array, `useCallback` for fn
- Check: no new ref created in parent render

Still re-render after memo? Context consumer or unstable prop sneaking in.
```
