# Emitted Malbolge static analyzer

## Status

Active implementation

## Purpose

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

## Scope

This document governs the following declared TODO scope:

- `verifier/`
- `tests/differential/`
- `tests/exhaustive/`
- `tests/fuzz/`

## Current Behavior

### Implemented initial-image slice

`verifier/emitted_malbolge.py` statically inspects raw `malbolge-1998` source
without executing guest instructions. It applies the historical loader's six
C-locale whitespace bytes, graphical ASCII boundary, two-word recurrence base,
59,049-word capacity, and position-dependent 94-cell decode table. Reports are
canonical JSON and include the exact historical profile identity/capacity,
required source words, SHA-256 of the exact raw source bytes, admitted initial
cells with original byte offsets, stable findings, and analysis limits. Schema
`malbolge-static-image/v4` retains the exact `entry_transition` from the
historical all-zero register state and adds one exact or explicitly unresolved
`second_transition`. The prefix replays committed entry writes before resolving
the reachable second fetch/data cells, decode, C/D alias, planned data write,
encryption address/input/output, accumulator dependency, halt/rejection, pointer
succession, and wrap. A second `p` whose accumulator depends on prior input is
reported unresolved rather than assigned a guessed value. Historical recurrence
words are derived only when a bounded read needs them. The report still records
that the profile's code/data pointers and words stay in `0..=59048`.

Initial-image admission is deliberately narrower than whole-program safety. The
current slice proves only a two-transition prefix. It does not claim third-step
or later reachability, general dataflow/evolved-memory equivalence, source-map
context, or input-dependent cycle/hang safety. Those remain open under this
TODO.

## Invariants

- The fixed historical address range is closed structurally; this does not
  imply which addresses are reachable or whether a particular run wraps a
  pointer.
- Per-cell encryption-target classification does not imply reachability. The
  bounded transfer records resolve only the first two historical transitions.
- Two-transition evidence never implies third-step or later control flow,
  general dataflow/evolved-memory equivalence, source-map context, or cycle/hang
  safety.
- Every reported initial cell preserves its loaded position and raw-source byte
  offset, and every report binds the exact source bytes and historical profile.
- Future dynamic analyses must state their bounded assumptions rather than
  executing arbitrary guest work to completion or treating unknown as safe.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance. The CLI prints canonical JSON for both admitted and
rejected initial images, returning a nonzero status when the image is rejected.
Unreadable source fails before a semantic report is emitted.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `canonical-malbolge-target-profile`.
- Current executable evidence covers known-valid source, exact loader
  whitespace, lexical rejection, recurrence underflow, historical capacity,
  all 8,836 graphical-byte/position decode pairs against an independent table
  anchored to the preserved historical interpreter `xlat1`, load-admission
  parity anchored to its `strchr("ji*p</vo", ...)` check, historical pointer
  assignment/wrap closure, `i`/`v`/ordinary post-step encryption-target
  classification anchored to the preserved interpreter order, positional decode
  rejection, exact second-step input/no-op/halt/invalid-encryption fixtures,
  explicit input-dependent-crazy unresolved evidence, a 24-case public CLI
  differential including recurrence-backed entry `j`, 16 seeded invalid
  positional mutations with byte-exact replay, byte-exact CLI/library report
  parity, bounded analysis limits, CLI second-step rejection status, and CLI read
  failure.

## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
