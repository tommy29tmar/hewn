# Design Scope

This prototype intentionally solves the narrowest useful layer of SIGIL:

- represent a symbolic draft as a file format
- validate that format deterministically
- preserve a codebook for repeated entities
- provide an audit path back to human-readable text

It does **not** attempt to solve:

- automatic compilation from arbitrary user language into SIGIL
- confidence estimation
- adaptive expansion policies
- latent or learned reasoning tokens
- benchmark orchestration across providers

The parser therefore exists to make the representation concrete, not to overclaim runtime intelligence that does not exist yet.

## Why The Grammar Is Narrow

SIGIL is deliberately line-oriented:

- one header
- optional codebook
- one clause per line
- optional audit block

This keeps parsing simple, diff-friendly, and portable across tools.

## Why `audit` Is Outside The EBNF

`audit` mode is plain human language. Once the system returns only prose, the symbolic grammar no longer applies. The EBNF in this repo therefore targets the symbolic substrate rather than every possible user-facing output.

