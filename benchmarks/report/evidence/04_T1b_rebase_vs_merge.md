# Evidence — T1b / `git-rebase-vs-merge`

## Prompt

```text
How does git rebase differ from git merge?
```

## `baseline`

output_tokens (anthropic) = **218**, output_tokens (tiktoken) = 134, input_tokens = 6, cache_creation = 0, cache_read = 28522, latency wall = 6332ms (median across runs: 5206ms)

```text
**Merge** preserves history as-is: it creates a new commit that ties two branch tips together, keeping both parent lineages visible.

**Rebase** rewrites history: it takes your commits and replays them on top of another branch, producing new commits with new SHAs and a linear history.

Key tradeoffs:
- Merge is non-destructive and safe for shared branches. History shows exactly what happened, including the branch topology.
- Rebase gives a cleaner, linear log but rewrites commits. Never rebase commits already pushed to a shared branch — it breaks other people's clones.

Rule of thumb: rebase local work before pushing, merge public branches.
```

## `terse`

output_tokens (anthropic) = **248**, output_tokens (tiktoken) = 154, input_tokens = 6, cache_creation = 0, cache_read = 20294, latency wall = 5201ms (median across runs: 5201ms)

```text
**Merge**: Creates a new commit that joins two branches. Preserves full history, including the branch topology. Non-destructive.

**Rebase**: Replays your commits on top of another branch, rewriting history. Produces a linear history with no merge commit.

Key differences:
- **History shape**: merge = branching graph; rebase = straight line.
- **Commit hashes**: merge keeps them; rebase creates new ones.
- **Safety**: merge is safe on shared branches; rebase rewrites history, so avoid on branches others have pulled.
- **Conflict resolution**: merge resolves once; rebase may require resolving per replayed commit.

Rule of thumb: rebase local work before pushing; merge when integrating shared branches.
```

## `caveman_full`

output_tokens (anthropic) = **103**, output_tokens (tiktoken) = 61, input_tokens = 6, cache_creation = 0, cache_read = 21739, latency wall = 3339ms (median across runs: 3356ms)

```text
Rebase: replay commits on top of target. Linear history, new SHAs, rewrites.
Merge: join branches via merge commit. Preserves history, keeps SHAs, non-linear.

Rebase = clean line. Merge = true record.

Rule: rebase local/private, merge shared/public.
```

## `caveman_full_plus_ultra_directive`

output_tokens (anthropic) = **102**, output_tokens (tiktoken) = 56, input_tokens = 6, cache_creation = 6552, cache_read = 15201, latency wall = 4126ms (median across runs: 3778ms)

```text
Rebase: replay commits onto new base. Linear history. Rewrite SHAs.
Merge: join branches via merge commit. Preserve history. Keep SHAs.

Rebase → clean log, lose context, unsafe on shared branch.
Merge → true history, extra commits, safe always.
```

## `hewn_prompt_only`

output_tokens (anthropic) = **225**, output_tokens (tiktoken) = 142, input_tokens = 6, cache_creation = 15817, cache_read = 16796, latency wall = 5433ms (median across runs: 5560ms)

```text
**Merge** creates a new commit that joins two branch histories, preserving the original commits and their timestamps. The history shows the branches as parallel lines that converge.

**Rebase** replays your commits on top of another branch, producing new commits with new hashes. The history becomes linear, as if you'd written your changes on top of the latest base from the start.

Key tradeoffs:
- **Merge**: non-destructive, preserves true history, but can clutter the log with merge commits.
- **Rebase**: clean linear history, but rewrites commits — never rebase branches others have pulled.

Rule of thumb: rebase local/feature branches before sharing; merge when integrating shared branches.
```

## `hewn_full`

output_tokens (anthropic) = **158**, output_tokens (tiktoken) = 96, input_tokens = 6, cache_creation = 0, cache_read = 30005, latency wall = 7847ms (median across runs: 5994ms)

```text
rebase rewrites commits onto new base — linear history, new SHAs
merge ties two branches with merge commit — preserves original commits and branching shape

rebase good for local cleanup before sharing
merge good for shared branches — never rebase public history, breaks collaborators

conflicts: rebase resolves per-commit (can hit same conflict multiple times), merge resolves once
rebase loses merge context; merge keeps it

rule of thumb: rebase private, merge public
```
