# Benchmark Artifacts

`evals/runs/` contains the raw provider outputs behind the benchmark claims in
this repository.

Conventions:

- published benchmark rows live in named experiment directories such as
  `exp_*`, `multi_ir_*`, `macro_compiled_*`, `openai_macro_*`,
  `claude_macro_*`, and `top_tier_*`
- historical top-level `.jsonl` files are kept when they are referenced by the
  benchmark docs or by the eval workflow docs
- ad-hoc scratch files are not part of the public evidence surface

Ignored by default:

- `tmp_*.jsonl`
- `*smoke*.jsonl`
- `my_run.jsonl`

When adding a new published benchmark row, prefer a named subdirectory and
reference it from `evals/benchmark_matrix.json`.
