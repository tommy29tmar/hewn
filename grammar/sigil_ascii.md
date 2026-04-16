# SIGIL ASCII Fallback

Use these aliases on models or transports that do not behave well with Unicode operators.

| Unicode | ASCII | Meaning |
|---|---|---|
| `∧` | `&` | conjunction |
| `∨` | `|` | disjunction |
| `⇒` | `=>` | implication / likely cause |
| `→` | `->` | ordered next step |
| `Δ(x)` | `delta(x)` | change / patch |
| `⊥` | `FAIL` | contradiction / failure |
| `?` | `?` | uncertainty |
| `!` | `!` | high risk / priority |

Recommendations:

- Keep exact literals unchanged.
- Do not transliterate code, file paths, commands, or schema names.
- Prefer one operator style per document.
- Use Unicode only when the target model handles it reliably.

