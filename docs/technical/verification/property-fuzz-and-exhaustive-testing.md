# Property, fuzz, and exhaustive testing

## Status

Active implementation

## Purpose

Use property testing, fuzzing, sanitizers, regression corpora, and exhaustive
finite-domain verification for small functions and VM primitives such as rotate
and crazy operations.

## Scope

This document governs the following declared TODO scope:

- `verifier/`
- `tests/differential/`
- `tests/exhaustive/`
- `tests/fuzz/`

## Current Behavior

### Deterministic generated differential cases

`tests/fuzz/cases.rs` generates valid classic source by construction: at each
loaded position it chooses only graphical bytes whose public
`decode_instruction` result is one of the eight load-admitted instructions. No
ambient entropy is used. The fixed seed plus ordinal fully reconstructs source,
input bytes, and step budget.

The same module defines deterministic shrink candidates. Shrinking reduces
source length while preserving the already-valid prefix, then input length and
step budget. A differential failure repeatedly tests smaller candidates and
reports the minimized replay identity rather than discarding the original case.

`tests/differential/classic_profile.rs` currently replays 24 generated cases
through the public classic `Machine` and `ProfileMachine` selected explicitly
for
`malbolge-1998`. Each requested step compares normalized continuation,
termination, or invalid-self-encryption rejection plus registers, input cursor,
output, and termination state. Final comparison checks all 59,049 memory words.
The two runtime APIs do not share private transition helpers in this test.

### Exhaustive finite domains

`tests/exhaustive/loader_boundaries.rs` exhausts every byte value that is
neither
ASCII whitespace nor graphical source, checks all 94 position-dependent decode
phases have both admitted and rejected graphical bytes, mutates one valid
94-word source at every phase to require exact `InvalidInstruction` identity,
and fixes recurrence-base and source-capacity boundaries.

The earlier `tests/vm/tables.rs` remains exhaustive arithmetic evidence: every
classic rotate word, every graphical decode position, and both five-trit crazy
chunk positions are checked against independent scalar formulas. This work is
referenced rather than duplicated under a second test implementation.

### Remaining scope

This slice establishes deterministic replay/shrink and finite VM/loader domains.
Sanitizer campaigns and verifier-valid-versus-mutated-invalid testing remain
open
because the general translation verifier is not yet implemented. Those future
checks must preserve stable seeds/counterexamples rather than turning this task
into nondeterministic CI fuzzing.

## Invariants

- Generators cover valid/invalid words, instruction positions, crazy/rotate
  arithmetic, self-modification, loader boundaries, and small-state exhaustive
  domains with deterministic shrinking/replay.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- `cargo test --test property_verification --all-features` executes generated
  replay/shrink, classic/profile differential, and loader exhaustive evidence.
- `tests/vm/tables.rs` supplies the existing exhaustive rotate/crazy/decode
  table
  equivalence evidence under the full VM integration target.
- Required future evidence still includes sanitizer campaigns and deliberate
  valid/invalid verifier mutations once that verifier surface exists.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `independent-pure-c-malbolge-vm`.
## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
